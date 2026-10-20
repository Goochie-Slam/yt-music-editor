from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import proc
from app.core.config import Settings, find_binary
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "appdata",
        ffmpeg=find_binary("ffmpeg", "YTME_FFMPEG"),
        ffprobe=find_binary("ffprobe", "YTME_FFPROBE"),
        ytdlp=find_binary("yt-dlp", "YTME_YTDLP"),
        frontend_dist=tmp_path / "no-dist",
        extra_hosts=["testserver"],
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def projects_dir(tmp_path: Path) -> Path:
    d = tmp_path / "Dự án của tôi"  # Vietnamese + spaces on purpose
    d.mkdir()
    return d


requires_ffmpeg = pytest.mark.skipif(
    find_binary("ffmpeg", "YTME_FFMPEG") is None, reason="FFmpeg not installed"
)

FFMPEG = find_binary("ffmpeg", "YTME_FFMPEG")
FFPROBE = find_binary("ffprobe", "YTME_FFPROBE")
YTDLP = find_binary("yt-dlp", "YTME_YTDLP")

requires_ytdlp = pytest.mark.skipif(YTDLP is None, reason="yt-dlp not installed")


def make_media(path: Path, *inputs: str, args: tuple[str, ...] = ()) -> Path:
    """Fixtures are generated with lavfi, never committed (docs/CODING-GUIDE.md §8.2)."""
    assert FFMPEG is not None
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str | Path] = [FFMPEG, "-nostdin", "-v", "error", "-y"]
    for i in inputs:
        cmd += ["-f", "lavfi", "-i", i]
    r = proc.run([*cmd, *args, path], timeout=60)
    assert r.ok, r.stderr_text()
    return path


def sine(path: Path, seconds: float, freq: int = 440, *args: str) -> Path:
    return make_media(path, f"sine=frequency={freq}:duration={seconds}", args=args)


class JobCtx:
    """A JobContext stand-in for calling job functions directly."""

    def __init__(self) -> None:
        self.cancel_event = threading.Event()
        self.events: list[tuple[float, str | None]] = []

    def progress(self, fraction: float, message: str | None = None) -> None:
        self.events.append((fraction, message))

    def check_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise proc.Cancelled("job")


@pytest.fixture
def http_dir(tmp_path: Path) -> Iterator[tuple[Path, str]]:
    """A local web server: lets yt-dlp's generic extractor run without the internet."""
    import functools
    import http.server

    root = tmp_path / "www"
    root.mkdir()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a, **k: None  # type: ignore[attr-defined]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield root, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def wait_job(client: TestClient, job_id: str, timeout: float = 60) -> dict:  # type: ignore[type-arg]
    import time

    end = time.monotonic() + timeout
    while time.monotonic() < end:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] in ("done", "failed", "cancelled"):
            return job  # type: ignore[no-any-return]
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish")
