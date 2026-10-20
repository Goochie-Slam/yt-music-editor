"""Bring audio into a project: probe the source, decode it ONCE to a lossless WAV (F1.11).

Cache layout inside the project folder (F1.10):
    cache/audio/<key>.wav    float32 · 48 kHz · stereo (RF64 when > 4 GB)
    cache/audio/<key>.json   what we learnt about the source (duration, bitrate, format, title)

float32 rather than 16/24-bit integer: lossy sources often decode to samples above 0 dBFS. Integer
PCM would clip them here, before normalisation gets the chance to turn them down.

The key depends on the source content (not its path) plus DECODE_VERSION, so moving or renaming
a file still hits the cache, and changing the decode settings invalidates it.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import shutil
import threading
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.audio import ytdlp
from app.core import proc
from app.core.errors import AppError
from app.core.jobs import JobContext
from app.core.tools import parse_progress_line

log = logging.getLogger(__name__)

SAMPLE_RATE = 48_000
CHANNELS = 2
BYTES_PER_SECOND = SAMPLE_RATE * CHANNELS * 4  # float32
DECODE_VERSION = "f32-48k-2ch-v1"
AUDIO_DIR = Path("cache") / "audio"
LOW_BITRATE_KBPS = 160  # F1.8: the UI warns at or below this, for lossy sources only

# What a dropped folder is filtered by. A file named explicitly is always tried: ffprobe decides.
# fmt: off
SUPPORTED_EXTS = frozenset([
    "mp4", "m4v", "mkv", "mka", "mov", "avi", "webm", "flv", "wmv", "mpg", "mpeg", "ts", "3gp",
    "mp3", "wav", "flac", "m4a", "aac", "ogg", "oga", "opus", "wma", "aiff", "aif", "alac", "wv",
    "ape", "ac3", "dts", "caf",
])
# fmt: on
_PCM_LIKE = {"wav", "aiff", "aif", "caf"}
# A well-compressed FLAC can be under 160 kbps; it is still lossless and must not be flagged.
_LOSSLESS = {"flac", "alac", "wavpack", "ape", "tta", "truehd", "mlp", "shorten"}


@dataclass(frozen=True)
class Probe:
    duration: float | None
    codec: str
    container: str  # file extension, lowercase
    bitrate_kbps: int | None
    channels: int = 2

    @property
    def lossless(self) -> bool:
        return self.codec.startswith("pcm_") or self.codec in _LOSSLESS

    @property
    def format_label(self) -> str:
        codec = "pcm" if self.codec.startswith("pcm_") else self.codec
        if not self.container:
            return codec
        if codec == self.container or (codec == "pcm" and self.container in _PCM_LIKE):
            return self.container
        return f"{self.container}/{codec}"


@dataclass(frozen=True)
class IngestResult:
    cache_wav: str  # relative to the project folder, always with "/"
    duration: float
    src_bitrate_kbps: int | None
    src_format: str
    src_lossless: bool = False
    title: str | None = None  # only known for links

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        return {
            "cacheWav": d["cache_wav"],
            "duration": d["duration"],
            "srcBitrateKbps": d["src_bitrate_kbps"],
            "srcFormat": d["src_format"],
            "srcLossless": d["src_lossless"],
            "title": d["title"],
        }


# --------------------------------------------------------------------------- probe


def _kbps(value: object) -> int | None:
    try:
        bps = float(str(value))
    except ValueError:
        return None
    return round(bps / 1000) if bps > 0 else None


def _duration(value: object) -> float | None:
    try:
        d = float(str(value))
    except ValueError:
        return None
    return d if d > 0 else None


def probe(ffprobe: Path, path: Path) -> Probe:
    if not path.is_file():
        raise AppError(404, "file_not_found", str(path), path=str(path))
    r = proc.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        timeout=60,
    )
    if not r.ok:
        raise AppError(422, "unsupported_file", r.stderr_text())
    try:
        info = json.loads(r.stdout.decode("utf-8", errors="replace"))
    except ValueError as e:
        raise AppError(422, "unsupported_file", str(e)) from e
    streams: list[dict[str, Any]] = info.get("streams") or []
    fmt: dict[str, Any] = info.get("format") or {}
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio:
        raise AppError(422, "no_audio", str(path))
    a = audio[0]  # the stream `-map 0:a:0` decodes
    tags = {k.lower(): v for k, v in (a.get("tags") or {}).items()}
    kbps = _kbps(a.get("bit_rate")) or _kbps(tags.get("bps")) or _kbps(tags.get("bps-eng"))
    only_audio = all(s.get("codec_type") == "audio" for s in streams) and len(audio) == 1
    if kbps is None and only_audio:
        kbps = _kbps(fmt.get("bit_rate"))  # e.g. opus in webm: only the container knows
    return Probe(
        duration=_duration(fmt.get("duration")) or _duration(a.get("duration")),
        codec=str(a.get("codec_name") or "?"),
        container=path.suffix.lower().lstrip("."),
        bitrate_kbps=kbps,
        channels=int(a.get("channels") or 2),
    )


# --------------------------------------------------------------------------- cache


def _digest(*parts: bytes) -> str:
    h = hashlib.sha256(DECODE_VERSION.encode())
    for p in parts:
        h.update(len(p).to_bytes(8, "little"))
        h.update(p)
    return h.hexdigest()[:24]


def file_key(path: Path, sample: int = 1 << 20) -> str:
    """Size + first and last MiB: reading a 3 GB video in full just to name it is too slow."""
    size = path.stat().st_size
    with open(path, "rb") as f:
        head = f.read(sample)
        f.seek(max(0, size - sample))
        tail = f.read(sample)
    return _digest(str(size).encode(), head, tail)


def url_key(url: str, site: str = "", remote_id: str = "") -> str:
    """The site's own id, so youtu.be/x and youtube.com/watch?v=x share one download. Not for
    yt-dlp's generic extractor: its "id" is just the file name (a/mix.mp3 and b/mix.mp3)."""
    site = site.lower()
    ident = f"{site}:{remote_id}" if site and site != "generic" and remote_id else url.strip()
    return _digest(ident.encode())


