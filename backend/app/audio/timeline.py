"""Mix timeline maths (docs/CODING-GUIDE.md §5.3).

start[i+1]   = start[i] + len[i] - overlap[i]        (overlap < 0 leaves a silent gap)
chapter[i+1] = start[i+1] + overlap[i] / 2  if overlap[i] > 0   (middle of the crossfade)
             = start[i+1]                   otherwise           (start of the fade-in)

Chapter times drive both the on-screen "Now Playing" switch and chapters.txt, so they always agree.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class Seam:
    """The transition between track i and track i + 1."""

    fade_out: float
    fade_in: float
    overlap: float


@dataclass(frozen=True)
class Timeline:
    starts: list[float]
    chapters: list[float]
    total: float


def build(lengths: list[float], seams: list[Seam]) -> Timeline:
    if not lengths:
        return Timeline([], [], 0.0)
    if len(seams) != len(lengths) - 1:
        raise ValueError("need exactly one seam between each pair of tracks")
    starts, chapters = [0.0], [0.0]
    for i, seam in enumerate(seams):
        nxt = starts[i] + lengths[i] - seam.overlap
        starts.append(nxt)
        chapters.append(nxt + seam.overlap / 2 if seam.overlap > 0 else nxt)
    return Timeline(starts, chapters, starts[-1] + lengths[-1])


class SeamIssue(StrEnum):
    TOO_LONG = "too_long"  # F2.12: a fade or overlap longer than half the shorter track
    NEGATIVE_FADE = "negative_fade"


def validate_seam(seam: Seam, len_a: float, len_b: float) -> list[SeamIssue]:
    issues: list[SeamIssue] = []
    if seam.fade_out < 0 or seam.fade_in < 0:
        issues.append(SeamIssue.NEGATIVE_FADE)
    if max(seam.fade_out, seam.fade_in, seam.overlap) > 0.5 * min(len_a, len_b):
        issues.append(SeamIssue.TOO_LONG)
    return issues


class ChapterIssue(StrEnum):
    """YouTube only turns timestamps into chapters when these rules hold (F2.22)."""

    FIRST_NOT_ZERO = "first_not_zero"
    TOO_FEW = "too_few"  # needs at least 3
    TOO_SHORT = "too_short"  # each chapter at least 10 s


MIN_CHAPTERS = 3
MIN_CHAPTER_SEC = 10.0


def validate_chapters(chapters: list[float], total: float) -> list[ChapterIssue]:
    issues: list[ChapterIssue] = []
    if not chapters or round(chapters[0]) != 0:
        issues.append(ChapterIssue.FIRST_NOT_ZERO)
    if len(chapters) < MIN_CHAPTERS:
        issues.append(ChapterIssue.TOO_FEW)
    ends = [*chapters[1:], total]
    if any(e - s < MIN_CHAPTER_SEC for s, e in zip(chapters, ends, strict=True)):
        issues.append(ChapterIssue.TOO_SHORT)
    return issues


def format_timestamp(sec: float, force_hours: bool) -> str:
    s = round(sec)
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if force_hours or h else f"{m:02d}:{s:02d}"


def chapters_text(chapters: list[float], titles: list[str], total: float) -> str:
    hours = total >= 3600
    return (
        "\n".join(
            f"{format_timestamp(c, hours)} {t}" for c, t in zip(chapters, titles, strict=True)
        )
        + "\n"
    )
