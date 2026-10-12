"""Parse a pasted tracklist ("mm:ss Title" per line) into segments to cut (F1.5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

# Optional bracket around the time, then an optional dash / pipe separator before the title.
_LINE = re.compile(
    r"^\s*[\[(]?(?:(?P<h>\d{1,2}):)?(?P<m>\d{1,2}):(?P<s>\d{2})[\])]?\s*(?:[-–—|:]\s*)?(?P<title>.+?)\s*$"
)


class LineError(StrEnum):
    BAD_FORMAT = "bad_format"
    BAD_SECONDS = "bad_seconds"  # e.g. 03:75
    NOT_INCREASING = "not_increasing"
    PAST_END = "past_end"  # timestamp at or after the end of the source file


@dataclass(frozen=True)
class Segment:
    index: int
    title: str
    start: float
    end: float


@dataclass(frozen=True)
class ParseError:
    line_no: int  # 1-based, as the user sees it
    text: str
    error: LineError


@dataclass(frozen=True)
class ParseResult:
    segments: list[Segment]
    errors: list[ParseError]


def parse(text: str, source_duration: float) -> ParseResult:
    entries: list[tuple[float, str]] = []
    errors: list[ParseError] = []
    for no, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        m = _LINE.match(raw)
        if not m:
            errors.append(ParseError(no, raw, LineError.BAD_FORMAT))
            continue
        h, mi, s = int(m["h"] or 0), int(m["m"]), int(m["s"])
        if s >= 60 or (m["h"] and mi >= 60):
            errors.append(ParseError(no, raw, LineError.BAD_SECONDS))
            continue
        t = float(h * 3600 + mi * 60 + s)
        if entries and t <= entries[-1][0]:
            errors.append(ParseError(no, raw, LineError.NOT_INCREASING))
            continue
        if t >= source_duration:
            errors.append(ParseError(no, raw, LineError.PAST_END))
            continue
        entries.append((t, m["title"]))
    ends = [t for t, _ in entries[1:]] + ([source_duration] if entries else [])
    segments = [
        Segment(i + 1, title, start, end)
        for i, ((start, title), end) in enumerate(zip(entries, ends, strict=True))
    ]
    return ParseResult(segments, errors)
