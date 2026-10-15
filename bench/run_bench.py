"""M0 / Spike S1 — render benchmark for YT Music Editor.

Measures end-to-end render throughput (GPU draw -> readback -> pipe -> FFmpeg encode)
for the scene the app will produce, and projects the time needed for a 3-hour mix.

Strategies compared (see docs/DECISIONS.md D-21):
  A  draw every layer on every frame
  B  pre-render one background loop (artwork + zoom + grain + dust) once, then
     decode it in a loop and composite overlay / visualizer / text on top

Everything is synthetic: no user files are needed and nothing copyrighted is used.
All animation is a pure function of time t, as required by docs/CODING-GUIDE.md §6.4.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import psutil
except ImportError:  # optional: only used for CPU usage sampling
    psutil = None

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
RESULTS = HERE / "results"
FPS = 30
LOOP_SEC = 60.0
MIX_SEC = 3 * 3600.0
RESOLUTIONS = {1080: (1920, 1080), 1440: (2560, 1440), 2160: (3840, 2160)}
# "Balanced" quality bitrates (Mbps), see ui-mockup export tab
BITRATE = {1080: 6, 1440: 12, 2160: 24}
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


# --------------------------------------------------------------------------- ffmpeg


def find_ffmpeg() -> str:
    candidates = [
        os.environ.get("YTME_FFMPEG"),
        str(HERE / "ffmpeg" / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")),
        shutil.which("ffmpeg"),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    sys.exit("Không tìm thấy FFmpeg. Đặt ffmpeg vào bench/ffmpeg/bin/ hoặc PATH, "
             "hoặc set biến YTME_FFMPEG.")


FFMPEG = ""


def run(args: list[str], **kw) -> subprocess.CompletedProcess:
    check = kw.pop("check", False)
    return subprocess.run(args, capture_output=True, check=check, creationflags=NO_WINDOW, **kw)


def ffmpeg_version() -> str:
    out = run([FFMPEG, "-hide_banner", "-version"]).stdout.decode(errors="replace")
    return out.splitlines()[0] if out else "?"


def probe_encoder(name: str) -> bool:
    """Encoders can be compiled in but unusable (no GPU / driver), so try a real encode."""
    r = run([FFMPEG, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
             "color=black:s=256x256:d=0.2:r=30", "-c:v", name, "-f", "null", "-"])
    return r.returncode == 0


def probe_cuda_decode() -> bool:
    clip = WORK / "probe.mp4"
    if not clip.exists():
        run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
             "testsrc2=s=256x256:d=0.5:r=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)])
    r = run([FFMPEG, "-hide_banner", "-loglevel", "error", "-hwaccel", "cuda", "-i", str(clip),
             "-f", "null", "-"])
    return r.returncode == 0


def encoder_args(enc: str, height: int, high_quality: bool = False) -> list[str]:
    br = BITRATE[height]
    if enc == "nvenc":
        cq = "16" if high_quality else "21"
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", cq,
                "-b:v", f"{br}M", "-maxrate", f"{int(br * 1.5)}M", "-bufsize", f"{br * 2}M",
                "-g", "60", "-bf", "2"]
    crf = "16" if high_quality else "20"
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf, "-g", "60"]


COLOR_ARGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
              "-color_range", "tv"]


class Encoder:
    """FFmpeg process fed raw frames on stdin by a writer thread (overlaps GPU work and I/O)."""

    def __init__(self, out: Path, w: int, h: int, pix: str, enc: str, height: int, hq: bool = False):
        self.cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "rawvideo", "-pix_fmt", pix, "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
                    *encoder_args(enc, height, hq), "-pix_fmt", "yuv420p", *COLOR_ARGS, str(out)]
        self.proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                     creationflags=NO_WINDOW)
        self.q: queue.Queue[bytes | None] = queue.Queue(maxsize=4)
        self.error: str | None = None
        self.t = threading.Thread(target=self._write, daemon=True)
        self.t.start()

    def _write(self) -> None:
        assert self.proc.stdin
        while (buf := self.q.get()) is not None:
            try:
                self.proc.stdin.write(buf)
            except (BrokenPipeError, OSError) as e:
                self.error = str(e)
                break
        try:
            self.proc.stdin.close()
        except OSError:
            pass

    def put(self, buf: bytes) -> None:
        if self.error:
            raise RuntimeError(self.error)
        self.q.put(buf)

    def close(self) -> None:
        self.q.put(None)
        self.t.join()
        assert self.proc.stderr
        err = self.proc.stderr.read()  # stdin is already closed by the writer thread
        self.proc.wait()
        if self.error or self.proc.returncode != 0:
            raise RuntimeError(f"FFmpeg lỗi: {err.decode(errors='replace')[-800:]}")


class FrameSource:
    """Decodes a video in an endless loop to raw NV12 frames (1.5 bytes/px, no RGB conversion on CPU)."""

    def __init__(self, path: Path, w: int, h: int, cuda: bool):
        hw = ["-hwaccel", "cuda"] if cuda else []
        self.size = w * h * 3 // 2
        self.proc = subprocess.Popen(
            [FFMPEG, "-hide_banner", "-loglevel", "error", *hw, "-stream_loop", "-1", "-i", str(path),
             "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "nv12", "-"],
            stdout=subprocess.PIPE, creationflags=NO_WINDOW, bufsize=self.size * 2)
        self.q: queue.Queue[bytes] = queue.Queue(maxsize=6)
        self.alive = True
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.proc.stdout
        while self.alive:
            buf = self.proc.stdout.read(self.size)
            if len(buf) < self.size:
                break
            self.q.put(buf)

    def get(self) -> bytes:
        return self.q.get(timeout=30)

    def close(self) -> None:
        self.alive = False
        self.proc.kill()
        self.proc.wait()


# --------------------------------------------------------------------------- monitor


class Monitor:
    """Samples GPU (nvidia-smi) and CPU usage while a run is in progress."""

    def __init__(self) -> None:
        self.gpu: list[float] = []
        self.vram: list[float] = []
        self.cpu: list[float] = []
        self.smi = shutil.which("nvidia-smi")
        self._stop = threading.Event()
        self._proc: subprocess.Popen | None = None

    def start(self) -> None:
        if self.smi:
            self._proc = subprocess.Popen(
                [self.smi, "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits",
                 "-lms", "500"], stdout=subprocess.PIPE, text=True, creationflags=NO_WINDOW)
            threading.Thread(target=self._read_smi, daemon=True).start()
        if psutil:
            psutil.cpu_percent(None)
            threading.Thread(target=self._read_cpu, daemon=True).start()

    def _read_smi(self) -> None:
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            try:
                g, m = (float(x) for x in line.split(",")[:2])
                self.gpu.append(g)
                self.vram.append(m)
            except ValueError:
                pass

    def _read_cpu(self) -> None:
        while not self._stop.wait(0.5):
            self.cpu.append(psutil.cpu_percent(None))

    def stop(self) -> dict:
        self._stop.set()
        if self._proc:
            self._proc.kill()
        avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
        return {"gpu_util_avg": avg(self.gpu), "vram_mb_max": max(self.vram) if self.vram else None,
                "cpu_util_avg": avg(self.cpu)}


# --------------------------------------------------------------------------- assets


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def make_artwork() -> Image.Image:
    """Portrait 9:16 artwork so the 16:9 output exercises the blur-fill path."""
    w, h = 1080, 1920
    y = np.linspace(0, 1, h)[:, None]
    top, mid, bot = np.array([27, 23, 64]), np.array([107, 58, 122]), np.array([224, 128, 106])
    grad = np.where(y < 0.6, top + (mid - top) * (y / 0.6), mid + (bot - mid) * ((y - 0.6) / 0.4))
    img = Image.fromarray(np.repeat(grad[:, None, :], w, axis=1).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)
    d.ellipse((620, 820, 900, 1100), fill=(255, 230, 176))
    rng = np.random.default_rng(3)
    for _ in range(9):
        x0 = int(rng.uniform(0, w))
        bh = int(rng.uniform(250, 550))
        d.rectangle((x0, h - bh, x0 + 90, h), fill=(13, 8, 20))
    d.text((w // 2, 300), "ARTWORK", fill=(255, 255, 255), font=font(64), anchor="mm")
    return img


def text_image(text: str, size: int) -> Image.Image:
    f = font(size)
    l, t, r, b = f.getbbox(text)
    img = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((10 - l + 2, 10 - t + 2), text, font=f, fill=(0, 0, 0, 160))
    d.text((10 - l, 10 - t), text, font=f, fill=(255, 255, 255, 255))
    return img


def make_overlay_clip(w: int, h: int) -> Path:
    out = WORK / f"overlay_{h}.mp4"
    if out.exists():
        return out
    src = (f"gradients=s={w}x{h}:r={FPS}:d=10:c0=black:c1=0xff9040:c2=black:c3=0xff4080:"
           f"nb_colors=4:speed=0.02")
    r = run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", src, "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)])
    if r.returncode != 0:  # very old FFmpeg without the gradients source
        run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
             f"testsrc2=s={w}x{h}:r={FPS}:d=10", "-c:v", "libx264", "-preset", "veryfast",
             "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def spectrum(frame: int, bins: int = 64) -> np.ndarray:
    """Stand-in for precomputed FFT data: a cheap pure function of the frame index."""
    t = frame / FPS
    i = np.arange(bins)
    f = i / bins
    beat = max(0.0, math.cos(t * math.pi * 2 * 1.6)) ** 8
    v = (1 - f) * 0.7 * (0.55 + 0.45 * np.sin(t * 3.1 + i * 0.7)) + beat * (1 - f) * 0.5
    v += 0.2 * np.abs(np.sin(t * 5.3 + i * 1.9))
    return np.clip(v, 0.02, 1.0).astype("f4")


# --------------------------------------------------------------------------- shaders

QUAD_VS = """
#version 330 core
in vec2 in_pos; out vec2 v_uv;
void main(){ v_uv = in_pos * 0.5 + 0.5; gl_Position = vec4(in_pos, 0.0, 1.0); }
"""

NV12_FN = """
vec3 nv12(sampler2D ty, sampler2D tuv, vec2 uv){
  uv.y = 1.0 - uv.y;  // decoded frames are top-row-first
  float y = (texture(ty, uv).r * 255.0 - 16.0) / 219.0;
  vec2 c = (texture(tuv, uv).rg * 255.0 - 128.0) / 224.0;
  return clamp(vec3(y + 1.5748*c.y, y - 0.1873*c.x - 0.4681*c.y, y + 1.8556*c.x), 0.0, 1.0);
}
"""

SCENE_FS = """
#version 330 core
in vec2 v_uv; out vec4 f;
uniform sampler2D u_bg, u_art, u_ovY, u_ovUV, u_loopY, u_loopUV;
uniform vec2 u_res; uniform float u_t, u_artAspect, u_ovOpacity;
uniform int u_mode;   // 0 = full scene (A), 1 = loop pre-render (B), 2 = loop + overlay (B final)
uniform int u_ov, u_frame, u_loopFrames;
""" + NV12_FN + """
float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
void main(){
  vec3 col;
  if (u_mode == 2) {
    col = nv12(u_loopY, u_loopUV, v_uv);
  } else {
    float z = 1.0 + 0.07 * (0.5 - 0.5 * cos(6.2831853 * u_t / 60.0));
    vec2 p = (v_uv - 0.5) / z + 0.5;
    col = texture(u_bg, p).rgb * 0.65;
    float fa = u_res.x / u_res.y;
    vec2 size = u_artAspect < fa ? vec2(u_artAspect / fa, 1.0) : vec2(1.0, fa / u_artAspect);
    vec2 q = (p - 0.5) / size + 0.5;
    if (all(greaterThanEqual(q, vec2(0.0))) && all(lessThanEqual(q, vec2(1.0)))) col = texture(u_art, q).rgb;
    col += (hash(floor(v_uv * u_res) + float(u_frame % u_loopFrames) * 17.0) - 0.5) * 0.09;
  }
  if (u_mode != 1 && u_ov == 1) {
    vec3 o = nv12(u_ovY, u_ovUV, v_uv);
    col = mix(col, 1.0 - (1.0 - col) * (1.0 - o), u_ovOpacity);   // Screen blend
  }
  f = vec4(clamp(col, 0.0, 1.0), 1.0);
}
"""

DUST_VS = """
#version 330 core
uniform float u_t; uniform vec2 u_res; out float v_a;
float h(float n){ return fract(sin(n) * 43758.5453); }
void main(){
  float i = float(gl_VertexID);
  float cyc = 1.0 + floor(h(i * 3.7) * 3.0);          // whole cycles per loop -> seamless
  float ph = u_t / 60.0;
  float x = fract(h(i * 1.1) + 0.02 * sin(6.2831853 * (ph * cyc + h(i * 5.1))));
  float y = fract(h(i * 2.3) + ph * cyc);
  gl_Position = vec4(x * 2.0 - 1.0, y * 2.0 - 1.0, 0.0, 1.0);
  gl_PointSize = (2.0 + 4.0 * h(i * 7.7)) * u_res.y / 1080.0;
  v_a = 0.2 + 0.5 * h(i * 9.1);
}
"""
DUST_FS = """
#version 330 core
in float v_a; out vec4 f;
void main(){ float a = smoothstep(0.5, 0.0, length(gl_PointCoord - 0.5)) * v_a; f = vec4(vec3(1.0, 0.95, 0.84) * a, a); }
"""

VIZ_VS = """
#version 330 core
uniform float u_spec[64]; uniform vec2 u_res, u_center; uniform float u_r0, u_len, u_w;
out float v_k;
void main(){
  int bar = gl_VertexID / 6, c = gl_VertexID % 6;
  int k = bar < 32 ? bar : 63 - bar;                     // mirror low->high around the ring
  float a = float(bar) / 64.0 * 6.2831853 - 1.5707963;
  vec2 dir = vec2(cos(a), sin(a)), nrm = vec2(-dir.y, dir.x);
  float along = (c == 1 || c == 2 || c == 4) ? u_r0 + u_len * u_spec[k] : u_r0;
  float side = (c == 2 || c == 4 || c == 5) ? 0.5 : -0.5;
  vec2 px = u_center + dir * along + nrm * side * u_w;
  gl_Position = vec4(px / u_res * 2.0 - 1.0, 0.0, 1.0);
  v_k = float(k) / 32.0;
}
"""
VIZ_FS = """
#version 330 core
in float v_k; out vec4 f;
void main(){ f = vec4(mix(vec3(1.0), vec3(0.13, 0.83, 0.93), v_k), 0.9); }
"""

SPRITE_VS = """
#version 330 core
in vec2 in_pos; uniform vec4 u_rect; uniform vec2 u_res; out vec2 v_uv;
void main(){ v_uv = in_pos * 0.5 + 0.5; vec2 px = u_rect.xy + v_uv * u_rect.zw;
  gl_Position = vec4(px / u_res * 2.0 - 1.0, 0.0, 1.0); }
