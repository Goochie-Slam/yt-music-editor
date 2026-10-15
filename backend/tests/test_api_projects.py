import json
from pathlib import Path

from fastapi.testclient import TestClient


def create(client: TestClient, parent: Path, name: str = "Chill Night Mix") -> dict:  # type: ignore[type-arg]
    r = client.post("/api/projects", json={"name": name, "parentDir": str(parent)})
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def test_create_project_writes_folder_with_defaults(client: TestClient, projects_dir: Path) -> None:
    body = create(client, projects_dir, "Nhạc Đêm: Mưa")
    folder = Path(body["path"])
    assert folder == projects_dir / "Nhạc Đêm Mưa"
    assert {p.name for p in folder.iterdir()} >= {"project.json", "cache", "media", "renders"}
    p = body["project"]
    assert p["schemaVersion"] == 1 and p["name"] == "Nhạc Đêm: Mưa"
    assert p["mix"]["targetLufs"] == -14
    title = next(e for e in p["video"]["elements"] if e["kind"] == "text")
    assert title["text"] == "Nhạc Đêm: Mưa"
    assert set(title["pos"]) == {"16:9", "9:16"}


def test_same_name_twice_gets_unique_folder(client: TestClient, projects_dir: Path) -> None:
    a, b = create(client, projects_dir), create(client, projects_dir)
    assert a["path"] != b["path"] and b["path"].endswith("(2)")


def test_recent_lists_newest_first_and_drops_deleted(
    client: TestClient, projects_dir: Path
) -> None:
    a = create(client, projects_dir, "A")
    b = create(client, projects_dir, "B")
    assert [i["name"] for i in client.get("/api/projects").json()] == ["B", "A"]
    (Path(b["path"]) / "project.json").unlink()
    assert [i["id"] for i in client.get("/api/projects").json()] == [a["project"]["id"]]


def test_save_roundtrip_and_backups(client: TestClient, projects_dir: Path) -> None:
    body = create(client, projects_dir)
    pid, folder = body["project"]["id"], Path(body["path"])
    proj = client.get(f"/api/projects/{pid}").json()
    proj["mix"]["tracks"].append({"libId": "L1", "title": "Bài 1", "trimIn": 2.4})
    proj["mix"]["transitions"]["t1>t2"] = {
        "fadeOut": 3,
        "fadeIn": 1,
        "overlap": -1.5,
        "curveOut": "log",
        "curveIn": "linear",
    }
    saved = client.put(f"/api/projects/{pid}", json=proj)
    assert saved.status_code == 200, saved.text
    # >= : Windows' system clock can return the same timestamp for back-to-back calls
    assert saved.json()["updatedAt"] >= proj["updatedAt"]
    again = client.get(f"/api/projects/{pid}").json()
    assert again["mix"]["tracks"][0]["title"] == "Bài 1"
    assert again["mix"]["transitions"]["t1>t2"]["overlap"] == -1.5
    assert (folder / "project.json.bak1").exists()


def test_save_rejects_invalid_data_with_vietnamese_message(
    client: TestClient, projects_dir: Path
) -> None:
    body = create(client, projects_dir)
    proj = body["project"]
    proj["mix"]["transitions"]["a>b"] = {
        "fadeOut": 99,
        "fadeIn": 1,
        "overlap": 0,
        "curveOut": "log",
        "curveIn": "log",
    }
    r = client.put(f"/api/projects/{proj['id']}", json=proj)
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_input" and r.json()["message_vi"]
    proj2 = body["project"] | {"unknownField": 1}
    assert client.put(f"/api/projects/{proj['id']}", json=proj2).status_code == 422


def test_save_with_wrong_id_is_rejected(client: TestClient, projects_dir: Path) -> None:
    a, b = create(client, projects_dir, "A"), create(client, projects_dir, "B")
    r = client.put(f"/api/projects/{a['project']['id']}", json=b["project"])
    assert r.status_code == 409 and r.json()["code"] == "project_id_mismatch"


def test_open_by_folder_or_file(client: TestClient, projects_dir: Path, settings) -> None:  # type: ignore[no-untyped-def]
    body = create(client, projects_dir)
    folder = Path(body["path"])
    (settings.data_dir / "recent.json").unlink()  # forget it, then reopen
    for path in (folder, folder / "project.json"):
        r = client.post("/api/projects/open", json={"path": str(path)})
        assert r.status_code == 200 and r.json()["project"]["id"] == body["project"]["id"]


def test_open_errors(client: TestClient, projects_dir: Path) -> None:
    r = client.post("/api/projects/open", json={"path": str(projects_dir / "nope")})
    assert r.status_code == 404 and r.json()["code"] == "project_not_found"
    broken = projects_dir / "broken"
    broken.mkdir()
    (broken / "project.json").write_text("{not json", encoding="utf-8")
    r = client.post("/api/projects/open", json={"path": str(broken)})
    assert r.status_code == 422 and r.json()["code"] == "project_corrupt"
    future = projects_dir / "future"
    future.mkdir()
    (future / "project.json").write_text(
        json.dumps({"schemaVersion": 99, "name": "x"}), encoding="utf-8"
    )
    r = client.post("/api/projects/open", json={"path": str(future)})
    assert r.json()["code"] == "project_too_new"


def test_create_in_missing_folder(client: TestClient, projects_dir: Path) -> None:
    r = client.post("/api/projects", json={"name": "x", "parentDir": str(projects_dir / "missing")})
    assert r.status_code == 400 and r.json()["code"] == "folder_not_found"


def test_default_projects_dir_is_created_on_demand(
    client: TestClient,
    settings,
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    target = settings.default_projects_dir
    assert client.get("/api/system").json()["defaultProjectsDir"] == str(target)
    r = client.post("/api/projects", json={"name": "Mix 1", "parentDir": str(target)})
    assert r.status_code == 200 and (target / "Mix 1" / "project.json").exists()
