"""Links via the standalone yt-dlp executable (F1.2, F1.9).

The .exe — not the Python package — because `yt-dlp -U` can then update it in place when a site
changes (YouTube does, often). Everything goes through core/proc.py like any other process.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core import proc
from app.core.errors import AppError

RESOLVE_TIMEOUT = 180  # a 500-song playlist takes a while even with --flat-playlist
UNAVAILABLE_TITLES = {"[private video]", "[deleted video]", "[unavailable video]"}


@dataclass(frozen=True)
class Tools:
    ytdlp: Path
    ffmpeg: Path | None = None
    deno: Path | None = None
    node: Path | None = None

    def base(self) -> list[str | Path]:
        args: list[str | Path] = [self.ytdlp, "--ignore-config", "--encoding", "utf-8"]
        # YouTube needs a JS runtime. Only Deno is on by default; Node (which the dev setup
        # already requires) is enabled explicitly. Deno keeps priority when both exist.
        if self.deno:
            args += ["--js-runtimes", f"deno:{self.deno}"]
        if self.node:
            args += ["--js-runtimes", f"node:{self.node}"]
        if self.ffmpeg:
            args += ["--ffmpeg-location", self.ffmpeg]
        return args


# --------------------------------------------------------------------------- errors

_JS_RUNTIME = re.compile(r"no supported javascript runtime", re.I)
# First match wins, so specific causes come before generic ones.
_ERRORS: list[tuple[str, re.Pattern[str]]] = [
    ("yt_bot", re.compile(r"not a bot", re.I)),
    ("yt_age", re.compile(r"confirm your age|age[- ]restricted|inappropriate for some", re.I)),
    ("yt_private", re.compile(r"private video|video is private", re.I)),
    ("yt_members", re.compile(r"members[- ]only|join this channel|requires payment", re.I)),
    ("yt_drm", re.compile(r"\bDRM\b")),
    ("yt_geo", re.compile(r"available in your country|geo[- ]?restrict", re.I)),
    ("yt_live", re.compile(r"live event will begin|premieres in|is not yet available", re.I)),
    ("yt_rate_limited", re.compile(r"HTTP Error 429|too many requests", re.I)),
    ("yt_not_found", re.compile(r"HTTP Error 404", re.I)),
    ("yt_unsupported", re.compile(r"unsupported url", re.I)),
    (
        "yt_unavailable",
        re.compile(r"unavailable|has been removed|no longer available|been terminated", re.I),
    ),
    ("yt_js_runtime", _JS_RUNTIME),
    (
        "yt_network",
        re.compile(
            r"getaddrinfo|name resolution|timed out|connection (refused|reset)|network is "
            r"unreachable|unable to connect|ssl",
            re.I,
        ),
    ),
]
_PREFIX = re.compile(r"^ERROR:\s*(\[[^\]]+\]\s*)?([\w-]+:\s*)?")


def error_from_output(stderr: str) -> AppError:
    errors = [ln for ln in stderr.splitlines() if ln.startswith("ERROR:")]
    text = "\n".join(errors) or stderr
    for code, pattern in _ERRORS:
        if pattern.search(text):
            return AppError(502, code, stderr[-2000:])
    # The JS-runtime problem shows up as a WARNING, with a vaguer ERROR after it.
    if _JS_RUNTIME.search(stderr):
        return AppError(502, "yt_js_runtime", stderr[-2000:])
    first = errors[0] if errors else (stderr.strip().splitlines() or ["?"])[-1]
    reason = _PREFIX.sub("", first).strip()[:200]
    return AppError(502, "yt_failed", stderr[-2000:], reason=reason)


def _require_ok(r: proc.ProcResult) -> None:
    if not r.ok:
        raise error_from_output(r.stderr.decode("utf-8", errors="replace"))


# --------------------------------------------------------------------------- resolve


def _site(info: dict[str, Any], fallback: str = "") -> str:
    return str(info.get("ie_key") or info.get("extractor_key") or fallback).lower()


def _entry(e: dict[str, Any], fallback_site: str) -> dict[str, Any]:
    url = str(e.get("webpage_url") or e.get("url") or "")
    title = str(e.get("title") or url)
    return {
        "url": url,
        "title": title,
        "duration": e.get("duration"),
        "site": _site(e, fallback_site),
        "remoteId": str(e.get("id") or ""),
        "available": bool(url) and title.lower() not in UNAVAILABLE_TITLES,
    }


def parse_resolve(stdout: str, url: str) -> dict[str, Any]:
    lines = [ln for ln in stdout.splitlines() if ln.startswith("{")]
    if not lines:
        raise AppError(502, "yt_failed", stdout[-2000:], reason="no JSON")
    info: dict[str, Any] = json.loads(lines[-1])
    site = _site(info)
    if info.get("_type") == "playlist":
        entries = [_entry(e, site) for e in info.get("entries") or [] if isinstance(e, dict)]
        return {"kind": "playlist", "title": str(info.get("title") or url), "entries": entries}
    single = _entry(info, site)
    single["url"] = str(info.get("webpage_url") or info.get("original_url") or url)
    return {"kind": "single", "title": single["title"], "entries": [single]}


def resolve(tools: Tools, url: str, cancel: threading.Event | None = None) -> dict[str, Any]:
    """One link → {kind: single|playlist, title, entries[]}. --flat-playlist keeps a playlist
    quick: entries are listed, not each fully extracted."""
    r = proc.run(
        [*tools.base(), "-J", "--flat-playlist", "--", url], cancel=cancel, timeout=RESOLVE_TIMEOUT
    )
    _require_ok(r)
    return parse_resolve(r.stdout.decode("utf-8", errors="replace"), url)


# --------------------------------------------------------------------------- download


def parse_progress(line: str) -> float | None:
    """Our --progress-template line: "[dl] <downloaded> <total> <estimate>" ("NA" if unknown)."""
    if not line.startswith("[dl] "):
        return None
    parts = line[5:].split()
    if len(parts) != 3 or not parts[0].isdigit():
        return None
    total = next((int(p) for p in parts[1:] if p.isdigit() and int(p) > 0), None)
    return min(1.0, int(parts[0]) / total) if total else None


@dataclass(frozen=True)
class Downloaded:
    path: Path
    title: str
    site: str
    remote_id: str


def download(
    tools: Tools,
    url: str,
    out_dir: Path,
    stem: str,
    on_progress: Callable[[float], None],
    cancel: threading.Event | None = None,
) -> Downloaded:
    """Best audio-only format, as is — our own FFmpeg step decodes it (no -x re-encode).

    yt-dlp keeps a .part file when cancelled and resumes it on the next try."""
    out_dir.mkdir(parents=True, exist_ok=True)
    info: dict[str, Any] = {}
    final: list[str] = []

    def on_line(line: str) -> None:
        if (f := parse_progress(line)) is not None:
            on_progress(f)
        elif line.startswith("[info] "):
            info.update(json.loads(line[7:]))
        elif line.startswith("[file] "):
            final.append(line[7:])

    template = str(out_dir / f"{stem}.%(ext)s").replace("%", "%%").replace("%%(ext)s", "%(ext)s")
    # fmt: off
    args = [
        *tools.base(), "--no-playlist", "-f", "bestaudio/best", "--no-simulate",
        "--progress", "--newline", "--progress-template",
        "download:[dl] %(progress.downloaded_bytes)s %(progress.total_bytes)s "
        "%(progress.total_bytes_estimate)s",
        "--print", "before_dl:[info] %(.{id,title,extractor_key})j",
        "--print", "after_move:[file] %(filepath)s",
        "-o", template, "--", url,
    ]
    # fmt: on
    r = proc.run(args, cancel=cancel, on_stdout_line=on_line)
    _require_ok(r)
    if not final or not Path(final[-1]).is_file():
        raise AppError(502, "yt_failed", r.stderr_text(), reason="no output file")
    return Downloaded(
        path=Path(final[-1]),
        title=str(info.get("title") or url),
        site=str(info.get("extractor_key") or "").lower(),
        remote_id=str(info.get("id") or ""),
    )


# --------------------------------------------------------------------------- update


def update(ytdlp: Path, cancel: threading.Event | None = None) -> str:
    """`yt-dlp -U` (F1.9). Returns yt-dlp's own last line, e.g. "yt-dlp is up to date (…)"."""
    r = proc.run([ytdlp, "-U"], cancel=cancel, timeout=300)
    text = (r.stdout + b"\n" + r.stderr).decode("utf-8", errors="replace")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not r.ok:
        raise AppError(502, "ytdlp_update_failed", text[-2000:])
    return lines[-1] if lines else ""
