import json
from pathlib import Path

import pytest

from app.audio import export, ingest
from app.core import proc
from app.core.errors import AppError
from tests.conftest import FFMPEG, FFPROBE, JobCtx, requires_ffmpeg, sine


def test_names_follow_pattern_with_padding() -> None:
    titles = [f"Bài {i}" for i in range(1, 13)]
    names = export.render_names("{index} - {title}", titles)
    assert names[0] == "01 - Bài 1" and names[11] == "12 - Bài 12"
    assert export.render_names("{index}", ["a"] * 120)[0] == "001"
    assert export.render_names("{title}", ["Mưa"]) == ["Mưa"]


def test_names_are_safe_on_windows() -> None:
    assert export.render_names("{title}", ['AC/DC: "Live"? <x>|*'])[0] == "AC_DC_ _Live__ _x___"
    assert export.render_names("{title}", ["CON"])[0] == "_CON"
    assert export.render_names("{title}", ["dots...  "])[0] == "dots"
    assert export.render_names("{title}", ["   "])[0] == "untitled"
    assert len(export.render_names("{title}", ["x" * 400])[0]) == export.MAX_NAME
    # placeholders in titles are not expanded again; braces elsewhere are kept as text
    assert export.render_names("{index} {title}", ["{index}"])[0] == "01 {index}"


def test_pattern_needs_a_placeholder() -> None:
    with pytest.raises(AppError) as e:
        export.render_names("mix", ["a", "b"])
    assert e.value.code == "pattern_invalid" and "{title}" in e.value.message_vi


def test_never_overwrites(tmp_path: Path) -> None:
    (tmp_path / "01 - A.mp3").write_bytes(b"old")
    taken: set[str] = set()
    assert export.unique_path(tmp_path, "01 - A", ".mp3", taken).name == "01 - A (2).mp3"
    # Windows file names ignore case, so names within one batch must too
    assert export.unique_path(tmp_path, "Mưa", ".mp3", taken).name == "Mưa.mp3"
    assert export.unique_path(tmp_path, "MƯA", ".mp3", taken).name == "MƯA (2).mp3"


def mp3_info(path: Path) -> dict:  # type: ignore[type-arg]
    assert FFPROBE
    r = proc.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    )
    return json.loads(r.stdout)  # type: ignore[no-any-return]


@requires_ffmpeg
def test_exports_320_cbr_without_tags_and_exact_segments(tmp_path: Path) -> None:
    assert FFMPEG and FFPROBE
    project = tmp_path / "Dự án"
    media = tmp_path / "nguồn"
    full = ingest.ingest_file(
        FFMPEG,
        FFPROBE,
        project,
        sine(media / "có tag.flac", 4, 440, "-metadata", "title=Không được giữ"),
        JobCtx(),  # type: ignore[arg-type]
    )
    wav = project / full.cache_wav
    entries = [
        export.Entry("Bài đầu: “Mưa”", wav, duration=full.duration),
        export.Entry("Đoạn cắt", wav, start=1.0, end=2.5, duration=1.5),
        export.Entry("Hỏng", project / "cache" / "audio" / "missing.wav", duration=1),
    ]
    out = tmp_path / "Xuất MP3"
    ctx = JobCtx()
    r = export.export_mp3(FFMPEG, entries, out, "{index} - {title}", ctx)  # type: ignore[arg-type]

    assert r["files"] == ["01 - Bài đầu_ “Mưa”.mp3", "02 - Đoạn cắt.mp3"]
    assert [f["title"] for f in r["failed"]] == ["Hỏng"]
    assert r["failed"][0]["message"] == "FFmpeg báo lỗi khi xử lý."
    assert sorted(p.name for p in out.iterdir()) == sorted(r["files"])  # no .part leftovers

    for name, expected in zip(r["files"], [4.0, 1.5], strict=True):
        path = out / name
        info = mp3_info(path)
        stream = info["streams"][0]
        assert stream["codec_name"] == "mp3"
        assert int(stream["bit_rate"]) == 320_000
        assert not info["format"].get("tags"), "no tags (F1.4)"
        assert path.read_bytes()[:3] != b"ID3"
        assert float(info["format"]["duration"]) == pytest.approx(expected, abs=0.05)
    fractions = [f for f, _ in ctx.events]
    assert fractions == sorted(fractions) and fractions[-1] <= 1.0


@requires_ffmpeg
def test_export_checks_disk_space(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    assert FFMPEG
    monkeypatch.setattr(shutil, "disk_usage", lambda _: shutil._ntuple_diskusage(1, 1, 10))  # type: ignore[attr-defined]
    with pytest.raises(AppError) as e:
        export.export_mp3(
            FFMPEG,
            [export.Entry("a", tmp_path / "a.wav", duration=3600)],
            tmp_path / "out",
            "{title}",
            JobCtx(),  # type: ignore[arg-type]
        )
    assert e.value.code == "disk_full"
