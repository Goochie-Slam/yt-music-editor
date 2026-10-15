import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def test_rejects_foreign_host(client: TestClient) -> None:
    r = client.get("/api/presets/transitions", headers={"host": "evil.example:8765"})
    assert r.status_code == 403 and r.json()["code"] == "forbidden_host"


def test_rejects_foreign_origin(client: TestClient) -> None:
    r = client.post("/api/system/selftest", headers={"origin": "http://evil.example"})
    assert r.status_code == 403


def test_accepts_local_origins(client: TestClient) -> None:
    for origin in ("http://testserver", "http://127.0.0.1:5173"):
        assert client.get("/api/jobs", headers={"origin": origin}).status_code == 200


def test_websocket_from_foreign_origin_is_closed(client: TestClient) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/api/ws", headers={"origin": "http://evil.example"}) as ws,
    ):
        ws.receive_json()


def test_server_binds_loopback_by_default() -> None:
    from app.core.config import Settings

    assert Settings().host == "127.0.0.1"
