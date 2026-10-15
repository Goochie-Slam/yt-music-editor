"""Project folders on disk and the "recent projects" registry (F5.1, F5.4).

A project is a folder chosen by the user:
    <folder>/project.json   (+ .bak1 … .bak5)
    <folder>/cache/         lossless WAV, peaks, spectrum — safe to delete
    <folder>/media/         artwork, overlays copied in by the user
    <folder>/renders/       render jobs and their chunk state
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from pydantic import ValidationError

from app.core.errors import AppError
from app.core.fsutil import atomic_write_text, safe_folder_name, unique_dir
from app.core.util import utcnow
from app.models.migrations import migrate
from app.models.project import Project, ProjectSummary, TextElement

PROJECT_FILE = "project.json"
SUBDIRS = ("cache", "media", "renders")
MAX_RECENT = 20


class ProjectStore:
    def __init__(self, data_dir: Path):
        self._registry = data_dir / "recent.json"
        self._lock = threading.Lock()

    # ----------------------------------------------------------------- registry

    def _read_registry(self) -> list[ProjectSummary]:
        if not self._registry.exists():
            return []
        try:
            items = json.loads(self._registry.read_text(encoding="utf-8"))
            return [ProjectSummary.model_validate(i) for i in items]
        except (ValueError, ValidationError):
            return []  # a broken registry only loses the "recent" list, never projects

    def _remember(self, project: Project, folder: Path) -> None:
        entry = ProjectSummary(
            id=project.id, name=project.name, path=str(folder), updated_at=project.updated_at
        )
        items = [i for i in self._read_registry() if i.id != project.id and i.path != str(folder)]
        items.insert(0, entry)
        data = [i.model_dump(mode="json") for i in items[:MAX_RECENT]]
        atomic_write_text(self._registry, json.dumps(data, ensure_ascii=False, indent=1), backups=0)

    def recent(self) -> list[ProjectSummary]:
        with self._lock:
            return [i for i in self._read_registry() if (Path(i.path) / PROJECT_FILE).exists()]

    def folder_of(self, project_id: str) -> Path:
        for item in self._read_registry():
            if item.id == project_id:
                return Path(item.path)
        raise AppError.not_found("project", project_id)

    # ----------------------------------------------------------------- files

    @staticmethod
    def _load(folder: Path) -> Project:
        file = folder / PROJECT_FILE
        if not file.is_file():
            raise AppError(404, "project_not_found", str(file), path=str(folder))
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise AppError(422, "project_corrupt", str(e)) from e
        try:
            return Project.model_validate(migrate(raw))
        except ValidationError as e:
            raise AppError(422, "project_corrupt", str(e)[:2000]) from e

    @staticmethod
    def _write(folder: Path, project: Project) -> None:
        text = project.model_dump_json(indent=2)
        atomic_write_text(folder / PROJECT_FILE, text)

    # ----------------------------------------------------------------- public

    def create(self, name: str, parent_dir: Path) -> tuple[Project, Path]:
        if not parent_dir.is_dir():
            raise AppError(400, "folder_not_found", str(parent_dir), path=str(parent_dir))
        folder = unique_dir(parent_dir, safe_folder_name(name))
        project = Project(name=name)
        for el in project.video.elements:
            if isinstance(el, TextElement) and not el.text:
                el.text = name  # the playlist title starts as the project name
        with self._lock:
            for sub in SUBDIRS:
                (folder / sub).mkdir(parents=True, exist_ok=True)
            self._write(folder, project)
            self._remember(project, folder)
        return project, folder

    def open(self, path: Path) -> tuple[Project, Path]:
        folder = path.parent if path.name == PROJECT_FILE else path
        project = self._load(folder)
        with self._lock:
            self._remember(project, folder)
        return project, folder

    def get(self, project_id: str) -> Project:
        return self._load(self.folder_of(project_id))

    def save(self, project_id: str, project: Project) -> Project:
        if project.id != project_id:
            raise AppError(409, "project_id_mismatch", f"{project.id} != {project_id}")
        folder = self.folder_of(project_id)
        project.updated_at = utcnow()
        with self._lock:
            self._write(folder, project)
            self._remember(project, folder)
        return project
