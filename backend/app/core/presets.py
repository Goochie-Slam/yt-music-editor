"""Transition presets: 5 built-in (read-only) + the user's own, shared by all projects.

F2.10, F5.3.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.core.errors import AppError
from app.core.fsutil import atomic_write_text
from app.core.util import new_id
from app.models.preset import TransitionPreset, TransitionPresetIn

BUILTIN_FILE = Path(__file__).resolve().parents[1] / "presets" / "transitions.json"
_LIST = TypeAdapter(list[TransitionPreset])


def builtin_transitions() -> list[TransitionPreset]:
    items = _LIST.validate_json(BUILTIN_FILE.read_text(encoding="utf-8"))
    return [p.model_copy(update={"builtin": True}) for p in items]


class PresetStore:
    def __init__(self, presets_dir: Path):
        self._file = presets_dir / "transitions.json"
        self._lock = threading.Lock()

    def _user(self) -> list[TransitionPreset]:
        if not self._file.exists():
            return []
        try:
            return _LIST.validate_json(self._file.read_text(encoding="utf-8"))
        except ValidationError:
            return []

    def _save(self, items: list[TransitionPreset]) -> None:
        data = [p.model_dump(mode="json") for p in items]
        atomic_write_text(self._file, json.dumps(data, ensure_ascii=False, indent=1))

    def list(self) -> list[TransitionPreset]:
        return [*builtin_transitions(), *self._user()]

    def _check_name(self, name: str, ignore_id: str | None = None) -> None:
        if any(p.name.casefold() == name.casefold() and p.id != ignore_id for p in self.list()):
            raise AppError(409, "preset_name_taken", name, name=name)

    def create(self, data: TransitionPresetIn) -> TransitionPreset:
        with self._lock:
            self._check_name(data.name)
            preset = TransitionPreset(id=f"user-{new_id(8)}", **data.model_dump())
            self._save([*self._user(), preset])
        return preset

    def update(self, preset_id: str, data: TransitionPresetIn) -> TransitionPreset:
        with self._lock:
            if any(p.id == preset_id for p in builtin_transitions()):
                raise AppError(403, "preset_builtin", preset_id)
            items = self._user()
            idx = next((i for i, p in enumerate(items) if p.id == preset_id), None)
            if idx is None:
                raise AppError.not_found("preset", preset_id)
            self._check_name(data.name, ignore_id=preset_id)
            items[idx] = TransitionPreset(id=preset_id, **data.model_dump())
            self._save(items)
            return items[idx]

    def delete(self, preset_id: str) -> None:
        with self._lock:
            if any(p.id == preset_id for p in builtin_transitions()):
                raise AppError(403, "preset_builtin", preset_id)
            items = self._user()
            kept = [p for p in items if p.id != preset_id]
            if len(kept) == len(items):
                raise AppError.not_found("preset", preset_id)
            self._save(kept)
