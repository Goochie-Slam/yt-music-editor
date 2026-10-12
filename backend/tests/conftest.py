from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, find_binary
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "appdata",
        ffmpeg=find_binary("ffmpeg", "YTME_FFMPEG"),
        ffprobe=find_binary("ffprobe", "YTME_FFPROBE"),
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
