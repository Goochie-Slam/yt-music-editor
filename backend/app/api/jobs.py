from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(request: Request) -> list[dict[str, Any]]:
    return [j.to_event() for j in request.app.state.jobs.list()]


@router.get("/{job_id}")
def get_job(job_id: str, request: Request) -> dict[str, Any]:
    event: dict[str, Any] = request.app.state.jobs.get(job_id).to_event()
    return event


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, request: Request) -> dict[str, Any]:
    event: dict[str, Any] = request.app.state.jobs.cancel(job_id).to_event()
    return event
