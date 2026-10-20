from __future__ import annotations

import platform
import sys
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from app import __version__
from app.audio import ingest, ytdlp
from app.core import proc, tools
from app.core.config import Settings
from app.core.errors import AppError
from app.core.jobs import JobContext
from app.models.project import Model

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("")
def system_info(request: Request) -> dict[str, Any]:
    s: Settings = request.app.state.settings
    ffmpeg: dict[str, Any] = {"path": str(s.ffmpeg) if s.ffmpeg else None}
    if s.ffmpeg:
        ffmpeg["version"] = tools.ffmpeg_version(s.ffmpeg)
        ffmpeg["nvenc"] = tools.encoder_works(s.ffmpeg, "h264_nvenc")
        ffmpeg["x264"] = tools.encoder_works(s.ffmpeg, "libx264")
    ytdlp_info: dict[str, Any] = {"path": str(s.ytdlp) if s.ytdlp else None}
    if s.ytdlp:
        ytdlp_info["version"] = tools.ytdlp_version(s.ytdlp)
    return {
        "appVersion": __version__,
        "python": sys.version.split()[0],
        "os": platform.platform(),
        "dataDir": str(s.data_dir),
        "defaultProjectsDir": str(s.default_projects_dir),
        "ffmpeg": ffmpeg,
        "ffprobe": {"path": str(s.ffprobe) if s.ffprobe else None},
        "ytdlp": ytdlp_info,
        "jsRuntime": {
            "deno": str(s.deno) if s.deno else None,
            "node": str(s.node) if s.node else None,
        },
        "supportedExtensions": sorted(ingest.SUPPORTED_EXTS),
        "lowBitrateKbps": ingest.LOW_BITRATE_KBPS,
    }


@router.post("/selftest")
def run_selftest(request: Request) -> dict[str, str]:
    s: Settings = request.app.state.settings
    job = request.app.state.jobs.submit(
        "selftest", "Kiểm tra FFmpeg", partial(tools.selftest, s.ffmpeg)
    )
    return {"jobId": job.id}


@router.post("/ytdlp/update")
def update_ytdlp(request: Request) -> dict[str, str]:
    """F1.9 — sites change, an old yt-dlp stops working."""
    s: Settings = request.app.state.settings
    if s.ytdlp is None:
        raise AppError(500, "ytdlp_missing")
    exe = s.ytdlp

    def run(ctx: JobContext) -> dict[str, str]:
        ctx.progress(0.1, "Đang kiểm tra bản mới…")
        try:
            return {"message": ytdlp.update(exe, ctx.cancel_event)}
        finally:
            tools.ytdlp_version.cache_clear()

    job = request.app.state.jobs.submit("ytdlp-update", "Cập nhật yt-dlp", run)
    return {"jobId": job.id}


class FolderBody(Model):
    path: str


@router.post("/open-folder", status_code=204)
def open_folder(body: FolderBody) -> None:
    """Show an export folder in Explorer. The app runs on the user's own desktop."""
    folder = Path(body.path)
    if not folder.is_dir():
        raise AppError(404, "folder_not_found", body.path, path=body.path)
    proc.open_folder(folder)
