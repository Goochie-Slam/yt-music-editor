"""Background jobs: anything slower than ~1 s runs here and reports progress over the event bus."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.core.errors import AppError
from app.core.events import EventBus
from app.core.proc import Cancelled
from app.core.util import new_id

log = logging.getLogger(__name__)


class Lane(StrEnum):
    """Heavy work (download, decode, encode) is capped at F1.7's N; lookups never wait on it."""

    HEAVY = "heavy"
    LIGHT = "light"


HEAVY_WORKERS = 3  # F1.7 default
LIGHT_WORKERS = 4


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


FINISHED = {JobState.DONE, JobState.FAILED, JobState.CANCELLED}


@dataclass
class Job:
    id: str
    kind: str
    title: str
    state: JobState = JobState.QUEUED
    progress: float = 0.0
    message: str = ""
    error: dict[str, str] | None = None
    result: Any = None
    meta: dict[str, str] = field(default_factory=dict)  # e.g. projectId / itemId for the UI
    created_at: float = field(default_factory=time.time)
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def to_event(self) -> dict[str, Any]:
        return {
            "type": "job",
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "state": self.state.value,
            "progress": round(self.progress, 4),
            "message": self.message,
            "error": self.error,
            "result": self.result,
            "meta": self.meta,
            "createdAt": self.created_at,
        }


class JobContext:
    """Handed to the job function: report progress, observe cancellation."""

    def __init__(self, job: Job, manager: JobManager):
        self._job, self._mgr = job, manager

    @property
    def cancel_event(self) -> threading.Event:
        return self._job.cancel_event

    def progress(self, fraction: float, message: str | None = None) -> None:
        self._job.progress = min(1.0, max(0.0, fraction))
        if message is not None:
            self._job.message = message
        self._mgr.emit(self._job)

    def check_cancelled(self) -> None:
        if self._job.cancel_event.is_set():
            raise Cancelled(self._job.id)


JobFn = Callable[[JobContext], Any]


class JobManager:
    def __init__(self, bus: EventBus, workers: int = HEAVY_WORKERS):
        self._bus = bus
        self._pools = {
            Lane.HEAVY: ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job"),
            Lane.LIGHT: ThreadPoolExecutor(max_workers=LIGHT_WORKERS, thread_name_prefix="job-l"),
        }
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def emit(self, job: Job) -> None:
        self._bus.publish(job.to_event())

    def submit(
        self,
        kind: str,
        title: str,
        fn: JobFn,
        *,
        lane: Lane = Lane.HEAVY,
        meta: dict[str, str] | None = None,
    ) -> Job:
        job = Job(new_id(), kind, title, meta=meta or {})
        with self._lock:
            self._jobs[job.id] = job
        self.emit(job)
        self._pools[lane].submit(self._run, job, fn)
        return job

    def _run(self, job: Job, fn: JobFn) -> None:
        if job.cancel_event.is_set():
            job.state = JobState.CANCELLED
            self.emit(job)
            return
        job.state = JobState.RUNNING
        self.emit(job)
        try:
            job.result = fn(JobContext(job, self))
            job.state, job.progress = JobState.DONE, 1.0
        except Cancelled:
            job.state = JobState.CANCELLED
        except AppError as e:
            job.state, job.error = JobState.FAILED, e.payload()
        except Exception as e:
            log.exception("job %s (%s) crashed", job.id, job.kind)
            job.state = JobState.FAILED
            job.error = AppError.internal(str(e)).payload()
        self.emit(job)

    def cancel(self, job_id: str) -> Job:
        job = self.get(job_id)
        job.cancel_event.set()
        return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise AppError.not_found("job", job_id)
        return job

    def list(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at)

    def shutdown(self) -> None:
        for job in self.list():
            if job.state not in FINISHED:
                job.cancel_event.set()
        for pool in self._pools.values():
            pool.shutdown(wait=True, cancel_futures=True)
