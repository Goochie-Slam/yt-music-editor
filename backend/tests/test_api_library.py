from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import requires_ffmpeg, requires_ytdlp, sine, wait_job


def new_project(client: TestClient, parent: Path) -> tuple[str, Path]:
    r = client.post("/api/projects", json={"name": "Thư viện thử", "parentDir": str(parent)})
    assert r.status_code == 200, r.text
    return r.json()["project"]["id"], Path(r.json()["path"])


def test_expand_paths(client: TestClient, tmp_path: Path) -> None:
    d = tmp_path / "Nhạc"
    (d / "con").mkdir(parents=True)
    for n in ("a.mp3", "con/b.flac", "con/x.txt"):
        (d / n).write_bytes(b"x")
    r = client.post("/api/library/expand", json={"paths": [str(d), str(tmp_path / "nope")]})
    body = r.json()
    assert [f["name"] for f in body["files"]] == ["a", "b"]
    assert body["missing"] == [str(tmp_path / "nope")]


def test_tracklist_parse_endpoint(client: TestClient) -> None:
    r = client.post(
        "/api/tracklist/parse",
        json={"text": "00:00 Mở đầu\n03:75 sai giây\n02:10 – Bài hai\nrác", "duration": 400},  # noqa: RUF001
    )
    body = r.json()
    assert [(s["title"], s["start"], s["end"]) for s in body["segments"]] == [
        ("Mở đầu", 0, 130),
        ("Bài hai", 130, 400),
    ]
    assert [(e["lineNo"], e["error"]) for e in body["errors"]] == [
        (2, "bad_seconds"),
        (4, "bad_format"),
    ]


@requires_ffmpeg
def test_ingest_file_then_export(client: TestClient, projects_dir: Path, tmp_path: Path) -> None:
    pid, folder = new_project(client, projects_dir)
    src = sine(tmp_path / "nguồn" / "Bài hát.m4a", 3, 440, "-c:a", "aac", "-b:a", "128k")
    r = client.post(
        f"/api/projects/{pid}/library/ingest",
        json={"itemId": "item1", "title": "Bài hát", "source": {"kind": "file", "path": str(src)}},
    )
    job = wait_job(client, r.json()["jobId"])
    assert job["state"] == "done", job
    assert job["meta"] == {"projectId": pid, "itemId": "item1"}
    res = job["result"]
    assert res["itemId"] == "item1" and res["srcFormat"] == "m4a/aac"
    assert res["srcLossless"] is False
    assert (folder / res["cacheWav"]).is_file()

    out = tmp_path / "Xuất ra"
    r = client.post(
        f"/api/projects/{pid}/library/export",
        json={
            "folder": str(out),
            "pattern": "{index} - {title}",
            "entries": [
                {"title": "Bài hát", "wav": res["cacheWav"], "duration": res["duration"]},
                {"title": "Đoạn", "wav": res["cacheWav"], "start": 1, "end": 2, "duration": 1},
            ],
        },
    )
    job = wait_job(client, r.json()["jobId"])
    assert job["state"] == "done", job
    assert job["result"]["files"] == ["01 - Bài hát.mp3", "02 - Đoạn.mp3"]
    assert (out / "02 - Đoạn.mp3").is_file()


@requires_ffmpeg
def test_export_defaults_to_project_folder(
    client: TestClient, projects_dir: Path, tmp_path: Path
) -> None:
    pid, folder = new_project(client, projects_dir)
    src = sine(tmp_path / "a.wav", 1)
    job = wait_job(
        client,
        client.post(
            f"/api/projects/{pid}/library/ingest",
            json={"itemId": "a", "title": "A", "source": {"kind": "file", "path": str(src)}},
        ).json()["jobId"],
    )
    r = client.post(
        f"/api/projects/{pid}/library/export",
        json={"folder": "", "entries": [{"title": "A", "wav": job["result"]["cacheWav"]}]},
    )
    done = wait_job(client, r.json()["jobId"])
    assert done["result"]["folder"] == str(folder / "export")
    assert (folder / "export" / "01 - A.mp3").is_file()


@requires_ffmpeg
def test_upload_streams_then_deletes_the_copy(
    client: TestClient, projects_dir: Path, tmp_path: Path
) -> None:
    pid, folder = new_project(client, projects_dir)
    data = sine(tmp_path / "kéo thả.flac", 2).read_bytes()
    r = client.put(
        f"/api/projects/{pid}/library/up1/upload", params={"name": "kéo thả.flac"}, content=data
    )
    assert r.status_code == 200, r.text
    job = wait_job(client, r.json()["jobId"])
    assert job["state"] == "done", job
    assert job["result"]["srcFormat"] == "flac" and job["result"]["srcLossless"] is True
    assert list((folder / "cache" / "uploads").iterdir()) == []


