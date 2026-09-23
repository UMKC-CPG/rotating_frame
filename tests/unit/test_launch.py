"""Verifies pseudocode 7.4: the two velocity forms and the compass
convention, the resolution of rotating and inertial launches, offsets
along the Earth's local triad, the ring's geometry and symmetry at
time zero, and every refusal."""

import numpy as np
import pytest

from rotating_frame.core.frame import Frame, rodrigues
from rotating_frame.core.presets import (EARTH_ROTATION_RATE,
                                         launch_point_si, local_axes_si,
                                         preset)
from rotating_frame.launch import (LaunchSpec, LocalAxes, RingSpec,
                                   check_launch, check_ring,
                                   expand_ring, local_velocity,
                                   resolve_launch)

TOLERANCE = 1e-14
Z_HAT = np.array([0.0, 0.0, 1.0])
FRAME = Frame(Z_HAT, 1.0)
PLATFORM = LocalAxes(*np.eye(3), np.zeros(3))
LENGTH = 100.0


def earth_axes(latitude_deg=45.0):
    earth = preset('earth')
    latitude = np.radians(latitude_deg)
    east, north, up = local_axes_si(earth, latitude, EARTH_ROTATION_RATE)
    return LocalAxes(east, north, up,
                     launch_point_si(earth, latitude) / LENGTH)


def test_local_velocity_forms():
    assert np.allclose(local_velocity(LaunchSpec(np.zeros(3),
                                                 velocity=[1, 2, 3])),
                       [1.0, 2.0, 3.0])
    assert np.all(local_velocity(LaunchSpec(np.zeros(3))) == 0.0)
    north = local_velocity(LaunchSpec(np.zeros(3), speed=2.0, azimuth=0.0))
    assert np.allclose(north, [0.0, 2.0, 0.0], atol=TOLERANCE)
    east = local_velocity(LaunchSpec(np.zeros(3), speed=2.0,
                                     azimuth=np.pi / 2))
    assert np.allclose(east, [2.0, 0.0, 0.0], atol=TOLERANCE)
    up = local_velocity(LaunchSpec(np.zeros(3), speed=2.0,
                                   elevation=np.pi / 2))
    assert np.allclose(up, [0.0, 0.0, 2.0], atol=TOLERANCE)


def test_a_rotating_launch_gains_the_rim_speed():
    offset = np.array([0.6, 0.0, 0.2])
    resolved = resolve_launch(LaunchSpec(offset), PLATFORM, FRAME)
    assert np.allclose(resolved.position_in, offset)
    assert np.allclose(resolved.position_rot, offset)
    assert np.allclose(resolved.velocity_rot, 0.0)
    assert np.allclose(resolved.velocity_in, np.cross(Z_HAT, offset),
                       atol=TOLERANCE)
    assert resolved.spec.position is offset


def test_an_inertial_launch_at_rest_moves_backward_in_the_frame():
    offset = np.array([0.6, 0.0, 0.2])
    resolved = resolve_launch(LaunchSpec(offset, frame='inertial'),
                              PLATFORM, FRAME)
    assert np.allclose(resolved.velocity_in, 0.0)
    assert np.allclose(resolved.velocity_rot, -np.cross(Z_HAT, offset),
                       atol=TOLERANCE)
    assert np.allclose(resolved.position_in, resolved.position_rot)


def test_offsets_and_velocities_follow_the_earth_triad():
    axes = earth_axes()
    frame = Frame(Z_HAT, 1.0)
    spec = LaunchSpec(np.array([0.0, 0.0, 1.0]), speed=1.0,
                      azimuth=np.pi / 2)
    resolved = resolve_launch(spec, axes, frame)
    assert np.allclose(resolved.position_rot, axes.launch_point + axes.up,
                       atol=TOLERANCE)
    assert resolved.velocity_rot @ axes.east == pytest.approx(1.0)
    assert abs(resolved.velocity_rot @ axes.north) < TOLERANCE


