import array
import json
import os
import shutil
from pathlib import Path

import pytest

from app.audio import ingest
from app.core import proc
from app.core.errors import AppError
from tests.conftest import FFMPEG, FFPROBE, JobCtx, make_media, requires_ffmpeg, sine

pytestmark = requires_ffmpeg


@pytest.fixture
def media(tmp_path: Path) -> Path:
    d = tmp_path / "Nhạc của tôi"  # Vietnamese + space on purpose
    d.mkdir()
    return d


@pytest.fixture
def project(tmp_path: Path) -> Path:
    d = tmp_path / "Dự án"
    (d / "cache").mkdir(parents=True)
    return d


def wav_info(wav: Path) -> dict:  # type: ignore[type-arg]
    assert FFPROBE
    r = proc.run([FFPROBE, "-v", "error", "-print_format", "json", "-show_streams", wav])
    return json.loads(r.stdout)["streams"][0]  # type: ignore[no-any-return]


def run_ingest(project: Path, src: Path) -> ingest.IngestResult:
    assert FFMPEG and FFPROBE
    return ingest.ingest_file(FFMPEG, FFPROBE, project, src, JobCtx())  # type: ignore[arg-type]


# --------------------------------------------------------------------------- probe


NOISE = "anoisesrc=color=pink:amplitude=0.3:duration=3"  # encoders spend their full bitrate on it


@pytest.mark.parametrize(
    ("name", "args", "label", "kbps", "lossless"),
    [
        ("Bài 1.flac", ("-ac", "1", "-ar", "44100"), "flac", None, True),
        ("low.mp3", ("-c:a", "libmp3lame", "-b:a", "128k"), "mp3", 128, False),
        ("cd.wav", ("-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le"), "wav", 1411, True),
        ("song.m4a", ("-c:a", "aac", "-b:a", "192k"), "m4a/aac", 192, False),
        ("clip.webm", ("-c:a", "libopus", "-b:a", "96k"), "webm/opus", 96, False),
    ],
)
def test_probe_reports_format_and_bitrate(
    media: Path, name: str, args: tuple[str, ...], label: str, kbps: int | None, lossless: bool
) -> None:
    assert FFPROBE
    src = make_media(media / name, NOISE, args=args)
    p = ingest.probe(FFPROBE, src)
    assert p.format_label == label
    assert p.lossless is lossless
    assert p.duration == pytest.approx(3.0, abs=0.05)
    if kbps is not None:
        assert p.bitrate_kbps == pytest.approx(kbps, rel=0.15)


def test_compressible_flac_is_lossless_despite_low_bitrate(media: Path) -> None:
    assert FFPROBE
    p = ingest.probe(FFPROBE, sine(media / "pure tone.flac", 3))
    assert p.bitrate_kbps is not None and p.bitrate_kbps < 160
    assert p.lossless  # → no "low bitrate" warning in the UI


def test_probe_video_container(media: Path) -> None:
    assert FFPROBE
    src = make_media(
        media / "live show.mp4",
        "testsrc2=s=160x90:d=2:r=10",
        "sine=frequency=330:duration=2",
        args=("-c:v", "libx264", "-c:a", "aac", "-b:a", "128k", "-shortest"),
    )
    p = ingest.probe(FFPROBE, src)
    assert p.format_label == "mp4/aac"
    assert p.bitrate_kbps == pytest.approx(128, rel=0.2)  # the audio stream, not the video


def test_probe_errors_are_vietnamese(media: Path) -> None:
    assert FFPROBE
    with pytest.raises(AppError) as e:
        ingest.probe(FFPROBE, media / "không có.mp3")
    assert e.value.code == "file_not_found" and "không có.mp3" in e.value.message_vi

    junk = media / "hỏng.mp3"
    junk.write_bytes(os.urandom(4096))
    with pytest.raises(AppError) as e:
        ingest.probe(FFPROBE, junk)
    assert e.value.code == "unsupported_file"

    silent_video = make_media(
        media / "no audio.mp4", "testsrc2=s=64x64:d=1:r=10", args=("-c:v", "libx264")
    )
    with pytest.raises(AppError) as e:
        ingest.probe(FFPROBE, silent_video)
    assert e.value.code == "no_audio" and e.value.message_vi == "File không có âm thanh."


# --------------------------------------------------------------------------- decode + cache


