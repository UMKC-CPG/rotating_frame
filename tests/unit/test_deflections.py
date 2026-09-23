"""Verifies pseudocode 6.6 for `analysis/closed_form_deflections.py`:
when the overlay applies; the classroom cases of the Coriolis part
(the drop, the vertical launch, the horizontal launch); and the full
formula against the exact motion less the inertial-expectation ghost,
within the derived tolerance."""

import numpy as np
import pytest

from rotating_frame.analysis import (coriolis_deflection,
                                     first_order_deflection,
                                     first_order_tolerance, overlay_applies)
from rotating_frame.core.frame import Frame
from rotating_frame.core.presets import (EARTH_ATTRACTION, EARTH_RADIUS,
                                         EARTH_ROTATION_RATE)
from rotating_frame.forces import UniformGravityFrameFixed
from rotating_frame.motion.closed_forms import rotating_parabola

# Local axes as the frame's own: east = x, north = y, up = z, with the
# Earth's axis tilted in the north-up plane by the latitude.
EAST, NORTH, UP = np.eye(3)
G = EARTH_ATTRACTION
OMEGA = EARTH_ROTATION_RATE
EARTH_RATIO = OMEGA ** 2 * EARTH_RADIUS / G


def earth_frame(latitude_deg):
    latitude = np.radians(latitude_deg)
    return Frame(np.cos(latitude) * NORTH + np.sin(latitude) * UP, OMEGA)


def test_overlay_applies():
    assert overlay_applies(earth_frame(45.0), 5.0)          # a drop
    assert not overlay_applies(Frame(UP, 1.0), 2.0 * np.pi)  # a turn


@pytest.mark.parametrize('latitude_deg', [10.0, 45.0, 80.0])
def test_the_drop_lands_east(latitude_deg):
    frame = earth_frame(latitude_deg)
    times = np.array([1.0, 3.0, 4.5])
    deflection = coriolis_deflection(frame, np.zeros(3), -G * UP, times)
    expected = np.outer(G * OMEGA * times ** 3
                        * np.cos(np.radians(latitude_deg)) / 3.0, EAST)
    assert np.allclose(deflection, expected, atol=1e-14)


def test_a_vertical_launch_lands_west():
    frame = earth_frame(45.0)
    speed = 20.0
    flight = 2.0 * speed / G
    deflection = coriolis_deflection(frame, speed * UP, -G * UP,
                                     np.array([flight]))[0]
    westward = -(4.0 / 3.0) * speed ** 3 * OMEGA * np.cos(np.radians(45.0)) \
        / G ** 2
    assert deflection @ EAST == pytest.approx(westward, rel=1e-12)
    assert deflection @ EAST == pytest.approx(-5.7035e-3, rel=1e-4)


def test_a_horizontal_launch_east_deflects_south_and_up():
    frame = earth_frame(45.0)
    speed, time = 30.0, 2.0
    deflection = coriolis_deflection(frame, speed * EAST, np.zeros(3),
                                     np.array([time]))[0]
    magnitude = OMEGA * speed * time ** 2
    assert deflection @ NORTH == pytest.approx(
        -magnitude * np.sin(np.radians(45.0)), rel=1e-12)   # to the right
    assert deflection @ UP == pytest.approx(
        magnitude * np.cos(np.radians(45.0)), rel=1e-12)    # Eotvos, up
    assert deflection @ EAST == pytest.approx(0.0, abs=1e-14)


def test_first_order_tolerance():
    frame = earth_frame(45.0)
    turned = OMEGA * 5.0
    assert first_order_tolerance(frame, 5.0, EARTH_RATIO) == pytest.approx(
        turned + 2.0 * EARTH_RATIO + turned ** 2)
    assert first_order_tolerance(Frame(UP, 1.0), 0.05, 0.0) == pytest.approx(
        0.05 + 0.0025)


@pytest.mark.parametrize('case', ['drop', 'vertical', 'horizontal'])
def test_the_formula_against_the_exact_motion(case):
    """The exact rotating parabola, carried into the rotating frame,
    less the ghost (the plain parabola under the bare attraction, the
    inertial expectation), against the full first-order formula,
    within the derived tolerance; and the eastward component of the
    drop, pure Coriolis, against the Coriolis part within the sharper
    factor of design 4.6."""
    frame = earth_frame(45.0)
    latitude = np.radians(45.0)
    launch_point = EARTH_RADIUS * (np.cos(latitude) * UP
                                   - np.sin(latitude) * NORTH)
    radial = launch_point / EARTH_RADIUS
    gravity_rot = -G * radial
    field = UniformGravityFrameFixed(gravity_rot, frame, None)
    if case == 'drop':
        velocity_rot0, duration = np.zeros(3), 4.5
    elif case == 'vertical':
        velocity_rot0, duration = 20.0 * radial, 2.0 * 20.0 / G
    else:
        velocity_rot0, duration = 30.0 * EAST, 2.0
    times = np.array([duration])
    position_rot0 = launch_point + 100.0 * radial
    position_in0, velocity_in0 = frame.launch_to_inertial(position_rot0,
                                                          velocity_rot0)
    positions_in, velocities_in = rotating_parabola(
        position_in0, velocity_in0, gravity_rot, frame, times)
    positions_rot, _ = frame.to_rotating(times, positions_in, velocities_in)
    ghost = position_rot0 + np.outer(times, velocity_rot0) \
        + 0.5 * np.outer(times ** 2, gravity_rot)
    exact = (positions_rot - ghost)[0]
    formula = first_order_deflection(frame, position_rot0, velocity_rot0,
                                     gravity_rot, times)[0]
    tolerance = first_order_tolerance(frame, duration, EARTH_RATIO)
    assert np.linalg.norm(exact - formula) <= tolerance * np.linalg.norm(
        formula)
    if case == 'drop':
        east_exact = exact @ EAST
        east_coriolis = coriolis_deflection(frame, velocity_rot0,
                                            gravity_rot, times)[0] @ EAST
        assert east_exact / east_coriolis == pytest.approx(
            1.0 - EARTH_RATIO, rel=1e-5)