def test_expand_ring():
    ring = RingSpec(count=12, radius=0.25, speed=0.3)
    launches = expand_ring(ring)
    assert len(launches) == 12
    for index, launch in enumerate(launches):
        assert launch.label == f'ring {index}'
        assert launch.frame == 'rotating'
        assert np.linalg.norm(launch.position) == pytest.approx(0.25)
        assert np.linalg.norm(launch.velocity) == pytest.approx(0.3)
        toward = -launch.position / 0.25
        assert np.allclose(launch.velocity, 0.3 * toward, atol=TOLERANCE)
    assert np.allclose(launches[0].position, [0.0, 0.25, 0.0],
                       atol=TOLERANCE)                    # north
    assert np.allclose(launches[3].position, [0.25, 0.0, 0.0],
                       atol=TOLERANCE)                    # east, 90 deg
    outward = expand_ring(RingSpec(12, 0.25, 0.3, sense='outward'))
    assert np.allclose(outward[5].velocity, -launches[5].velocity)
    moved = expand_ring(RingSpec(4, 0.1, 0.2, target=[1.0, 2.0, 0.0],
                                 height=0.5))
    assert np.allclose(moved[0].position, [1.0, 2.1, 0.5], atol=TOLERANCE)


def test_the_ring_is_symmetric_at_time_zero():
    launches = expand_ring(RingSpec(count=12, radius=0.25, speed=0.3))
    resolved = [resolve_launch(launch, PLATFORM, FRAME) for launch in
                launches]
    for index in range(12):
        rotation = rodrigues(Z_HAT, -2.0 * np.pi * index / 12)   # clockwise
        assert np.allclose(resolved[index].position_rot,
                           rotation @ resolved[0].position_rot,
                           atol=TOLERANCE)
        assert np.allclose(resolved[index].velocity_rot,
                           rotation @ resolved[0].velocity_rot,
                           atol=TOLERANCE)


@pytest.mark.parametrize('spec, rule, key', [
    (LaunchSpec(np.zeros(3), velocity=[1, 0, 0], speed=1.0), 'duration',
     'velocity or speed'),
    (LaunchSpec(np.zeros(3), elevation=0.3), 'duration',
     'launch.elevation: needs'),
    (LaunchSpec(np.zeros(3), speed=1.0, elevation=2.0), 'duration',
     'launch.elevation: must'),
    (LaunchSpec(np.zeros(3), speed=-1.0), 'duration', 'launch.speed'),
    (LaunchSpec(np.zeros(3), frame='sideways'), 'duration',
     'launch.frame'),
    (LaunchSpec(np.array([0.0, 0.0, -0.1])), 'lands', 'below the ground'),
    (LaunchSpec(np.zeros(3)), 'lands', 'no upward velocity'),
    (LaunchSpec(np.array([0.8, 0.8, 0.0])), 'leaves', 'outside the disc')])
def test_check_launch_refuses_naming_the_key(spec, rule, key):
    with pytest.raises(ValueError, match=key):
        check_launch(spec, rule)


def test_check_launch_passes_the_ordinary_cases():
    check_launch(LaunchSpec(np.array([0.0, 0.0, 1.0])), 'lands')
    check_launch(LaunchSpec(np.zeros(3), speed=1.0, elevation=0.5), 'lands')
    check_launch(LaunchSpec(np.array([0.9, 0.0, 0.0]), velocity=[-1, 0, 0]),
                 'leaves')
    check_launch(LaunchSpec(np.zeros(3), frame='inertial'), 'duration')


@pytest.mark.parametrize('ring, rule, key', [
    (RingSpec(0, 0.2, 0.1), 'duration', 'ring.count'),
    (RingSpec(4, 0.0, 0.1), 'duration', 'ring.radius'),
    (RingSpec(4, 0.2, -0.1), 'duration', 'ring.speed'),
    (RingSpec(4, 0.2, 0.1, sense='sideways'), 'duration', 'ring.sense'),
    (RingSpec(4, 0.2, 0.1, height=-1.0), 'lands', 'ring.height'),
    (RingSpec(4, 1.5, 0.1), 'leaves', 'outside the disc')])
def test_check_ring_refuses_naming_the_key(ring, rule, key):
    with pytest.raises(ValueError, match=key):
        check_ring(ring, rule)
    check_ring(RingSpec(12, 0.25, 0.3), 'leaves')