_key_locks: dict[str, threading.RLock] = {}
_key_locks_guard = threading.Lock()


@contextlib.contextmanager
def _locked(project_dir: Path, key: str, ctx: JobContext) -> Iterator[None]:
    """One import per cache entry at a time: the same file dropped twice, or a playlist that has a
    song twice, must not write the same temp file from two jobs. The second waits, then hits the
    cache. Re-entrant: a link's download step holds it while it decodes."""
    with _key_locks_guard:
        lock = _key_locks.setdefault(f"{project_dir.resolve()}|{key}", threading.RLock())
    while not lock.acquire(timeout=0.2):
        ctx.check_cancelled()
    try:
        yield
    finally:
        lock.release()


def _paths(project_dir: Path, key: str) -> tuple[Path, Path]:
    d = project_dir / AUDIO_DIR
    return d / f"{key}.wav", d / f"{key}.json"


def cached(project_dir: Path, key: str) -> IngestResult | None:
    wav, meta = _paths(project_dir, key)
    if not (wav.is_file() and meta.is_file()):
        return None
    try:
        m = json.loads(meta.read_text(encoding="utf-8"))
        return IngestResult(
            cache_wav=(AUDIO_DIR / wav.name).as_posix(),
            duration=float(m["duration"]),
            src_bitrate_kbps=m.get("srcBitrateKbps"),
            src_format=str(m.get("srcFormat", "")),
            src_lossless=bool(m.get("srcLossless", False)),
            title=m.get("title"),
        )
    except (OSError, ValueError, KeyError):
        return None  # unreadable sidecar: decode again


def _store_meta(meta: Path, result: IngestResult) -> None:
    tmp = meta.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result.to_json(), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, meta)


# --------------------------------------------------------------------------- decode


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def ensure_free_space(folder: Path, need: float) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(folder).free
    if free < need:
        raise AppError(
            507,
            "disk_full",
            f"{folder}: need {need:.0f}, free {free}",
            need=human_bytes(need),
            free=human_bytes(free),
        )


def wav_duration(ffprobe: Path, wav: Path) -> float:
    r = proc.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav],
        timeout=60,
    )
    d = _duration(r.stdout.decode(errors="replace").strip()) if r.ok else None
    if d is None:
        raise AppError(500, "decode_failed", f"cannot read duration of {wav}: {r.stderr_text()}")
    return d


def decode(
    ffmpeg: Path,
    src: Path,
    dst: Path,
    duration_hint: float | None,
    cancel: threading.Event | None,
    on_progress: Callable[[float], None],
    channels: int = 2,
) -> None:
    """Source → float32 48 kHz stereo WAV. Written to a temp name, so the cache never holds a
    half-decoded file (cancel, crash, full disk)."""
    tmp = dst.with_name(dst.stem + ".part.wav")

    def on_line(line: str) -> None:
        t = parse_progress_line(line)
        if t is not None and duration_hint:
            on_progress(min(1.0, t / duration_hint))

    # FFmpeg would pan mono to stereo at -3 dB; players put mono on both speakers at full level.
    upmix: list[proc.Arg] = ["-af", "pan=stereo|c0=c0|c1=c0"] if channels == 1 else []
    # fmt: off
    args: list[proc.Arg] = [
        ffmpeg, "-nostdin", "-hide_banner", "-v", "error", "-nostats",
        "-progress", "pipe:1", "-y", "-i", src,
        "-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "-1", *upmix,
        "-ac", str(CHANNELS), "-ar", str(SAMPLE_RATE),
        "-c:a", "pcm_f32le", "-rf64", "auto", "-f", "wav", tmp,
    ]
    # fmt: on
    try:
        r = proc.run(args, cancel=cancel, on_stdout_line=on_line)
        if not r.ok:
            raise AppError(500, "decode_failed", r.stderr_text())
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)