def test_errors_are_vietnamese(client: TestClient, projects_dir: Path) -> None:
    pid, _ = new_project(client, projects_dir)
    bad_id = client.post(
        f"/api/projects/{pid}/library/ingest",
        json={"itemId": "../x", "title": "x", "source": {"kind": "file", "path": "/a.mp3"}},
    )
    assert bad_id.status_code == 400 and bad_id.json()["message_vi"]

    no_project = client.post(
        "/api/projects/nope/library/ingest",
        json={"itemId": "a", "title": "x", "source": {"kind": "file", "path": "/a.mp3"}},
    )
    assert no_project.status_code == 404
    assert no_project.json()["message_vi"] == "Không tìm thấy project."

    escape = client.post(
        f"/api/projects/{pid}/library/export",
        json={"entries": [{"title": "x", "wav": "../../../etc/passwd"}]},
    )
    assert escape.status_code == 400 and escape.json()["code"] == "outside_project"

    relative = client.post(
        f"/api/projects/{pid}/library/export",
        json={"folder": "relative/out", "entries": [{"title": "x", "wav": "cache/a.wav"}]},
    )
    assert relative.status_code == 400 and relative.json()["code"] == "export_folder_invalid"

    pattern = client.post(
        f"/api/projects/{pid}/library/export",
        json={"pattern": "mix", "entries": [{"title": "x", "wav": "cache/a.wav"}]},
    )
    assert pattern.status_code == 400 and pattern.json()["code"] == "pattern_invalid"


@requires_ffmpeg
def test_missing_source_file_fails_the_job_in_vietnamese(
    client: TestClient, projects_dir: Path, tmp_path: Path
) -> None:
    pid, _ = new_project(client, projects_dir)
    r = client.post(
        f"/api/projects/{pid}/library/ingest",
        json={
            "itemId": "gone",
            "title": "Mất",
            "source": {"kind": "file", "path": str(tmp_path / "đã xóa.mp3")},
        },
    )
    job = wait_job(client, r.json()["jobId"])
    assert job["state"] == "failed"
    assert job["error"]["code"] == "file_not_found" and "đã xóa.mp3" in job["error"]["message_vi"]


def test_links_need_ytdlp(settings: Settings) -> None:
    settings.ytdlp = None
    with TestClient(create_app(settings)) as c:
        r = c.post("/api/library/resolve", json={"url": "https://youtu.be/x"})
    assert r.status_code == 500 and r.json()["code"] == "ytdlp_missing"
    assert "Start.bat" in r.json()["message_vi"]


def test_resolve_rejects_non_http(client: TestClient) -> None:
    r = client.post("/api/library/resolve", json={"url": "file:///etc/passwd"})
    assert r.status_code == 422


@requires_ffmpeg
@requires_ytdlp
def test_resolve_and_download_via_api(
    client: TestClient, projects_dir: Path, http_dir: tuple[Path, str]
) -> None:
    root, base = http_dir
    sine(root / "song.mp3", 2, 440, "-c:a", "libmp3lame")
    job = wait_job(
        client,
        client.post("/api/library/resolve", json={"url": f"{base}/song.mp3"}).json()["jobId"],
    )
    assert job["state"] == "done", job
    entry = job["result"]["entries"][0]
    assert job["result"]["kind"] == "single" and entry["url"] == f"{base}/song.mp3"

    pid, folder = new_project(client, projects_dir)
    r = client.post(
        f"/api/projects/{pid}/library/ingest",
        json={
            "itemId": "dl1",
            "title": entry["title"],
            "source": {"kind": "url", "url": entry["url"], "site": entry["site"]},
        },
    )
    job = wait_job(client, r.json()["jobId"])
    assert job["state"] == "done", job
    assert job["kind"] == "download" and (folder / job["result"]["cacheWav"]).is_file()


def test_system_info_lists_extensions(client: TestClient) -> None:
    info = client.get("/api/system").json()
    assert {"flac", "mkv", "mp3", "m4a", "opus"} <= set(info["supportedExtensions"])
    assert info["lowBitrateKbps"] == 160
    assert set(info["jsRuntime"]) == {"deno", "node"}


def test_open_folder(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import proc

    opened: list[Path] = []
    monkeypatch.setattr(proc, "open_folder", opened.append)
    assert client.post("/api/system/open-folder", json={"path": str(tmp_path)}).status_code == 204
    assert opened == [tmp_path]
    r = client.post("/api/system/open-folder", json={"path": str(tmp_path / "nope")})
    assert r.status_code == 404
