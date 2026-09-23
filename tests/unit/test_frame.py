"""Verifies pseudocode 1.6: the frame, Rodrigues' rotation, the
transforms, the launch conversion, the triads, and the sign check
that fixes the handedness every later section relies on."""

import numpy as np
import pytest

from rotating_frame.core.frame import (Frame, cross_matrix, rodrigues,
                                       IDENTITY)

TOLERANCE = 1e-14          # a handful of products of order-one numbers
RANDOM = np.random.default_rng(20260922)
X_HAT, Y_HAT, Z_HAT = np.eye(3)


def unit(vector):
    return vector / np.linalg.norm(vector)


def test_cross_matrix_is_the_cross_product():
    for _ in range(5):
        vector, other = RANDOM.normal(size=(2, 3))
        assert np.allclose(cross_matrix(vector) @ other,
                           np.cross(vector, other), atol=TOLERANCE)


@pytest.mark.parametrize('axis', [X_HAT, Z_HAT, unit(np.array([1., 2., -3.]))])
@pytest.mark.parametrize('angle', [0.0, np.pi / 2, np.pi, -np.pi / 3, 1e4])
def test_rodrigues_is_a_proper_rotation_about_the_axis(axis, angle):
    rotation = rodrigues(axis, angle)
    assert np.allclose(rotation @ rotation.T, IDENTITY, atol=TOLERANCE)
    assert np.isclose(np.linalg.det(rotation), 1.0, atol=TOLERANCE)
    assert np.allclose(rotation @ axis, axis, atol=TOLERANCE)


def test_rotations_about_one_axis_compose_by_adding_angles():
    axis = unit(np.array([0.3, -0.4, 0.5]))
    for first, second in RANDOM.normal(size=(5, 2)):
        assert np.allclose(rodrigues(axis, first) @ rodrigues(axis, second),
                           rodrigues(axis, first + second), atol=TOLERANCE)


def test_rodrigues_is_right_handed():
    assert np.allclose(rodrigues(Z_HAT, np.pi / 2) @ X_HAT, Y_HAT,
                       atol=TOLERANCE)


def test_rodrigues_over_a_sample_axis():
    angles = np.linspace(0.0, 3.0, 7)
    stacked = rodrigues(Z_HAT, angles)
    assert stacked.shape == (7, 3, 3)
    for angle, rotation in zip(angles, stacked):
        assert np.allclose(rotation, rodrigues(Z_HAT, angle),
                           atol=TOLERANCE)


def test_frame_normalizes_its_axis_and_refuses_a_bad_one():
    frame = Frame([0.0, 0.0, 2.0], -1.5)
    assert np.allclose(frame.axis, Z_HAT)
    assert frame.rate == -1.5
    for bad in ([0.0, 0.0, 0.0], [np.nan, 0.0, 1.0], [np.inf, 0.0, 0.0]):
        with pytest.raises(ValueError, match='nonzero vector'):
            Frame(bad, 1.0)


def test_the_four_answers_and_their_shapes():
    frame = Frame(Z_HAT, 2.0)
    assert frame.angle(0.5) == 1.0
    assert np.allclose(frame.angular_velocity(0.5), 2.0 * Z_HAT)
    assert np.allclose(frame.angular_acceleration(0.5), 0.0)
    assert frame.rotation(0.5).shape == (3, 3)
    times = np.linspace(0.0, 1.0, 4)
    assert frame.angle(times).shape == (4,)
    assert frame.angular_velocity(times).shape == (4, 3)
    assert frame.angular_acceleration(times).shape == (4, 3)
    assert np.all(frame.angular_acceleration(times) == 0.0)
    assert frame.rotation(times).shape == (4, 3, 3)


def test_round_trip_between_the_frames():
    frame = Frame(unit(np.array([1.0, 1.0, 1.0])), 0.7)
    for _ in range(5):
        time = RANDOM.uniform(0.0, 10.0)
        position, velocity = RANDOM.normal(size=(2, 3))
        back = frame.to_inertial(time, *frame.to_rotating(time, position,
                                                          velocity))
        assert np.allclose(back[0], position, atol=TOLERANCE)
        assert np.allclose(back[1], velocity, atol=TOLERANCE)
        forth = frame.to_rotating(time, *frame.to_inertial(time, position,
                                                           velocity))
        assert np.allclose(forth[0], position, atol=TOLERANCE)
        assert np.allclose(forth[1], velocity, atol=TOLERANCE)


