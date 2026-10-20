"""Final encodes — the only place lossy files are made (F1.11).

Library export (F1.4): MP3 320 kbps CBR, no tags at all, named by a user pattern.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.audio.ingest import ensure_free_space
from app.core import proc
from app.core.errors import AppError
from app.core.jobs import JobContext
from app.core.tools import parse_progress_line
from app.messages import message

MP3_BYTES_PER_SECOND = 320_000 / 8
_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM\d|LPT\d)(\..*)?$", re.I)
MAX_NAME = 150  # leaves room for the folder within Windows' 260-character path limit


@dataclass(frozen=True)
class Entry:
    title: str
    wav: Path
    start: float = 0.0
    end: float | None = None  # None = to the end of the WAV
    duration: float = 0.0  # for progress and the disk-space check


def safe_filename(name: str, fallback: str = "untitled") -> str:
    cleaned = " ".join(_INVALID.sub("_", name).split()).rstrip(". ")
    if not cleaned:
        cleaned = fallback
    if _RESERVED.match(cleaned):
        cleaned = f"_{cleaned}"
    return cleaned[:MAX_NAME].rstrip(". ")


def render_names(pattern: str, titles: list[str]) -> list[str]:
    """{index} is zero-padded to the batch size (01…12, 001…120). Plain replace, not
    str.format: the pattern is user text."""
    if "{title}" not in pattern and "{index}" not in pattern:
        raise AppError(400, "pattern_invalid", pattern)
    width = max(2, len(str(len(titles))))
    return [
        safe_filename(pattern.replace("{index}", str(i).zfill(width)).replace("{title}", t))
        for i, t in enumerate(titles, start=1)
    ]


def unique_path(folder: Path, stem: str, ext: str, taken: set[str]) -> Path:
    """Never overwrite: an existing file — or one written earlier in this batch — gets (2), (3)…"""
    n, name = 1, stem
    while name.casefold() in taken or (folder / f"{name}{ext}").exists():
        n += 1
        name = f"{stem} ({n})"
    taken.add(name.casefold())
    return folder / f"{name}{ext}"


def mp3_args(ffmpeg: Path, entry: Entry, out: Path) -> list[proc.Arg]:
    # -ss before -i on PCM is sample-exact; no ID3v2, no ID3v1, no copied metadata
    seek: list[proc.Arg] = ["-ss", f"{entry.start:.6f}"] if entry.start > 0 else []
    span: list[proc.Arg] = [] if entry.end is None else ["-t", f"{entry.end - entry.start:.6f}"]
    # fmt: off
    return [
        ffmpeg, "-nostdin", "-hide_banner", "-v", "error", "-nostats", "-progress", "pipe:1",
        "-y", *seek, "-i", entry.wav, *span, "-map", "0:a:0",
        "-c:a", "libmp3lame", "-b:a", "320k",
        "-map_metadata", "-1", "-id3v2_version", "0", "-write_id3v1", "0",
        "-f", "mp3", out,
    ]
    # fmt: on


def export_mp3(
    ffmpeg: Path, entries: list[Entry], folder: Path, pattern: str, ctx: JobContext
) -> dict[str, Any]:
    if not entries:
        raise AppError(400, "nothing_selected")
    names = render_names(pattern, [e.title for e in entries])
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise AppError(400, "export_folder_invalid", str(e), path=str(folder)) from e
    total = sum(e.duration for e in entries) or float(len(entries))
    ensure_free_space(folder, total * MP3_BYTES_PER_SECOND * 1.02 + 1_000_000)

    written: list[str] = []
    failed: list[dict[str, str]] = []
    taken: set[str] = set()
    done = 0.0
    for i, (entry, stem) in enumerate(zip(entries, names, strict=True), start=1):
        weight = entry.duration or 1.0
        out = unique_path(folder, stem, ".mp3", taken)
        tmp = out.with_name(out.stem + ".part.mp3")
        label = f"{i}/{len(entries)} · {out.name}"
        ctx.progress(done / total, label)

        def on_line(line: str, base: float = done, w: float = weight, lab: str = label) -> None:
            t = parse_progress_line(line)
            if t is not None:
                ctx.progress((base + min(w, t)) / total, lab)

        try:
            r = proc.run(
                mp3_args(ffmpeg, entry, tmp), cancel=ctx.cancel_event, on_stdout_line=on_line
            )
            if r.ok:
                os.replace(tmp, out)
                written.append(out.name)
            else:  # one bad file must not stop the other 24
                failed.append(
                    {
                        "title": entry.title,
                        "message": message("ffmpeg_failed"),
                        "detail": r.stderr_text(300),
                    }
                )
        finally:
            tmp.unlink(missing_ok=True)
        done += weight
    return {"folder": str(folder), "files": written, "failed": failed}