def ingest_file(
    ffmpeg: Path,
    ffprobe: Path,
    project_dir: Path,
    src: Path,
    ctx: JobContext,
    *,
    span: tuple[float, float] = (0.0, 1.0),
    title: str | None = None,
    key: str | None = None,
) -> IngestResult:
    """Probe + decode a file on disk. `span` maps this step onto part of the job's progress bar
    (a link spends the first part downloading)."""
    lo, hi = span
    ctx.progress(lo, "Đang đọc file…")
    if not src.is_file():
        raise AppError(404, "file_not_found", str(src), path=str(src))
    key = key or file_key(src)
    with _locked(project_dir, key, ctx):
        return _ingest_file(ffmpeg, ffprobe, project_dir, src, ctx, lo, hi, title, key)


def _ingest_file(
    ffmpeg: Path,
    ffprobe: Path,
    project_dir: Path,
    src: Path,
    ctx: JobContext,
    lo: float,
    hi: float,
    title: str | None,
    key: str,
) -> IngestResult:
    if (hit := cached(project_dir, key)) is not None:
        return hit
    info = probe(ffprobe, src)
    wav, meta = _paths(project_dir, key)
    if info.duration:
        ensure_free_space(wav.parent, info.duration * BYTES_PER_SECOND * 1.02)
    else:
        wav.parent.mkdir(parents=True, exist_ok=True)

    def on_fraction(f: float) -> None:
        ctx.progress(lo + (hi - lo) * f, f"Đang giải mã… {round(f * 100)}%")

    ctx.progress(lo, "Đang giải mã…")
    decode(ffmpeg, src, wav, info.duration, ctx.cancel_event, on_fraction, info.channels)
    result = IngestResult(
        cache_wav=(AUDIO_DIR / wav.name).as_posix(),
        duration=wav_duration(ffprobe, wav),
        src_bitrate_kbps=info.bitrate_kbps,
        src_format=info.format_label,
        src_lossless=info.lossless,
        title=title,
    )
    _store_meta(meta, result)
    return result


def resolve_in_project(project_dir: Path, rel: str) -> Path:
    """A path the UI sent back to us must stay inside the project folder."""
    root = project_dir.resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root):
        raise AppError(400, "outside_project", rel)
    return p


def expand_paths(raw: list[str], limit: int = 5000) -> tuple[list[Path], list[str]]:
    """Pasted paths → audio/video files. Folders are walked recursively and filtered by
    extension; a file named explicitly is always kept. Returns (files, missing)."""
    files: list[Path] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for text in raw:
        s = text.strip().strip('"').strip("'").strip()
        if not s:
            continue
        p = Path(s).expanduser()
        if not p.is_absolute():
            missing.append(s)  # relative to what? the backend's cwd means nothing to the user
        elif p.is_file():
            found = [p]
        elif p.is_dir():
            found = sorted(
                (f for f in p.rglob("*") if f.is_file() and f.suffix.lower()[1:] in SUPPORTED_EXTS),
                key=lambda f: [part.casefold() for part in f.relative_to(p).parts],
            )
        else:
            missing.append(s)
            continue
        for f in found:
            r = f.resolve()
            if r not in seen and len(files) < limit:
                seen.add(r)
                files.append(f)
    return files, missing


DOWNLOAD_SHARE = 0.85  # of a link's progress bar; decoding takes the rest


def ingest_url(
    tools: ytdlp.Tools,
    ffprobe: Path,
    project_dir: Path,
    url: str,
    ctx: JobContext,
    *,
    site: str = "",
    remote_id: str = "",
) -> IngestResult:
    """Download (yt-dlp) → decode. The downloaded original is deleted once the WAV exists."""
    assert tools.ffmpeg is not None
    key = url_key(url, site, remote_id)
    with _locked(project_dir, key, ctx):
        return _ingest_url(tools, ffprobe, project_dir, url, ctx, key)


def _ingest_url(
    tools: ytdlp.Tools, ffprobe: Path, project_dir: Path, url: str, ctx: JobContext, key: str
) -> IngestResult:
    assert tools.ffmpeg is not None
    if (hit := cached(project_dir, key)) is not None:
        return hit
    ctx.progress(0.0, "Đang tải…")

    def on_fraction(f: float) -> None:
        ctx.progress(DOWNLOAD_SHARE * f, f"Đang tải… {round(f * 100)}%")

    dl = ytdlp.download(
        tools, url, project_dir / "cache" / "dl", key, on_fraction, ctx.cancel_event
    )
    try:
        return ingest_file(
            tools.ffmpeg,
            ffprobe,
            project_dir,
            dl.path,
            ctx,
            span=(DOWNLOAD_SHARE, 1.0),
            title=dl.title,
            key=key,
        )
    finally:
        dl.path.unlink(missing_ok=True)


def sweep_temp(project_dir: Path) -> int:
    """At startup, before any job runs: drop copies of dropped files and half-decoded WAVs left
    behind when the app was closed mid-import. Downloads (cache/dl) stay: yt-dlp resumes them."""
    removed = 0
    leftovers = [*(project_dir / "cache" / "uploads").glob("*")]
    leftovers += (project_dir / AUDIO_DIR).glob("*.part.wav")
    for f in leftovers:
        try:
            f.unlink()
            removed += 1
        except OSError:
            log.warning("could not remove leftover %s", f)
    return removed
