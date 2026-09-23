"""Verifies pseudocode 2.5 for `core/presets.py`: the three presets
and their numbers, the launch point, the gravity vector, the local
axes from the plumb line, and the tilt."""

import numpy as np
import pytest

from rotating_frame.core.presets import (EARTH_ATTRACTION, EARTH_RADIUS,
                                         EARTH_ROTATION_RATE, PRESETS,
                                         effective_gravity_si,
                                         gravity_vector_si, launch_point_si,
                                         local_axes_si, plumb_line_tilt,
                                         preset)

TOLERANCE = 1e-14


def test_the_presets_and_their_numbers():
    assert set(PRESETS) == {'turntable', 'merry_go_round', 'earth'}
    assert preset('earth').gravity_si == pytest.approx(9.820, abs=5e-4)
    assert EARTH_ATTRACTION == pytest.approx(9.820, abs=5e-4)
    assert preset('turntable').rate_si == pytest.approx(3.4907, rel=1e-4)
    for name, each in PRESETS.items():
        assert each.name == name
        assert np.isclose(np.linalg.norm(each.axis), 1.0)
        assert set(each.display_units) >= {'length', 'time', 'speed',
                                           'acceleration', 'angle'}
        assert 'duration' in each.stop_rules
    with pytest.raises(ValueError, match='turntable, merry_go_round, earth'):
        preset('moon')


def test_the_launch_point():
    latitude = np.radians(45.0)
    point = launch_point_si(preset('earth'), latitude)
    assert np.isclose(np.linalg.norm(point), EARTH_RADIUS)
    assert np.isclose(point[2], EARTH_RADIUS * np.sin(latitude))
    assert point[1] == 0.0
    for name in ('turntable', 'merry_go_round'):
        assert np.all(launch_point_si(preset(name)) == 0.0)


def test_the_gravity_vector():
    assert gravity_vector_si(preset('turntable')) is None
    assert np.allclose(gravity_vector_si(preset('merry_go_round')),
                       [0.0, 0.0, -9.81])
    latitude = np.radians(30.0)
    earth_gravity = gravity_vector_si(preset('earth'), latitude)
    # Toward the center, with the bare attraction's magnitude.
    assert np.isclose(np.linalg.norm(earth_gravity), EARTH_ATTRACTION)
    assert np.allclose(earth_gravity / EARTH_ATTRACTION,
                       -launch_point_si(preset('earth'), latitude)
                       / EARTH_RADIUS, atol=TOLERANCE)


@pytest.mark.parametrize('name', ['turntable', 'merry_go_round', 'earth'])
@pytest.mark.parametrize('latitude_deg', [10.0, 45.0, 80.0])
def test_the_local_axes_are_orthonormal_and_right_handed(name,
                                                         latitude_deg):
    east, north, up = local_axes_si(preset(name), np.radians(latitude_deg))
    for axis in (east, north, up):
        assert np.isclose(np.linalg.norm(axis), 1.0, atol=TOLERANCE)
    assert abs(east @ north) < TOLERANCE
    assert abs(north @ up) < TOLERANCE
    assert abs(up @ east) < TOLERANCE
    assert np.allclose(np.cross(east, north), up, atol=TOLERANCE)


def test_the_earth_axes_point_the_right_way():
    latitude = np.radians(45.0)
    east, north, up = local_axes_si(preset('earth'), latitude)
    assert east @ np.array([0.0, 1.0, 0.0]) > 0.999     # +y is east
    radial = launch_point_si(preset('earth'), latitude) / EARTH_RADIUS
    assert np.degrees(np.arccos(up @ radial)) < 0.1     # nearly radial
    assert north[2] > 0.0                                # north is upward
                                                         #   in z, i.e.
                                                         #   toward the pole
    assert np.allclose(local_axes_si(preset('turntable')), np.eye(3))


def test_the_plumb_line_numbers():
    earth = preset('earth')
    tilt = np.degrees(plumb_line_tilt(earth, np.radians(45.0)))
    assert tilt == pytest.approx(0.099, abs=5e-4)
    at_equator = effective_gravity_si(earth, 0.0)
    assert EARTH_ATTRACTION - at_equator == pytest.approx(
        EARTH_ROTATION_RATE ** 2 * EARTH_RADIUS, rel=1e-6)
    assert EARTH_ROTATION_RATE ** 2 * EARTH_RADIUS == pytest.approx(
        0.0339, abs=5e-5)
    assert effective_gravity_si(preset('merry_go_round')) == 9.81
    assert effective_gravity_si(preset('turntable')) is None


def test_a_faster_earth_tilts_the_plumb_line_more():
    earth = preset('earth')
    latitude = np.radians(45.0)
    plain = plumb_line_tilt(earth, latitude)
    doubled = plumb_line_tilt(earth, latitude, 2.0 * EARTH_ROTATION_RATE)
    assert doubled == pytest.approx(4.0 * plain, rel=1e-2)   # first order
    assert np.degrees(doubled) == pytest.approx(0.397, abs=5e-3)
