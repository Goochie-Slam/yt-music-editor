"""YT Music Editor backend.

Dev: `uv run uvicorn app.main:create_app --factory --port 8765 --reload`.

Packaged app: `python -m app.main` (opens the browser).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import threading
import webbrowser
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import jobs, library, presets, projects, system, ws
from app.core.config import Settings, load_settings
from app.core.errors import install_handlers
from app.core.events import EventBus
from app.core.jobs import JobManager
from app.core.presets import PresetStore
from app.core.projects import ProjectStore
from app.core.security import LocalOnlyMiddleware


def setup_logging(settings: Settings) -> None:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        settings.logs_dir / "backend.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(settings)
    bus = EventBus()
    job_manager = JobManager(bus)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        bus.bind_loop(asyncio.get_running_loop())
        yield
        job_manager.shutdown()

    app = FastAPI(title="YT Music Editor", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.bus = bus
    app.state.jobs = job_manager
    app.state.projects = ProjectStore(settings.data_dir)
    app.state.presets = PresetStore(settings.presets_dir)
    install_handlers(app)
    for r in (
        system.router,
        jobs.router,
        projects.router,
        presets.router,
        library.router,
        ws.router,
    ):
        app.include_router(r)
    if settings.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="ui")
    app.add_middleware(LocalOnlyMiddleware, settings=settings)
    return app


def main() -> None:
    import uvicorn

    ap = argparse.ArgumentParser()
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    settings = load_settings()
    url = f"http://{settings.host}:{settings.port}/"
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="warning")


if __name__ == "__main__":
    main()
