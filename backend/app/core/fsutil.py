"""File helpers: atomic writes with rotating backups, Windows-safe folder names."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

BACKUPS = 5
_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def atomic_write_text(path: Path, text: str, backups: int = BACKUPS) -> None:
    """Never leaves a half-written file: write a temp file next to it, then os.replace.

    The previous content is kept as path.bak1 … path.bak{backups} (newest first).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if backups and path.exists():
        for i in range(backups, 1, -1):
            older = path.with_name(f"{path.name}.bak{i - 1}")
            if older.exists():
                os.replace(older, path.with_name(f"{path.name}.bak{i}"))
        shutil.copy2(path, path.with_name(f"{path.name}.bak1"))
    tmp = path.with_name(f"{path.name}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def safe_folder_name(name: str, fallback: str = "project") -> str:
    """Keep Vietnamese letters and spaces; drop what Windows forbids in file names."""
    cleaned = _INVALID.sub("", name).strip().rstrip(". ")
    if not cleaned or cleaned.upper() in _RESERVED:
        return fallback
    return cleaned[:80]


def unique_dir(parent: Path, name: str) -> Path:
    candidate = parent / name
    n = 2
    while candidate.exists():
        candidate = parent / f"{name} ({n})"
        n += 1
    return candidate
