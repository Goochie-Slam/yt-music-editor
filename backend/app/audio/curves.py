"""Fade gain curves — must stay identical to frontend/src/audio/curves.ts.

Both implementations are checked against shared/fixtures/curves.json
(regenerate with `python -m app.audio.curves`).

Convention: x in [0, 1] is fade progress. gain_in(x) rises 0 -> 1 and the fade-out is the
same curve reversed in time: gain_out(x) = gain_in(1 - x).
"""

from __future__ import annotations

import json
import math
from enum import StrEnum
from pathlib import Path


class Curve(StrEnum):
    EQUAL_POWER = "equal-power"  # constant perceived loudness across a crossfade
    LINEAR = "linear"  # dips ~3 dB in the middle of a crossfade
    LOG = "log"  # roughly linear in dB: the most natural fade to / from silence
    S_CURVE = "s-curve"  # slow at both ends


LOG_EXPONENT = 2.5


def gain_in(curve: Curve, x: float) -> float:
    x = min(1.0, max(0.0, x))
    match curve:
        case Curve.EQUAL_POWER:
            return math.sin(x * math.pi / 2)
        case Curve.LINEAR:
            return x
        case Curve.LOG:
            return math.pow(x, LOG_EXPONENT)
        case Curve.S_CURVE:
            return (1 - math.cos(math.pi * x)) / 2


def gain_out(curve: Curve, x: float) -> float:
    return gain_in(curve, 1.0 - x)


FIXTURE = Path(__file__).resolve().parents[3] / "shared" / "fixtures" / "curves.json"
FIXTURE_POINTS = 101
# libm differs in the last bit between Windows and Linux; rounding keeps the file byte-identical
# on both (CI checks it is up to date). Tests compare with a 1e-6 tolerance anyway.
FIXTURE_DIGITS = 12


def fixture_data() -> dict[str, dict[str, list[float]]]:
    xs = [i / (FIXTURE_POINTS - 1) for i in range(FIXTURE_POINTS)]
    r = FIXTURE_DIGITS
    return {
        c.value: {
            "in": [round(gain_in(c, x), r) for x in xs],
            "out": [round(gain_out(c, x), r) for x in xs],
        }
        for c in Curve
    }


if __name__ == "__main__":
    text = json.dumps(fixture_data(), indent=1) + "\n"
    FIXTURE.write_text(text, encoding="utf-8", newline="\n")  # same bytes on Windows
    print(f"wrote {FIXTURE}")
