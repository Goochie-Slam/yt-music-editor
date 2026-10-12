import json
import math

import pytest

from app.audio.curves import FIXTURE, Curve, fixture_data, gain_in, gain_out


@pytest.mark.parametrize("curve", list(Curve))
def test_endpoints(curve: Curve) -> None:
    assert gain_in(curve, 0) == pytest.approx(0, abs=1e-12)
    assert gain_in(curve, 1) == pytest.approx(1)
    assert gain_out(curve, 0) == pytest.approx(1)
    assert gain_out(curve, 1) == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize("curve", list(Curve))
def test_fade_out_is_fade_in_reversed(curve: Curve) -> None:
    for i in range(11):
        x = i / 10
        assert gain_out(curve, x) == pytest.approx(gain_in(curve, 1 - x))


@pytest.mark.parametrize("curve", list(Curve))
def test_monotonic_and_clamped(curve: Curve) -> None:
    xs = [i / 100 for i in range(101)]
    ys = [gain_in(curve, x) for x in xs]
    assert ys == sorted(ys)
    assert gain_in(curve, -1) == gain_in(curve, 0)
    assert gain_in(curve, 2) == gain_in(curve, 1)


def test_equal_power_keeps_power_constant_across_crossfade() -> None:
    for i in range(101):
        x = i / 100
        power = gain_in(Curve.EQUAL_POWER, x) ** 2 + gain_out(Curve.EQUAL_POWER, x) ** 2
        assert power == pytest.approx(1)


def test_linear_dips_3db_in_the_middle() -> None:
    power = gain_in(Curve.LINEAR, 0.5) ** 2 + gain_out(Curve.LINEAR, 0.5) ** 2
    assert 10 * math.log10(power) == pytest.approx(-3.01, abs=0.01)


def test_shared_fixture_is_up_to_date() -> None:
    """frontend/src/audio/curves.ts is tested against the same file."""
    stored = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fresh = fixture_data()
    assert stored.keys() == fresh.keys()
    for name, data in fresh.items():
        assert stored[name]["in"] == pytest.approx(data["in"], abs=1e-9)
        assert stored[name]["out"] == pytest.approx(data["out"], abs=1e-9)
