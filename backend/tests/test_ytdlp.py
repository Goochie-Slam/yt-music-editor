import json
from pathlib import Path

import pytest

from app.audio import ingest, ytdlp
from app.core import proc
from app.core.errors import AppError
from tests.conftest import FFMPEG, FFPROBE, YTDLP, JobCtx, requires_ffmpeg, requires_ytdlp, sine

# --------------------------------------------------------------------------- error mapping

YT = "ERROR: [youtube] dQw4w9WgXcQ: "


@pytest.mark.parametrize(
    ("stderr", "code"),
    [
        (YT + "Private video. Sign in if you've been granted access", "yt_private"),
        (YT + "Video unavailable. This video has been removed by the uploader", "yt_unavailable"),
        (YT + "Sign in to confirm your age. This video may be inappropriate", "yt_age"),
        (YT + "Sign in to confirm you’re not a bot. Use --cookies", "yt_bot"),  # noqa: RUF001
        (YT + "The uploader has not made this video available in your country", "yt_geo"),
        (YT + "Join this channel to get access to members-only content", "yt_members"),
        (YT + "This video is DRM protected", "yt_drm"),
        (YT + "This live event will begin in 3 hours.", "yt_live"),
        ("ERROR: [soundcloud] 123: HTTP Error 429: Too Many Requests", "yt_rate_limited"),
        (
            "ERROR: [generic] x: Unable to download webpage: HTTP Error 404: Not Found",
            "yt_not_found",
        ),
        ("ERROR: Unsupported URL: https://example.com/", "yt_unsupported"),
        (
            "ERROR: [mixcloud] a: Unable to download JSON metadata: <urlopen error "
            "[Errno 11001] getaddrinfo failed>",
            "yt_network",
        ),
        (
            "WARNING: [youtube] No supported JavaScript runtime could be found.\n"
            + YT
            + "Requested format is not available",
            "yt_js_runtime",
        ),
    ],
)
def test_errors_become_vietnamese(stderr: str, code: str) -> None:
    e = ytdlp.error_from_output(stderr)
    assert e.code == code
    assert e.message_vi and "{" not in e.message_vi
    assert e.detail == stderr


def test_unknown_error_keeps_ytdlp_reason() -> None:
    e = ytdlp.error_from_output("WARNING: meh\nERROR: [vimeo] 42: Something odd happened")
    assert e.code == "yt_failed"
    assert e.message_vi == "yt-dlp báo lỗi: Something odd happened"


def test_progress_template_parsing() -> None:
    assert ytdlp.parse_progress("[dl] 50 200 NA") == 0.25
    assert ytdlp.parse_progress("[dl] 50 NA 100") == 0.5  # only an estimate is known
    assert ytdlp.parse_progress("[dl] 50 NA NA") is None
    assert ytdlp.parse_progress("[download] 5%") is None


def test_parse_playlist_marks_unavailable_entries() -> None:
    out = json.dumps(
        {
            "_type": "playlist",
            "title": "Lofi tuyển tập",
            "extractor_key": "YoutubeTab",
            "entries": [
                {
                    "url": "https://www.youtube.com/watch?v=a",
                    "id": "a",
                    "title": "Bài A",
                    "duration": 201,
                    "ie_key": "Youtube",
                },
                {
                    "url": "https://www.youtube.com/watch?v=b",
                    "id": "b",
                    "title": "[Private video]",
                    "ie_key": "Youtube",
                },
                None,
            ],
        }
    )
    r = ytdlp.parse_resolve("some noise\n" + out, "https://youtube.com/playlist?list=x")
    assert r["kind"] == "playlist" and r["title"] == "Lofi tuyển tập"
    assert [e["title"] for e in r["entries"]] == ["Bài A", "[Private video]"]
    assert r["entries"][0] == {
        "url": "https://www.youtube.com/watch?v=a",
        "title": "Bài A",
        "duration": 201,
        "site": "youtube",
        "remoteId": "a",
        "available": True,
    }
    assert r["entries"][1]["available"] is False


def test_parse_single_video() -> None:
    out = json.dumps(
        {
            "id": "x1",
            "title": "Mưa",
            "extractor_key": "Soundcloud",
            "duration": 180.5,
            "webpage_url": "https://soundcloud.com/a/mua",
        }
    )
    r = ytdlp.parse_resolve(out, "https://on.soundcloud.com/short")
    assert r["kind"] == "single"
    assert r["entries"][0]["url"] == "https://soundcloud.com/a/mua"
    assert r["entries"][0]["site"] == "soundcloud" and r["entries"][0]["remoteId"] == "x1"