"""
SPRITE_FS = """
#version 330 core
in vec2 v_uv; uniform sampler2D u_tex; out vec4 f;
void main(){ f = texture(u_tex, v_uv); }
"""

# Output conversion: FBO row 0 is read first, so sample the scene upside down to get top-row-first frames.
Y_FS = """
#version 330 core
uniform sampler2D u_scene; uniform vec2 u_res; out float f;
void main(){ vec2 uv = vec2(gl_FragCoord.x / u_res.x, 1.0 - gl_FragCoord.y / u_res.y);
  vec3 c = texture(u_scene, uv).rgb; f = (16.0 + 219.0 * dot(c, vec3(0.2126, 0.7152, 0.0722))) / 255.0; }
"""
UV_FS = """
#version 330 core
uniform sampler2D u_scene; uniform vec2 u_res; out vec2 f;
void main(){ vec2 px = floor(gl_FragCoord.xy) * 2.0 + 1.0;          // centre of the 2x2 block
  vec3 c = texture(u_scene, vec2(px.x / u_res.x, 1.0 - px.y / u_res.y)).rgb;
  float u = 128.0 + 224.0 * dot(c, vec3(-0.1146, -0.3854, 0.5));
  float v = 128.0 + 224.0 * dot(c, vec3(0.5, -0.4542, -0.0458)); f = vec2(u, v) / 255.0; }
