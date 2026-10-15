from fastapi.testclient import TestClient

from app.core.tools import parse_progress_line
from tests.conftest import requires_ffmpeg


def test_parse_progress_line() -> None:
    assert parse_progress_line("out_time_us=2500000") == 2.5
    assert parse_progress_line("out_time_us=N/A") is None
    assert parse_progress_line("progress=continue") is None


@requires_ffmpeg
def test_system_info_detects_ffmpeg(client: TestClient) -> None:
    info = client.get("/api/system").json()
    assert info["ffmpeg"]["path"] and info["ffmpeg"]["version"].startswith("ffmpeg version")
    assert info["ffmpeg"]["x264"] is True
    assert isinstance(info["ffmpeg"]["nvenc"], bool)


@requires_ffmpeg
def test_selftest_job_streams_progress_over_websocket(client: TestClient) -> None:
    with client.websocket_connect("/api/ws") as ws:
        job_id = client.post("/api/system/selftest").json()["jobId"]
        progress, state = [], None
        while state not in ("done", "failed", "cancelled"):
            ev = ws.receive_json()
            if ev.get("id") != job_id:
                continue
            state = ev["state"]
            progress.append(ev["progress"])
    assert state == "done", client.get(f"/api/jobs/{job_id}").json()
    assert progress == sorted(progress) and progress[-1] == 1.0
    assert any(0 < p < 1 for p in progress), "expected intermediate progress from -progress pipe"


@requires_ffmpeg
def test_selftest_can_be_cancelled(client: TestClient) -> None:
    import time

    job_id = client.post("/api/system/selftest").json()["jobId"]
    time.sleep(0.5)
    client.post(f"/api/jobs/{job_id}/cancel")
    for _ in range(100):
        if client.get(f"/api/jobs/{job_id}").json()["state"] == "cancelled":
            break
        time.sleep(0.05)
    assert client.get(f"/api/jobs/{job_id}").json()["state"] == "cancelled"


def test_missing_job_is_404(client: TestClient) -> None:
    r = client.get("/api/jobs/nope")
    assert r.status_code == 404 and r.json()["message_vi"] == "Không tìm thấy tác vụ."
