"""Library tab (F1.1 to F1.11). Routers stay thin: validate → start a job → return its id.

The frontend is the only writer of project.json. Jobs never edit the project: their result
(cache path, duration, bitrate…) comes back in the job event and the UI stores it on the item.
That way an autosave can never race a background job and overwrite its result.
"""

from __future__ import annotations

import re
from functools import partial
from pathlib import Path
from typing import Annotated, Any

import anyio
from fastapi import APIRouter, Query, Request
from pydantic import Field

from app.audio import export, ingest, tracklist, ytdlp
from app.core.config import Settings
from app.core.errors import AppError
from app.core.jobs import JobContext, JobManager, Lane
from app.core.projects import ProjectStore
from app.models.project import FileSource, Model, UrlSource

router = APIRouter(tags=["library"])

_ITEM_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
UPLOAD_DIR = Path("cache") / "uploads"


class JobStarted(Model):
    job_id: str


def _settings(request: Request) -> Settings:
    s: Settings = request.app.state.settings
    return s


def _jobs(request: Request) -> JobManager:
    j: JobManager = request.app.state.jobs
    return j


def _folder(request: Request, project_id: str) -> Path:
    store: ProjectStore = request.app.state.projects
    return store.folder_of(project_id)


def _ffmpeg(s: Settings) -> tuple[Path, Path]:
    if s.ffmpeg is None or s.ffprobe is None:
        raise AppError(500, "ffmpeg_missing")
    return s.ffmpeg, s.ffprobe


def _ytdlp_tools(s: Settings) -> ytdlp.Tools:
    if s.ytdlp is None:
        raise AppError(500, "ytdlp_missing")
    return ytdlp.Tools(s.ytdlp, s.ffmpeg, s.deno, s.node)


def _check_item_id(item_id: str) -> str:
    if not _ITEM_ID.match(item_id):  # it becomes part of a file name
        raise AppError(400, "invalid_input", f"bad item id {item_id!r}")
    return item_id


# --------------------------------------------------------------------------- paths & links


class ExpandBody(Model):
    paths: list[str] = Field(max_length=1000)


class ExpandedFile(Model):
    path: str
    name: str


class Expanded(Model):
    files: list[ExpandedFile]
    missing: list[str]


@router.post("/api/library/expand")
def expand(body: ExpandBody) -> Expanded:
    """Pasted file / folder paths → the audio and video files they contain (F1.1)."""
    files, missing = ingest.expand_paths(body.paths)
    return Expanded(files=[ExpandedFile(path=str(f), name=f.stem) for f in files], missing=missing)


class ResolveBody(Model):
    url: str = Field(min_length=4, max_length=2000, pattern=r"^https?://")


@router.post("/api/library/resolve")
def resolve(body: ResolveBody, request: Request) -> JobStarted:
    """Link → single item or playlist entries for the picker (F1.2). Runs on the light lane so it
    never waits behind three long downloads."""
    tools = _ytdlp_tools(_settings(request))

    def run(ctx: JobContext) -> dict[str, Any]:
        ctx.progress(0.1, "Đang lấy thông tin…")
        return ytdlp.resolve(tools, body.url, ctx.cancel_event)

    job = _jobs(request).submit("resolve", body.url, run, lane=Lane.LIGHT, meta={"url": body.url})
    return JobStarted(job_id=job.id)


# --------------------------------------------------------------------------- ingest


class IngestBody(Model):
    item_id: str
    title: str
    source: Annotated[FileSource | UrlSource, Field(discriminator="kind")]


def _submit_file(
    request: Request, project_id: str, item_id: str, title: str, src: Path, *, delete_after: bool
) -> JobStarted:
    ffmpeg, ffprobe = _ffmpeg(_settings(request))
    folder = _folder(request, project_id)

    def run(ctx: JobContext) -> dict[str, Any]:
        try:
            return {
                "itemId": item_id,
                **ingest.ingest_file(ffmpeg, ffprobe, folder, src, ctx).to_json(),
            }
        finally:
            if delete_after:  # a dropped file's bytes were only a transport copy
                src.unlink(missing_ok=True)

    job = _jobs(request).submit(
        "ingest", title, run, meta={"projectId": project_id, "itemId": item_id}
    )
    return JobStarted(job_id=job.id)


