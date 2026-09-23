"""The drop oracle of pseudocode 4.6 and design 4.6, the spike made a
test: a stone dropped from rest in the rotating frame at height h at
latitude lambda lands east of the point below it by the textbook
(1/3) g Omega t^3 cos(lambda) times (1 - Omega^2 R_E / g0), the same
factor at every latitude, and north of it by a second-order amount.
Everything is assembled from the sections below the store: the
presets, the scales, the frame, the field, the closed form, the
transform, and the stopping rule."""

import numpy as np
import pytest

from rotating_frame.core.frame import Frame
from rotating_frame.core.natural_units import make_scales
from rotating_frame.core.presets import (EARTH_ATTRACTION, EARTH_RADIUS,
                                         EARTH_ROTATION_RATE,
                                         effective_gravity_si,
                                         gravity_vector_si, launch_point_si,
                                         local_axes_si, preset)
from rotating_frame.forces import UniformGravityFrameFixed
from rotating_frame.motion import LandsRule, provide

HEIGHT_SI = 100.0
CORRECTION = 1.0 - EARTH_ROTATION_RATE ** 2 * EARTH_RADIUS / EARTH_ATTRACTION


def drop(latitude_deg):
    earth = preset('earth')
    latitude = np.radians(latitude_deg)
    scales = make_scales(EARTH_ROTATION_RATE, 100.0)
    frame = Frame(earth.axis, 1.0)
    east, north, up = local_axes_si(earth, latitude, scales.rate)
    launch_point = launch_point_si(earth, latitude) / scales.length
    gravity_rot = gravity_vector_si(earth, latitude) / scales.acceleration
    field = UniformGravityFrameFixed(gravity_rot, frame, None)
    position_rot = launch_point + (HEIGHT_SI / scales.length) * up
    launch = frame.launch_to_inertial(position_rot, np.zeros(3))
    rule = LandsRule(launch_point, up)
    trajectory = provide(launch, field, frame, 10.0 / scales.time, 1000,
                         rule)
    event = trajectory.stop
    position_rot_at_stop, _ = frame.to_rotating(event.time,
                                                event.position_in,
                                                event.velocity_in)
    displacement_si = (position_rot_at_stop - launch_point) * scales.length
    return (event.time * scales.time, displacement_si @ east,
            displacement_si @ north,
            effective_gravity_si(earth, latitude, scales.rate))


@pytest.mark.parametrize('latitude_deg', [10.0, 30.0, 45.0, 60.0, 80.0])
def test_the_stone_lands_east_by_the_textbook_amount_times_the_factor(
        latitude_deg):
    landing_time, east, north, g_effective = drop(latitude_deg)
    textbook = (EARTH_ATTRACTION * EARTH_ROTATION_RATE * landing_time ** 3
                * np.cos(np.radians(latitude_deg)) / 3.0)
    assert east == pytest.approx(textbook * CORRECTION, rel=1e-5)
    assert abs(north) < (EARTH_ROTATION_RATE * landing_time) ** 2 * HEIGHT_SI
    assert landing_time == pytest.approx(np.sqrt(2.0 * HEIGHT_SI
                                                 / g_effective), rel=1e-6)


def test_the_correction_factor_is_the_stated_number():
    assert CORRECTION == pytest.approx(0.99655, abs=5e-6)