"""
FLIP_FS = """
#version 330 core
uniform sampler2D u_scene; uniform vec2 u_res; out vec4 f;
void main(){ f = texture(u_scene, vec2(gl_FragCoord.x / u_res.x, 1.0 - gl_FragCoord.y / u_res.y)); }
"""


# --------------------------------------------------------------------------- renderer


class Renderer:
    def __init__(self, ctx: moderngl.Context, w: int, h: int, art: Image.Image):
        self.ctx, self.w, self.h = ctx, w, h
        quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4"))
        prog = lambda fs, vs=QUAD_VS: ctx.program(vertex_shader=vs, fragment_shader=fs)
        self.scene_p = prog(SCENE_FS)
        self.scene_vao = ctx.vertex_array(self.scene_p, [(quad, "2f", "in_pos")])
        self.y_p, self.uv_p, self.flip_p = prog(Y_FS), prog(UV_FS), prog(FLIP_FS)
        self.y_vao = ctx.vertex_array(self.y_p, [(quad, "2f", "in_pos")])
        self.uv_vao = ctx.vertex_array(self.uv_p, [(quad, "2f", "in_pos")])
        self.flip_vao = ctx.vertex_array(self.flip_p, [(quad, "2f", "in_pos")])
        self.dust_p = ctx.program(vertex_shader=DUST_VS, fragment_shader=DUST_FS)
        self.dust_vao = ctx.vertex_array(self.dust_p, [])
        self.viz_p = ctx.program(vertex_shader=VIZ_VS, fragment_shader=VIZ_FS)
        self.viz_vao = ctx.vertex_array(self.viz_p, [])
        self.spr_p = ctx.program(vertex_shader=SPRITE_VS, fragment_shader=SPRITE_FS)
        self.spr_vao = ctx.vertex_array(self.spr_p, [(quad, "2f", "in_pos")])

        self.scene_tex = ctx.texture((w, h), 4)
        self.scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.scene_fbo = ctx.framebuffer([self.scene_tex])
        self.y_fbo = ctx.framebuffer([ctx.texture((w, h), 1)])
        self.uv_fbo = ctx.framebuffer([ctx.texture((w // 2, h // 2), 2)])
        self.rgba_fbo = ctx.framebuffer([ctx.texture((w, h), 4)])

        self.art = self._tex(art.convert("RGB"))
        cover = max(w / art.width, h / art.height)
        small = art.resize((max(1, int(art.width * cover / 4)), max(1, int(art.height * cover / 4))))
        left, top = (small.width - w // 4) // 2, (small.height - h // 4) // 2
        bg = small.crop((left, top, left + w // 4, top + h // 4)).filter(ImageFilter.GaussianBlur(8))
        self.bg = self._tex(bg.convert("RGB"))
        self.art_aspect = art.width / art.height
        self.ov = self._nv12_tex()
        self.loop = self._nv12_tex()
        self.title = self._tex(text_image("Chill Night Mix", int(64 * h / 1080)))
        self.now: moderngl.Texture | None = None
        self.now_idx = -1

    def _tex(self, img: Image.Image) -> moderngl.Texture:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        t = self.ctx.texture(img.size, len(img.getbands()), img.tobytes())
        t.filter = (moderngl.LINEAR, moderngl.LINEAR)
        return t

    def _nv12_tex(self) -> tuple[moderngl.Texture, moderngl.Texture]:
        y = self.ctx.texture((self.w, self.h), 1)
        uv = self.ctx.texture((self.w // 2, self.h // 2), 2)
        for t in (y, uv):
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
        return y, uv

    def _upload_nv12(self, tex: tuple[moderngl.Texture, moderngl.Texture], buf: bytes) -> None:
        n = self.w * self.h
        tex[0].write(buf[:n])
        tex[1].write(buf[n:])

    def draw(self, frame: int, mode: int, ov: bytes | None, loop: bytes | None, overlays: bool) -> None:
        """mode 0: everything (A) · 1: loop layers only (B pre) · 2: loop video + overlays (B final)."""
        ctx, w, h = self.ctx, self.w, self.h
        t = frame / FPS
        self.scene_fbo.use()
        ctx.disable(moderngl.BLEND)
        if ov is not None:
            self._upload_nv12(self.ov, ov)
        if loop is not None:
            self._upload_nv12(self.loop, loop)
        units = {"u_bg": self.bg, "u_art": self.art, "u_ovY": self.ov[0], "u_ovUV": self.ov[1],
                 "u_loopY": self.loop[0], "u_loopUV": self.loop[1]}
        for i, (name, tex) in enumerate(units.items()):
            tex.use(i)
            self.scene_p[name] = i
        p = self.scene_p
        p["u_res"], p["u_t"], p["u_artAspect"] = (w, h), t, self.art_aspect
        p["u_mode"], p["u_ov"], p["u_ovOpacity"] = mode, int(ov is not None), 0.45
        p["u_frame"], p["u_loopFrames"] = frame, int(LOOP_SEC * FPS)
        self.scene_vao.render(moderngl.TRIANGLE_STRIP)

        ctx.enable(moderngl.BLEND)
        if mode in (0, 1):  # dust belongs to the loop
            ctx.enable(moderngl.PROGRAM_POINT_SIZE)
            ctx.blend_func = moderngl.ONE, moderngl.ONE
            self.dust_p["u_t"], self.dust_p["u_res"] = t, (w, h)
            self.dust_vao.render(moderngl.POINTS, vertices=150)
        if overlays:
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            s = h / 1080
            v = self.viz_p
            v["u_spec"].write(spectrum(frame).tobytes())
            v["u_res"], v["u_center"] = (w, h), (w * 0.83, h * 0.5)
            v["u_r0"], v["u_len"], v["u_w"] = 90 * s, 60 * s, 4 * s
            self.viz_vao.render(moderngl.TRIANGLES, vertices=64 * 6)
            idx = int(t // 30)  # Now Playing changes -> re-rasterise text (cost is part of the test)
            if idx != self.now_idx:
                if self.now:
                    self.now.release()
                self.now = self._tex(text_image(f"{idx + 1}. Rainy Window Café", int(54 * s)))
                self.now_idx = idx
            for tex, x, y in ((self.title, 0.05 * w, h - 0.07 * h - self.title.height),
                              (self.now, 0.05 * w, 0.12 * h)):
                tex.use(0)
                self.spr_p["u_tex"], self.spr_p["u_res"] = 0, (w, h)
                self.spr_p["u_rect"] = (x, y, tex.width, tex.height)
                self.spr_vao.render(moderngl.TRIANGLE_STRIP)
        ctx.disable(moderngl.BLEND)

    def convert(self, pix: str) -> None:
        self.scene_tex.use(0)
        if pix == "nv12":
            self.y_fbo.use()
            self.y_p["u_scene"], self.y_p["u_res"] = 0, (self.w, self.h)
            self.y_vao.render(moderngl.TRIANGLE_STRIP)
            self.uv_fbo.use()
            self.uv_p["u_scene"], self.uv_p["u_res"] = 0, (self.w, self.h)
            self.uv_vao.render(moderngl.TRIANGLE_STRIP)
        else:
            self.rgba_fbo.use()
            self.flip_p["u_scene"], self.flip_p["u_res"] = 0, (self.w, self.h)
            self.flip_vao.render(moderngl.TRIANGLE_STRIP)

    def read_into(self, buf: moderngl.Buffer, pix: str) -> None:
        if pix == "nv12":
            self.y_fbo.read_into(buf, components=1, alignment=1)
            self.uv_fbo.read_into(buf, components=2, alignment=1, write_offset=self.w * self.h)
        else:
            self.rgba_fbo.read_into(buf, components=4, alignment=1)


# --------------------------------------------------------------------------- runs


@dataclass
class Config:
    height: int
    strategy: str  # "A" or "B"
    overlay: bool
    encoder: str  # "nvenc" or "x264"
    pix: str = "nv12"

    @property
    def name(self) -> str:
        return (f"{self.height}p-{self.strategy}-{'ov' if self.overlay else 'noov'}-"
                f"{self.encoder}-{self.pix}")


@dataclass
class Result:
    config: str
    height: int
    strategy: str
    overlay: bool
    encoder: str
    pix: str
    frames: int
    seconds: float
    fps: float
    x_realtime: float
    prerender_fps: float | None
    projected_3h_min: float
    file_mb_per_min: float
    monitor: dict = field(default_factory=dict)
    error: str | None = None


def render_pass(r: Renderer, frames: int, mode: int, pix: str, enc: Encoder,
                ov_src: FrameSource | None, loop_src: FrameSource | None, overlays: bool,
                preview: Path | None = None) -> float:
    """Ping-pong PBO readback: frame i is drawn while frame i-1 is copied out."""
    frame_bytes = r.w * r.h * 3 // 2 if pix == "nv12" else r.w * r.h * 4
    pbos = [r.ctx.buffer(reserve=frame_bytes) for _ in range(2)]
    t0 = time.perf_counter()
    for i in range(frames):
        r.draw(i, mode, ov_src.get() if ov_src else None, loop_src.get() if loop_src else None, overlays)
        r.convert(pix)
        r.read_into(pbos[i % 2], pix)
        if i > 0:
            enc.put(pbos[(i - 1) % 2].read())
        if preview and i == min(frames - 1, FPS):
            save_preview(r, preview)
    enc.put(pbos[(frames - 1) % 2].read())
    enc.close()
    dt = time.perf_counter() - t0
    for b in pbos:
        b.release()
    return dt


def save_preview(r: Renderer, path: Path) -> None:
    data = r.scene_fbo.read(components=3, alignment=1)
    Image.frombytes("RGB", (r.w, r.h), data).transpose(Image.FLIP_TOP_BOTTOM).save(path)


def run_config(ctx: moderngl.Context, cfg: Config, duration: float, art: Image.Image,
               cuda_dec: bool, keep: bool) -> Result:
    w, h = RESOLUTIONS[cfg.height]
    frames = int(duration * FPS)
    r = Renderer(ctx, w, h, art)
    out = WORK / f"{cfg.name}.mp4"
    mon = Monitor()
    prerender_fps = None
    pre_s = 0.0
    ov_src = loop_src = None
    try:
        if cfg.strategy == "B":
            # Pre-render ONE loop (in the real app: 60s once per project); time it separately.
            loop_frames = int(LOOP_SEC * FPS) if duration >= LOOP_SEC else frames
            loop_file = WORK / f"loop_{cfg.height}_{cfg.encoder}.mp4"
            enc = Encoder(loop_file, w, h, cfg.pix, cfg.encoder, cfg.height, hq=True)
            pre_s = render_pass(r, loop_frames, 1, cfg.pix, enc, None, None, overlays=False)
            prerender_fps = loop_frames / pre_s
            loop_src = FrameSource(loop_file, w, h, cuda_dec)
        if cfg.overlay:
            ov_src = FrameSource(make_overlay_clip(w, h), w, h, cuda_dec)
        mon.start()
        enc = Encoder(out, w, h, cfg.pix, cfg.encoder, cfg.height)
        mode = 0 if cfg.strategy == "A" else 2
        preview = RESULTS / f"preview-{cfg.name}.png"
        secs = render_pass(r, frames, mode, cfg.pix, enc, ov_src, loop_src, overlays=True, preview=preview)
        stats = mon.stop()
    finally:
        for s in (ov_src, loop_src):
            if s:
                s.close()
    fps = frames / secs
    total = MIX_SEC * FPS
    proj = total / fps + (LOOP_SEC * FPS / prerender_fps if prerender_fps else 0)
    size_mb = out.stat().st_size / 1e6
    if not keep:
        out.unlink(missing_ok=True)
    return Result(cfg.name, cfg.height, cfg.strategy, cfg.overlay, cfg.encoder, cfg.pix, frames,
                  round(secs, 2), round(fps, 1), round(fps / FPS, 2),
                  round(prerender_fps, 1) if prerender_fps else None, round(proj / 60, 1),
                  round(size_mb / (duration / 60), 1), stats)


def build_matrix(heights: list[int], encoders: list[str]) -> list[Config]:
    gpu = "nvenc" if "nvenc" in encoders else "x264"
    m: list[Config] = []
    for hgt in heights:
        m += [Config(hgt, "A", False, gpu), Config(hgt, "A", True, gpu), Config(hgt, "B", True, gpu)]
    if 1080 in heights:
        if gpu == "nvenc" and "x264" in encoders:
            m.append(Config(1080, "A", True, "x264"))  # CPU-encoder fallback reference
        m.append(Config(1080, "A", True, gpu, "rgba"))  # cost of reading back RGBA instead of NV12
    return m


def system_info(ctx: moderngl.Context) -> dict:
    info = {"host": socket.gethostname(), "os": platform.platform(), "python": sys.version.split()[0],
            "cpu": platform.processor() or platform.machine(), "cpu_count": os.cpu_count(),
            "gl_renderer": ctx.info.get("GL_RENDERER"), "gl_version": ctx.info.get("GL_VERSION"),
            "ffmpeg": ffmpeg_version()}
    if psutil:
        info["ram_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
    smi = shutil.which("nvidia-smi")
    if smi:
        q = run([smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
        info["nvidia"] = q.stdout.decode(errors="replace").strip()
    return info


def to_markdown(info: dict, results: list[Result], duration: float) -> str:
    lines = ["# Kết quả benchmark render (Spike S1)", "",
             f"- Máy: `{info.get('host')}` · {info.get('os')}",
             f"- GPU (OpenGL): **{info.get('gl_renderer')}** · nvidia-smi: {info.get('nvidia', '—')}",
             f"- CPU: {info.get('cpu')} ({info.get('cpu_count')} luồng) · RAM: {info.get('ram_gb', '?')} GB",
             f"- {info.get('ffmpeg')}",
             (f"- Mỗi cấu hình render {duration:.0f}s nội dung ở {FPS}fps. "
              "\"Dự kiến 3h\" = thời gian ước tính để render mix 3 tiếng."), "",
             "| Cấu hình | fps | × realtime | Pre-render loop fps | Dự kiến 3h | MB/phút | GPU % | CPU % | VRAM MB |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        if r.error:
            lines.append(f"| {r.config} | ❌ {r.error[:80]} | | | | | | | |")
            continue
        m = r.monitor
        lines.append(f"| {r.config} | {r.fps} | {r.x_realtime}× | {r.prerender_fps or '—'} | "
                     f"{r.projected_3h_min / 60:.1f} giờ | {r.file_mb_per_min} | "
                     f"{m.get('gpu_util_avg') or '—'} | {m.get('cpu_util_avg') or '—'} | "
                     f"{m.get('vram_mb_max') or '—'} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    global FFMPEG
    ap = argparse.ArgumentParser(description="YT Music Editor — render benchmark (Spike S1)")
    ap.add_argument("--duration", type=float, default=60, help="giây nội dung mỗi cấu hình (mặc định 60)")
    ap.add_argument("--quick", action="store_true", help="chạy nhanh: 15s mỗi cấu hình")
    ap.add_argument("--res", default="1080,1440,2160", help="ví dụ: 1080,1440")
    ap.add_argument("--encoders", default="nvenc,x264", help="nvenc,x264 (tự bỏ nvenc nếu không dùng được)")
    ap.add_argument("--keep", action="store_true", help="giữ lại file mp4 đã render trong bench/work")
    args = ap.parse_args()
    duration = 15.0 if args.quick else args.duration

    FFMPEG = find_ffmpeg()
    WORK.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    ctx = moderngl.create_standalone_context(require=330)
    info = system_info(ctx)
    print(f"GPU OpenGL : {info['gl_renderer']}\nFFmpeg     : {info['ffmpeg']}")
    if "nvidia" not in str(info["gl_renderer"]).lower():
        print("\n⚠ OpenGL KHÔNG chạy trên card NVIDIA. Với laptop: Settings → System → Display → Graphics "
              "→ thêm python.exe (trong bench\\.venv\\Scripts) → High performance, rồi chạy lại.\n")

    encoders = [e.strip() for e in args.encoders.split(",") if e.strip()]
    if "nvenc" in encoders and not probe_encoder("h264_nvenc"):
        print("⚠ h264_nvenc không dùng được → bỏ qua NVENC, chỉ đo x264.")
        encoders.remove("nvenc")
    if "x264" not in encoders and "nvenc" not in encoders:
        sys.exit("Không còn encoder nào để đo.")
    cuda_dec = "nvenc" in encoders and probe_cuda_decode()
    info["nvenc"] = "nvenc" in encoders
    info["cuda_decode"] = cuda_dec
    heights = [int(x) for x in args.res.split(",")]
    matrix = build_matrix(heights, encoders)
    art = make_artwork()
    print(f"Sẽ đo {len(matrix)} cấu hình × {duration:.0f}s. Đừng dùng máy cho việc nặng khác trong lúc chạy.\n")

    results: list[Result] = []
    for i, cfg in enumerate(matrix, 1):
        print(f"[{i}/{len(matrix)}] {cfg.name} …", end=" ", flush=True)
        try:
            res = run_config(ctx, cfg, duration, art, cuda_dec, args.keep)
            print(f"{res.fps} fps ({res.x_realtime}× realtime) → mix 3h ≈ {res.projected_3h_min / 60:.1f} giờ")
        except Exception as e:  # noqa: BLE001 — keep going: one failing config must not lose the others
            print(f"LỖI: {e}")
            res = Result(cfg.name, cfg.height, cfg.strategy, cfg.overlay, cfg.encoder, cfg.pix, 0, 0, 0, 0,
                         None, 0, 0, error=str(e))
        results.append(res)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = RESULTS / f"results-{info['host']}-{stamp}"
    base.with_suffix(".json").write_text(json.dumps(
        {"system": info, "duration": duration, "fps": FPS, "results": [asdict(r) for r in results]},
        indent=2, ensure_ascii=False), encoding="utf-8")
    md = to_markdown(info, results, duration)
    base.with_suffix(".md").write_text(md, encoding="utf-8")
    print("\n" + md)
    print(f"Đã lưu: {base}.json và .md — gửi 2 file này (và các ảnh preview-*.png) cho Claude.")


if __name__ == "__main__":
    main()
