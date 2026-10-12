"""Facts about the bundled external tools (shown in Settings, used to pick the encoder)."""

from __future__ import annotations

import functools
import threading
from pathlib import Path

from app.core import proc
from app.core.errors import AppError
from app.core.jobs import JobContext


@functools.cache
def ffmpeg_version(ffmpeg: Path) -> str:
    r = proc.run([ffmpeg, "-hide_banner", "-version"], timeout=15)
    first = r.stdout.decode(errors="replace").splitlines()
    return first[0] if r.ok and first else ""


@functools.cache
def encoder_works(ffmpeg: Path, encoder: str) -> bool:
    """Compiled-in is not enough (no GPU / old driver), so do a real 0.2 s encode."""
    r = proc.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=black:s=256x256:d=0.2:r=30",
            "-c:v",
            encoder,
            "-f",
            "null",
            "-",
        ],
        timeout=30,
    )
    return r.ok


@functools.cache
def ytdlp_version(ytdlp: Path) -> str:
    r = proc.run([ytdlp, "--version"], timeout=30)
    return r.stdout.decode(errors="replace").strip() if r.ok else ""


def parse_progress_line(line: str) -> float | None:
    """FFmpeg `-progress pipe:1` → seconds of output written so far."""
    key, _, value = line.partition("=")
    if key == "out_time_us" and value.strip().isdigit():
        return int(value) / 1_000_000
    return None


def selftest(ffmpeg: Path | None, ctx: JobContext, seconds: float = 5.0) -> dict[str, str]:
    """Exercise FFmpeg + progress parsing + cancellation end to end (Settings → "Kiểm tra")."""
    if ffmpeg is None:
        raise AppError(500, "ffmpeg_missing")
    done = threading.Event()

    def on_line(line: str) -> None:
        if (t := parse_progress_line(line)) is not None:
            ctx.progress(t / seconds, f"{t:.1f}/{seconds:.0f}s")
        if line == "progress=end":
            done.set()

    r = proc.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-progress",
            "pipe:1",
            "-re",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-f",
            "null",
            "-",
        ],
        cancel=ctx.cancel_event,
        on_stdout_line=on_line,
    )
    if not r.ok:
        raise AppError(500, "ffmpeg_failed", r.stderr_text())
    return {"ffmpeg": ffmpeg_version(ffmpeg)}
