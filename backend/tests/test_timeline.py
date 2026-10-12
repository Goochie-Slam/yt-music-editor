import pytest

from app.audio.timeline import (
    ChapterIssue,
    Seam,
    SeamIssue,
    build,
    chapters_text,
    validate_chapters,
    validate_seam,
)


def test_crossfade_overlaps_and_chapter_is_mid_crossfade() -> None:
    tl = build([200.0, 180.0], [Seam(6, 6, 6)])
    assert tl.starts == [0.0, 194.0]
    assert tl.chapters == [0.0, 197.0]
    assert tl.total == 374.0


def test_negative_overlap_leaves_gap_and_chapter_is_fade_in_start() -> None:
    tl = build([200.0, 180.0], [Seam(3, 1, -1.5)])
    assert tl.starts == [0.0, 201.5]
    assert tl.chapters == [0.0, 201.5]
    assert tl.total == 381.5


def test_zero_overlap_is_back_to_back() -> None:
    tl = build([10.0, 10.0, 10.0], [Seam(0, 0, 0), Seam(0, 0, 0)])
    assert tl.starts == [0.0, 10.0, 20.0]
    assert tl.total == 30.0


def test_empty_and_single_track() -> None:
    assert build([], []).total == 0
    single = build([42.0], [])
    assert single.starts == [0.0] and single.chapters == [0.0] and single.total == 42.0


def test_seam_count_must_match() -> None:
    with pytest.raises(ValueError):
        build([1.0, 2.0], [])


def test_validate_seam_too_long() -> None:
    assert validate_seam(Seam(6, 6, 6), 200, 180) == []
    assert validate_seam(Seam(6, 6, 6), 200, 11) == [SeamIssue.TOO_LONG]
    assert validate_seam(Seam(1, 6, 1), 200, 11) == [SeamIssue.TOO_LONG]


def test_validate_seam_negative_fade() -> None:
    assert SeamIssue.NEGATIVE_FADE in validate_seam(Seam(-1, 2, 0), 200, 200)


def test_chapters_rules() -> None:
    assert validate_chapters([0, 100, 200], 300) == []
    assert ChapterIssue.TOO_FEW in validate_chapters([0, 100], 300)
    assert ChapterIssue.FIRST_NOT_ZERO in validate_chapters([5, 100, 200], 300)
    assert ChapterIssue.TOO_SHORT in validate_chapters([0, 5, 200], 300)
    assert ChapterIssue.TOO_SHORT in validate_chapters([0, 100, 295], 300)


def test_chapters_text_uses_hours_when_mix_is_long() -> None:
    assert chapters_text([0, 197.4], ["A", "B"], 374) == "00:00 A\n03:17 B\n"
    assert chapters_text([0, 3725], ["A", "B"], 4000) == "00:00:00 A\n01:02:05 B\n"
