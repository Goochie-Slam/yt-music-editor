from __future__ import annotations

import platform
import sys
from functools import partial
from typing import Any

from fastapi import APIRouter, Request

from app import __version__
from app.core import tools
from app.core.config import Settings

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("")
def system_info(request: Request) -> dict[str, Any]:
    s: Settings = request.app.state.settings
    ffmpeg: dict[str, Any] = {"path": str(s.ffmpeg) if s.ffmpeg else None}
    if s.ffmpeg:
        ffmpeg["version"] = tools.ffmpeg_version(s.ffmpeg)
        ffmpeg["nvenc"] = tools.encoder_works(s.ffmpeg, "h264_nvenc")
        ffmpeg["x264"] = tools.encoder_works(s.ffmpeg, "libx264")
    ytdlp: dict[str, Any] = {"path": str(s.ytdlp) if s.ytdlp else None}
    if s.ytdlp:
        ytdlp["version"] = tools.ytdlp_version(s.ytdlp)
    return {
        "appVersion": __version__,
        "python": sys.version.split()[0],
        "os": platform.platform(),
        "dataDir": str(s.data_dir),
        "defaultProjectsDir": str(s.default_projects_dir),
        "ffmpeg": ffmpeg,
        "ffprobe": {"path": str(s.ffprobe) if s.ffprobe else None},
        "ytdlp": ytdlp,
    }


@router.post("/selftest")
def run_selftest(request: Request) -> dict[str, str]:
    s: Settings = request.app.state.settings
    job = request.app.state.jobs.submit(
        "selftest", "Kiểm tra FFmpeg", partial(tools.selftest, s.ffmpeg)
    )
    return {"jobId": job.id}
