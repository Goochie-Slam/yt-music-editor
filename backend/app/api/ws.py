from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/api/ws")
async def events(ws: WebSocket) -> None:
    """Job progress and other server-pushed events. Sends a snapshot of all jobs on connect."""
    await ws.accept()
    bus, jobs = ws.app.state.bus, ws.app.state.jobs
    q = bus.subscribe()
    try:
        for job in jobs.list():
            await ws.send_json(job.to_event())
        while True:
            await ws.send_json(await q.get())
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(q)
