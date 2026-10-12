"""Runtime settings: where data lives, which port, which external binaries."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent
EXE = ".exe" if os.name == "nt" else ""
DEFAULT_PORT = 8765
VITE_DEV_PORT = 5173


def default_data_dir() -> Path:
    if os.name == "nt":
        return (
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "YTMusicEditor"
        )
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "YTMusicEditor"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ytme"


def find_binary(name: str, env_var: str) -> Path | None:
    """Env var → bundled backend/bin → PATH."""
    if (env := os.environ.get(env_var)) and Path(env).is_file():
        return Path(env)
    bundled = BACKEND_DIR / "bin" / f"{name}{EXE}"
    if bundled.is_file():
        return bundled
    found = shutil.which(name)
    return Path(found) if found else None


@dataclass
class Settings:
    data_dir: Path = field(default_factory=default_data_dir)
    host: str = "127.0.0.1"  # N10: never listen on the LAN
    port: int = DEFAULT_PORT
    ffmpeg: Path | None = None
    ffprobe: Path | None = None
    ytdlp: Path | None = None
    frontend_dist: Path = REPO_DIR / "frontend" / "dist"
    extra_hosts: list[str] = field(default_factory=list)  # tests add "testserver"

    @property
    def allowed_hosts(self) -> set[str]:
        ports = (self.port, VITE_DEV_PORT)
        return {f"{h}:{p}" for h in ("127.0.0.1", "localhost") for p in ports} | set(
            self.extra_hosts
        )

    @property
    def allowed_origins(self) -> set[str]:
        return {f"http://{h}" for h in self.allowed_hosts}

    @property
    def presets_dir(self) -> Path:
        return self.data_dir / "presets"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


def load_settings() -> Settings:
    s = Settings(
        ffmpeg=find_binary("ffmpeg", "YTME_FFMPEG"),
        ffprobe=find_binary("ffprobe", "YTME_FFPROBE"),
        ytdlp=find_binary("yt-dlp", "YTME_YTDLP"),
    )
    if d := os.environ.get("YTME_DATA_DIR"):
        s.data_dir = Path(d)
    if p := os.environ.get("YTME_PORT"):
        s.port = int(p)
    return s
