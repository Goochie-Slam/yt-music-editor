import asyncio
import threading
import time

from app.core.errors import AppError
from app.core.events import EventBus
from app.core.jobs import JobContext, JobManager, JobState


def wait_for(cond, timeout: float = 5.0) -> None:  # type: ignore[no-untyped-def]
    end = time.monotonic() + timeout
    while not cond():
        assert time.monotonic() < end, "timed out"
        time.sleep(0.01)


def test_job_runs_and_reports_progress_over_the_bus() -> None:
    async def scenario() -> list[dict]:  # type: ignore[type-arg]
        bus = EventBus()
        bus.bind_loop(asyncio.get_running_loop())
        q = bus.subscribe()
        mgr = JobManager(bus)

        def work(ctx: JobContext) -> str:
            for i in range(1, 5):
                ctx.progress(i / 4, f"{i}/4")
            return "ok"

        job = mgr.submit("demo", "Demo", work)
        events = []
        while True:
            ev = await asyncio.wait_for(q.get(), 5)
            events.append(ev)
            if ev["state"] == "done":
                break
        assert mgr.get(job.id).result == "ok"
        mgr.shutdown()
        return events

    events = asyncio.run(scenario())
    states = [e["state"] for e in events]
    assert states[0] == "queued" and states[-1] == "done"
    assert events[-1]["progress"] == 1.0 and events[-1]["result"] == "ok"
    assert any(e["message"] == "2/4" for e in events)


def test_cancel_running_job() -> None:
    mgr = JobManager(EventBus())
    started = threading.Event()

    def work(ctx: JobContext) -> None:
        started.set()
        while True:
            ctx.check_cancelled()
            time.sleep(0.01)

    job = mgr.submit("demo", "Demo", work)
    started.wait(2)
    mgr.cancel(job.id)
    wait_for(lambda: job.state == JobState.CANCELLED)
    mgr.shutdown()


def test_failures_are_captured_with_vietnamese_message() -> None:
    mgr = JobManager(EventBus())

    def app_fail(_: JobContext) -> None:
        raise AppError(500, "ffmpeg_failed", "stderr…")

    def crash(_: JobContext) -> None:
        raise RuntimeError("bug")

    a, b = mgr.submit("x", "x", app_fail), mgr.submit("y", "y", crash)
    wait_for(lambda: a.state == JobState.FAILED and b.state == JobState.FAILED)
    assert a.error and a.error["code"] == "ffmpeg_failed" and "FFmpeg" in a.error["message_vi"]
    assert b.error and b.error["code"] == "internal" and b.error["detail"] == "bug"
    mgr.shutdown()