@router.post("/api/projects/{project_id}/library/ingest")
def start_ingest(project_id: str, body: IngestBody, request: Request) -> JobStarted:
    """Decode a file on disk, or download + decode a link, into the project's WAV cache."""
    item_id = _check_item_id(body.item_id)
    src = body.source
    if isinstance(src, FileSource):
        if src.uploaded:
            raise AppError(400, "invalid_input", "uploaded files come through /upload")
        return _submit_file(
            request, project_id, item_id, body.title, Path(src.path), delete_after=False
        )

    s = _settings(request)
    tools = _ytdlp_tools(s)
    _, ffprobe = _ffmpeg(s)
    folder = _folder(request, project_id)
    url, site, remote_id = src.url, src.site, src.remote_id

    def run(ctx: JobContext) -> dict[str, Any]:
        r = ingest.ingest_url(tools, ffprobe, folder, url, ctx, site=site, remote_id=remote_id)
        return {"itemId": item_id, **r.to_json()}

    job = _jobs(request).submit(
        "download", body.title, run, meta={"projectId": project_id, "itemId": item_id}
    )
    return JobStarted(job_id=job.id)


@router.put("/api/projects/{project_id}/library/{item_id}/upload")
async def upload(
    project_id: str,
    item_id: str,
    request: Request,
    name: Annotated[str, Query(min_length=1, max_length=260)],
) -> JobStarted:
    """A file dropped into the browser: the browser never tells us its path, so its bytes are
    streamed here, decoded like any file, then the copy is deleted."""
    _check_item_id(item_id)
    folder = _folder(request, project_id)
    ext = Path(name).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", ext):
        ext = ""
    dest = folder / UPLOAD_DIR / f"{item_id}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(dest, "wb") as f:  # chunk by chunk: a dropped 3 GB video must not sit in RAM
            async for chunk in request.stream():
                await anyio.to_thread.run_sync(f.write, chunk)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return _submit_file(request, project_id, item_id, Path(name).stem, dest, delete_after=True)


# --------------------------------------------------------------------------- tracklist


class TracklistBody(Model):
    text: str = Field(max_length=200_000)
    duration: float = Field(gt=0)


class TracklistSegment(Model):
    index: int
    title: str
    start: float
    end: float


class TracklistError(Model):
    line_no: int
    text: str
    error: tracklist.LineError


class TracklistParsed(Model):
    segments: list[TracklistSegment]
    errors: list[TracklistError]


@router.post("/api/tracklist/parse")
def parse_tracklist(body: TracklistBody) -> TracklistParsed:
    """Live preview while the user types (F1.5). One parser, here: the UI never re-implements it."""
    r = tracklist.parse(body.text, body.duration)
    return TracklistParsed(
        segments=[TracklistSegment(**vars(s)) for s in r.segments],
        errors=[TracklistError(line_no=e.line_no, text=e.text, error=e.error) for e in r.errors],
    )


# --------------------------------------------------------------------------- export


class ExportEntryBody(Model):
    title: str
    wav: str  # cacheWav of the item or of a segment's parent, relative to the project
    start: float = Field(0, ge=0)
    end: float | None = Field(None, gt=0)
    duration: float = Field(0, ge=0)


class ExportBody(Model):
    folder: str = ""  # empty = "<project>/export"
    pattern: str = Field("{index} - {title}", min_length=1, max_length=200)
    entries: list[ExportEntryBody] = Field(min_length=1, max_length=5000)


@router.post("/api/projects/{project_id}/library/export")
def start_export(project_id: str, body: ExportBody, request: Request) -> JobStarted:
    """Batch MP3 320 kbps CBR without tags (F1.4), straight from the lossless cache."""
    ffmpeg, _ = _ffmpeg(_settings(request))
    project_dir = _folder(request, project_id)
    target = Path(body.folder) if body.folder.strip() else project_dir / "export"
    if not target.is_absolute():
        raise AppError(400, "export_folder_invalid", body.folder, path=body.folder)
    export.render_names(body.pattern, ["x"])  # a bad pattern fails now, not inside the job
    if any(e.end is not None and e.end <= e.start for e in body.entries):
        raise AppError(400, "invalid_input", "segment end must be after its start")
    entries = [
        export.Entry(
            title=e.title,
            wav=ingest.resolve_in_project(project_dir, e.wav),
            start=e.start,
            end=e.end,
            duration=e.duration,
        )
        for e in body.entries
    ]
    n = len(entries)
    job = _jobs(request).submit(
        "export",
        f"Xuất {n} file MP3",
        partial(export.export_mp3, ffmpeg, entries, target, body.pattern),
        meta={"projectId": project_id},
    )
    return JobStarted(job_id=job.id)