def test_decodes_to_float32_48k_stereo_wav(media: Path, project: Path) -> None:
    src = sine(media / "mono 44k.flac", 3, 440, "-ac", "1", "-ar", "44100")
    r = run_ingest(project, src)
    wav = project / r.cache_wav
    assert r.cache_wav.startswith("cache/audio/") and wav.is_file()
    info = wav_info(wav)
    assert (info["codec_name"], info["sample_rate"], info["channels"]) == ("pcm_f32le", "48000", 2)
    assert r.duration == pytest.approx(3.0, abs=0.001)
    assert r.src_format == "flac"
    assert list(wav.parent.glob("*.part.wav")) == []


def test_keeps_samples_above_full_scale(media: Path, project: Path) -> None:
    """float32 cache: a hot master above 0 dBFS must not be clipped here. The source is mono,
    which also checks it reaches both channels at full level, not FFmpeg's -3 dB pan."""
    assert FFMPEG
    src = make_media(
        media / "hot.wav",
        "aevalsrc=2*sin(2*PI*100*t):s=48000:d=1",  # peaks at +6 dBFS
        args=("-c:a", "pcm_f32le"),
    )
    wav = project / run_ingest(project, src).cache_wav
    raw = proc.run([FFMPEG, "-v", "error", "-i", wav, "-f", "f32le", "-"]).stdout
    peak = max(abs(x) for x in array.array("f", raw))
    assert peak == pytest.approx(2.0, rel=0.01)


def test_cache_hit_skips_decoding_even_after_rename(
    media: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = sine(media / "a.mp3", 2, 440, "-c:a", "libmp3lame")
    first = run_ingest(project, src)
    moved = media / "sub" / "renamed copy.mp3"
    moved.parent.mkdir()
    shutil.copy(src, moved)

    def no_decode(*_: object, **__: object) -> None:
        raise AssertionError("cache should have been used")

    monkeypatch.setattr(ingest, "decode", no_decode)
    assert run_ingest(project, moved) == first


def test_different_content_gets_its_own_cache(media: Path, project: Path) -> None:
    a = run_ingest(project, sine(media / "a.wav", 1, 440))
    b = run_ingest(project, sine(media / "b.wav", 1, 660))
    assert a.cache_wav != b.cache_wav


def test_cancelled_decode_leaves_no_partial_file(media: Path, project: Path) -> None:
    assert FFMPEG and FFPROBE
    src = sine(media / "long.flac", 120)
    ctx = JobCtx()
    ctx.cancel_event.set()
    with pytest.raises(proc.Cancelled):
        ingest.ingest_file(FFMPEG, FFPROBE, project, src, ctx)  # type: ignore[arg-type]
    audio_dir = project / ingest.AUDIO_DIR
    assert list(audio_dir.glob("*")) == []


def test_refuses_when_disk_is_full(
    media: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = sine(media / "a.flac", 2)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: shutil._ntuple_diskusage(1, 1, 1000))  # type: ignore[attr-defined]
    with pytest.raises(AppError) as e:
        run_ingest(project, src)
    assert e.value.code == "disk_full" and "chỉ còn 1000 B" in e.value.message_vi


def test_progress_is_reported(media: Path, project: Path) -> None:
    assert FFMPEG and FFPROBE
    ctx = JobCtx()
    ingest.ingest_file(FFMPEG, FFPROBE, project, sine(media / "a.flac", 20), ctx)  # type: ignore[arg-type]
    fractions = [f for f, _ in ctx.events]
    assert fractions == sorted(fractions)
    assert fractions and fractions[-1] <= 1.0


# --------------------------------------------------------------------------- paths


def test_expand_paths_walks_folders_and_filters(tmp_path: Path) -> None:
    root = tmp_path / "Thư mục nhạc"
    for rel in ["b.mp3", "A.flac", "sub/c.mkv", "sub/notes.txt", "sub/cover.jpg"]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"x")
    explicit = root / "sub" / "notes.txt"
    files, missing = ingest.expand_paths(
        [
            f'"{root}"',  # Explorer's "Copy as path" adds quotes
            str(explicit),  # named explicitly → kept even though .txt
            str(root / "b.mp3"),  # duplicate of one inside the folder
            str(tmp_path / "không tồn tại"),
            "relative/path.mp3",
            "  ",
        ]
    )
    assert [f.relative_to(root).as_posix() for f in files] == [
        "A.flac",
        "b.mp3",
        "sub/c.mkv",
        "sub/notes.txt",
    ]
    assert missing == [str(tmp_path / "không tồn tại"), "relative/path.mp3"]
