from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from app.core.projects import ProjectStore
from app.models.project import Model, Project, ProjectSummary

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateBody(Model):
    name: str = Field(min_length=1, max_length=120)
    parent_dir: str


class OpenBody(Model):
    path: str


class Opened(Model):
    project: Project
    path: str


def _store(request: Request) -> ProjectStore:
    store: ProjectStore = request.app.state.projects
    return store


@router.get("")
def recent(request: Request) -> list[ProjectSummary]:
    return _store(request).recent()


@router.post("")
def create(body: CreateBody, request: Request) -> Opened:
    parent = Path(body.parent_dir)
    if parent == request.app.state.settings.default_projects_dir:
        parent.mkdir(parents=True, exist_ok=True)  # only our own default folder is auto-created
    project, folder = _store(request).create(body.name.strip(), parent)
    return Opened(project=project, path=str(folder))


@router.post("/open")
def open_project(body: OpenBody, request: Request) -> Opened:
    project, folder = _store(request).open(Path(body.path))
    return Opened(project=project, path=str(folder))


@router.get("/{project_id}")
def get(project_id: str, request: Request) -> Project:
    return _store(request).get(project_id)


@router.put("/{project_id}")
def save(project_id: str, project: Project, request: Request) -> Project:
    """Autosave target (F5.2): validated, then written atomically with rotating backups."""
    return _store(request).save(project_id, project)
