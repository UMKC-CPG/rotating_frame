"""Verifies pseudocode 2.5 for `core/natural_units.py`: the scales,
the way in and out, and the speed ratio."""

import numpy as np
import pytest

from rotating_frame.core.natural_units import (KINDS, Scales, factor,
                                               make_scales, speed_ratio,
                                               to_natural, to_real)

EARTH_RATE = 7.2921150e-5


def test_the_earth_scales_at_a_hundred_metres():
    scales = make_scales(EARTH_RATE, 100.0)
    assert scales.rate == EARTH_RATE
    assert scales.exaggeration == 1.0 and scales.mass is None
    assert scales.time == pytest.approx(13713.44, rel=1e-6)
    assert scales.speed == pytest.approx(7.2921150e-3, rel=1e-12)
    assert scales.acceleration == pytest.approx(5.3175e-7, rel=1e-4)


def test_the_exaggeration_multiplies_the_rate():
    plain = make_scales(EARTH_RATE, 100.0)
    doubled = make_scales(EARTH_RATE, 100.0, exaggeration=2.0)
    assert doubled.rate == 2.0 * plain.rate
    assert doubled.time == pytest.approx(plain.time / 2.0, rel=1e-15)
    assert doubled.acceleration == pytest.approx(4.0 * plain.acceleration,
                                                 rel=1e-15)
    assert doubled.exaggeration == 2.0


@pytest.mark.parametrize('arguments, key', [
    ((0.0, 1.0), 'frame.rate'), ((1.0, 0.0), 'frame.length_scale'),
    ((1.0, -1.0), 'frame.length_scale'),
    ((1.0, 1.0, None, 0.0), 'frame.exaggeration'),
    ((1.0, 1.0, None, -2.0), 'frame.exaggeration')])
def test_bad_scales_are_refused_naming_the_key(arguments, key):
    with pytest.raises(ValueError, match=key):
        make_scales(*arguments)


def test_round_trips_for_every_kind():
    scales = make_scales(0.5, 2.0, mass_si=0.2, exaggeration=3.0)
    values = np.array([0.0, 1.5, -7.25, 1e-6])
    for kind in KINDS:
        back = to_real(scales, to_natural(scales, values, kind), kind)
        assert np.allclose(back, values, rtol=1e-12, atol=0.0)
        scalar = to_real(scales, to_natural(scales, 3.7, kind), kind)
        assert scalar == pytest.approx(3.7, rel=1e-12)


def test_the_factors_are_the_stated_ones():
    scales = Scales(rate=2.0, length=3.0, mass=0.5, exaggeration=1.0)
    assert factor(scales, 'time') == 0.5
    assert factor(scales, 'length') == 3.0
    assert factor(scales, 'speed') == 6.0
    assert factor(scales, 'acceleration') == 12.0
    assert factor(scales, 'rate') == 2.0
    assert factor(scales, 'angle') == 1.0
    assert factor(scales, 'mass') == 0.5
    with pytest.raises(ValueError, match='unknown kind'):
        factor(scales, 'temperature')


def test_mass_without_a_mass_is_refused():
    scales = make_scales(1.0, 1.0)
    with pytest.raises(ValueError, match='no mass'):
        to_natural(scales, 1.0, 'mass')


def test_the_speed_ratio_of_the_two_worked_cases():
    turntable = make_scales((33.0 + 1.0 / 3.0) * 2.0 * np.pi / 60.0, 0.30)
    assert speed_ratio(turntable, 0.5) == pytest.approx(0.477, rel=2e-3)
    earth = make_scales(EARTH_RATE, 100.0)
    assert speed_ratio(earth, 10.0) == pytest.approx(1371.0, rel=2e-3)