def test_a_particle_at_rest_in_the_frame_moves_at_the_rim_speed():
    for rate in (1.0, -1.0, 3.0):
        frame = Frame(Z_HAT, rate)
        position_rot = np.array([0.6, 0.8, 0.5])       # 1.0 from the axis
        position_in, velocity_in = frame.to_inertial(2.0, position_rot,
                                                     np.zeros(3))
        assert np.isclose(np.linalg.norm(velocity_in), abs(rate),
                          atol=TOLERANCE)
        expected_direction = np.sign(rate) * np.cross(Z_HAT, position_in)
        assert np.allclose(velocity_in, expected_direction * abs(rate),
                           atol=TOLERANCE)


def test_the_transform_preserves_the_norm():
    frame = Frame(unit(np.array([2.0, -1.0, 0.5])), 1.3)
    positions = RANDOM.normal(size=(6, 3))
    times = RANDOM.uniform(0.0, 5.0, size=6)
    positions_rot, _ = frame.to_rotating(times, positions,
                                         np.zeros((6, 3)))
    assert np.allclose(np.linalg.norm(positions_rot, axis=1),
                       np.linalg.norm(positions, axis=1), atol=TOLERANCE)


def test_launch_conversion():
    frame = Frame(Z_HAT, 1.0)
    position_rot = np.array([1.0, 0.0, 0.0])               # the rim
    velocity_rot = np.array([-0.5, 0.0, 0.0])              # toward the axis
    position_in, velocity_in = frame.launch_to_inertial(position_rot,
                                                        velocity_rot)
    expected = frame.to_inertial(0.0, position_rot, velocity_rot)
    assert np.allclose(position_in, expected[0], atol=TOLERANCE)
    assert np.allclose(velocity_in, expected[1], atol=TOLERANCE)
    # The rim speed appears along n_hat x r_hat, which here is +y.
    assert np.isclose(velocity_in @ Y_HAT, frame.rate, atol=TOLERANCE)
    assert np.isclose(velocity_in @ X_HAT, -0.5, atol=TOLERANCE)


@pytest.mark.parametrize('latitude_deg', [10.0, 45.0, 80.0])
def test_the_sign_check_moving_north_is_pushed_east(latitude_deg):
    """Design 1.8: with the axis along +z and the launch point in the
    x-z plane, east is +y, and a northward velocity feels a Coriolis
    push of 2 sin(latitude) east. The term itself is design 5's; this
    fixes the handedness it relies on."""
    frame = Frame(Z_HAT, 1.0)
    latitude = np.radians(latitude_deg)
    velocity_north = np.array([-np.sin(latitude), 0.0, np.cos(latitude)])
    coriolis = -2.0 * np.cross(frame.angular_velocity(0.0), velocity_north)
    assert np.allclose(coriolis, [0.0, 2.0 * np.sin(latitude), 0.0],
                       atol=TOLERANCE)
    assert coriolis[1] > 0.0


def test_the_two_triads():
    frame = Frame(Z_HAT, 1.0)
    time = 0.4
    rotating_triad = frame.rotating_triad_in_inertial(time)
    inertial_triad = frame.inertial_triad_in_rotating(time)
    assert np.allclose(rotating_triad, frame.rotation(time), atol=TOLERANCE)
    assert np.allclose(inertial_triad, frame.rotation(time).T,
                       atol=TOLERANCE)
    assert np.allclose(rotating_triad @ inertial_triad, IDENTITY,
                       atol=TOLERANCE)


def test_vectorized_transform_equals_the_row_by_row_one():
    frame = Frame(unit(np.array([0.0, 1.0, 1.0])), -0.9)
    times = RANDOM.uniform(0.0, 4.0, size=5)
    positions, velocities = RANDOM.normal(size=(2, 5, 3))
    stacked = frame.to_rotating(times, positions, velocities)
    for k in range(5):
        single = frame.to_rotating(times[k], positions[k], velocities[k])
        assert np.allclose(stacked[0][k], single[0], atol=TOLERANCE)
        assert np.allclose(stacked[1][k], single[1], atol=TOLERANCE)
    # A scalar time with an array of states broadcasts too.
    at_once = frame.to_rotating(times[0], positions, velocities)
    assert at_once[0].shape == (5, 3)
    assert np.allclose(at_once[0][2], frame.to_rotating(times[0], positions[2],
                                                        velocities[2])[0],
                       atol=TOLERANCE)
