from fastapi.testclient import TestClient

P = {"fadeOut": 4, "fadeIn": 2, "overlap": 2, "curveOut": "equal-power", "curveIn": "equal-power"}


def test_five_builtin_presets(client: TestClient) -> None:
    items = client.get("/api/presets/transitions").json()
    assert [p["id"] for p in items] == [
        "smooth-blend",
        "quick-mix",
        "long-dissolve",
        "radio-segue",
        "fade-breathe",
    ]
    assert all(p["builtin"] for p in items)
    breathe = items[-1]
    assert breathe["overlap"] == -1.5


def test_user_preset_crud(client: TestClient) -> None:
    created = client.post("/api/presets/transitions", json={"name": "My Chill", **P}).json()
    assert created["id"].startswith("user-") and not created["builtin"]
    upd = client.put(
        f"/api/presets/transitions/{created['id']}", json={"name": "My Chill 2", **P, "fadeOut": 8}
    ).json()
    assert upd["fadeOut"] == 8
    assert len(client.get("/api/presets/transitions").json()) == 6
    assert client.delete(f"/api/presets/transitions/{created['id']}").status_code == 204
    assert len(client.get("/api/presets/transitions").json()) == 5


def test_preset_rules(client: TestClient) -> None:
    r = client.post("/api/presets/transitions", json={"name": "quick MIX", **P})
    assert r.status_code == 409 and r.json()["code"] == "preset_name_taken"
    assert client.delete("/api/presets/transitions/smooth-blend").status_code == 403
    r = client.put("/api/presets/transitions/smooth-blend", json={"name": "x", **P})
    assert r.status_code == 403
    assert client.delete("/api/presets/transitions/user-nope").status_code == 404
