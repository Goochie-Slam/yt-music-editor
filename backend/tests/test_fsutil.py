from pathlib import Path

from app.core.fsutil import atomic_write_text, safe_folder_name, unique_dir


def test_atomic_write_rotates_backups(tmp_path: Path) -> None:
    f = tmp_path / "project.json"
    for i in range(8):
        atomic_write_text(f, f"v{i}", backups=5)
    assert f.read_text(encoding="utf-8") == "v7"
    assert [
        f.with_name(f"project.json.bak{i}").read_text(encoding="utf-8") for i in range(1, 6)
    ] == ["v6", "v5", "v4", "v3", "v2"]
    assert not f.with_name("project.json.bak6").exists()
    assert not f.with_name("project.json.tmp").exists()


def test_atomic_write_without_backups(tmp_path: Path) -> None:
    f = tmp_path / "sub" / "a.json"
    atomic_write_text(f, "1", backups=0)
    atomic_write_text(f, "2", backups=0)
    assert f.read_text(encoding="utf-8") == "2"
    assert sorted(p.name for p in f.parent.iterdir()) == ["a.json"]


def test_safe_folder_name_keeps_vietnamese() -> None:
    assert safe_folder_name("Nhạc Chill: Đêm/Mưa?") == "Nhạc Chill ĐêmMưa"
    assert safe_folder_name("  bad.  ") == "bad"
    assert safe_folder_name("CON") == "project"
    assert safe_folder_name('<>:"|') == "project"


def test_unique_dir(tmp_path: Path) -> None:
    (tmp_path / "Mix").mkdir()
    (tmp_path / "Mix (2)").mkdir()
    assert unique_dir(tmp_path, "Mix") == tmp_path / "Mix (3)"
