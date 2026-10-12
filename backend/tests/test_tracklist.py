from app.audio.tracklist import LineError, parse

SRC = 2 * 3600 + 3 * 60 + 40  # 2:03:40


def test_parses_common_formats() -> None:
    text = """00:00 Intro — Blue Train
4:12 - Autumn Café
[09:30] Soft Echo
1:05:20 | Late Drive
1:12:44 Warm Garden"""
    r = parse(text, SRC)
    assert r.errors == []
    assert [(s.start, s.title) for s in r.segments] == [
        (0, "Intro — Blue Train"),
        (252, "Autumn Café"),
        (570, "Soft Echo"),
        (3920, "Late Drive"),
        (4364, "Warm Garden"),
    ]
    assert [s.end for s in r.segments] == [252, 570, 3920, 4364, SRC]
    assert [s.index for s in r.segments] == [1, 2, 3, 4, 5]


def test_reports_line_number_and_text_for_bad_lines() -> None:
    text = "00:00 A\n\n28.10 Sai định dạng\n03:75 B\n05:00 C"
    r = parse(text, SRC)
    assert [(e.line_no, e.error) for e in r.errors] == [
        (3, LineError.BAD_FORMAT),
        (4, LineError.BAD_SECONDS),
    ]
    assert r.errors[0].text == "28.10 Sai định dạng"
    assert [s.title for s in r.segments] == ["A", "C"]


def test_rejects_non_increasing_and_past_end() -> None:
    r = parse("10:00 A\n05:00 B\n10:00 C\n3:00:00 D", SRC)
    assert [e.error for e in r.errors] == [
        LineError.NOT_INCREASING,
        LineError.NOT_INCREASING,
        LineError.PAST_END,
    ]
    assert len(r.segments) == 1 and r.segments[0].end == SRC


def test_blank_input() -> None:
    r = parse("\n  \n", SRC)
    assert r.segments == [] and r.errors == []