def test_js_runtime_flags(tmp_path: Path) -> None:
    t = ytdlp.Tools(tmp_path / "yt-dlp", node=tmp_path / "node")
    args = [str(a) for a in t.base()]
    assert args[args.index("--js-runtimes") + 1] == f"node:{tmp_path / 'node'}"
    assert "--ignore-config" in args  # a user's yt-dlp.conf must not change our output


def test_update_reports_last_line(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(args: list[object], **_: object) -> proc.ProcResult:
        assert args[1:] == ["-U"]
        return proc.ProcResult([], 0, b"Current version: 2026.08.19\nyt-dlp is up to date\n", b"")

    monkeypatch.setattr(proc, "run", fake_run)
    assert ytdlp.update(tmp_path / "yt-dlp") == "yt-dlp is up to date"


def test_url_key_uses_site_id() -> None:
    a = ingest.url_key("https://youtu.be/abc", "youtube", "abc")
    b = ingest.url_key("https://www.youtube.com/watch?v=abc&t=3", "youtube", "abc")
    assert a == b != ingest.url_key("https://youtu.be/abc")


def test_generic_links_are_keyed_by_url() -> None:
    """The generic extractor's id is the file name: a/mix.mp3 and b/mix.mp3 are different songs."""
    a = ingest.url_key("http://x/a/mix.mp3", "Generic", "mix")
    b = ingest.url_key("http://x/b/mix.mp3", "generic", "mix")
    assert a != b


# ------------------------------------------------------------- real yt-dlp, local web server


def tools() -> ytdlp.Tools:
    assert YTDLP
    return ytdlp.Tools(YTDLP, FFMPEG)


@pytest.fixture
def site(http_dir: tuple[Path, str]) -> tuple[Path, str]:
    root, base = http_dir
    sine(root / "a.mp3", 3, 440, "-c:a", "libmp3lame", "-b:a", "128k")
    sine(root / "b.webm", 2, 660, "-c:a", "libopus")
    (root / "feed.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Danh sách thử</title><link>{base}/</link>
<item><title>Bài A</title><guid>a1</guid><enclosure url="{base}/a.mp3" type="audio/mpeg"/></item>
<item><title>Bài B</title><guid>b1</guid><enclosure url="{base}/b.webm" type="audio/webm"/></item>
</channel></rss>""",
        encoding="utf-8",
    )
    return root, base


@requires_ffmpeg
@requires_ytdlp
def test_resolve_playlist_feed(site: tuple[Path, str]) -> None:
    _, base = site
    r = ytdlp.resolve(tools(), f"{base}/feed.xml")
    assert r["kind"] == "playlist" and r["title"] == "Danh sách thử"
    assert [e["title"] for e in r["entries"]] == ["Bài A", "Bài B"]
    assert all(e["available"] and e["url"].startswith(base) for e in r["entries"])


@requires_ffmpeg
@requires_ytdlp
def test_download_and_decode_link(site: tuple[Path, str], tmp_path: Path) -> None:
    _, base = site
    project = tmp_path / "Dự án"
    ctx = JobCtx()
    assert FFPROBE
    r = ingest.ingest_url(tools(), FFPROBE, project, f"{base}/a.mp3", ctx)  # type: ignore[arg-type]
    assert (project / r.cache_wav).is_file()
    assert r.duration == pytest.approx(3.0, abs=0.06)
    assert r.src_format == "mp3" and r.src_bitrate_kbps == pytest.approx(128, rel=0.1)
    assert r.title == "a"
    assert list((project / "cache" / "dl").iterdir()) == []  # original deleted after decoding
    fractions = [f for f, _ in ctx.events]
    assert fractions == sorted(fractions)

    again = ingest.ingest_url(tools(), FFPROBE, project, f"{base}/a.mp3", JobCtx())  # type: ignore[arg-type]
    assert again == r  # cache hit, no second download


@requires_ffmpeg
@requires_ytdlp
def test_missing_link_is_a_clear_error(site: tuple[Path, str], tmp_path: Path) -> None:
    _, base = site
    with pytest.raises(AppError) as e:
        ytdlp.resolve(tools(), f"{base}/không-có.mp3")
    assert e.value.code == "yt_not_found"


def test_channel_tabs_are_not_songs() -> None:
    out = json.dumps(
        {
            "_type": "playlist",
            "title": "Kênh nhạc",
            "entries": [
                {
                    "_type": "url",
                    "url": "https://www.youtube.com/@x/videos",
                    "title": "Videos",
                    "ie_key": "YoutubeTab",
                },
                {
                    "_type": "url",
                    "url": "https://www.youtube.com/watch?v=a",
                    "title": "Bài",
                    "ie_key": "Youtube",
                    "id": "a",
                },
            ],
        }
    )
    entries = ytdlp.parse_resolve(out, "https://www.youtube.com/@x")["entries"]
    assert [e["available"] for e in entries] == [False, True]
