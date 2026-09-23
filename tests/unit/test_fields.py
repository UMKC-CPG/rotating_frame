"""Verifies pseudocode 3.3: the contract, the three fields, the
frame-fixed field's defining property, the approximation estimate,
and the factory."""

import numpy as np
import pytest

from rotating_frame.core.frame import Frame
from rotating_frame.forces import (Approximation, NoForce,
                                   UniformGravityFrameFixed,
                                   UniformGravitySpaceFixed, make_field)
from rotating_frame.forces.fields import UNIFORM_APPROXIMATION_NOTE
from rotating_frame.forces.force_interface import CLOSED_FORM_NAMES

TOLERANCE = 1e-14
RANDOM = np.random.default_rng(3)
Z_HAT = np.array([0.0, 0.0, 1.0])
TIMES = np.linspace(0.0, 4.0, 9)


def random_states(count):
    return RANDOM.normal(size=(count, 3)), RANDOM.normal(size=(count, 3))


def test_no_force():
    field = NoForce()
    assert field.closed_form == 'line' and field.approximation is None
    assert field.potential.frames == {'inertial', 'rotating'}
    single = field.acceleration(0.3, np.ones(3), np.ones(3))
    assert single.shape == (3,) and np.all(single == 0.0)
    positions, velocities = random_states(9)
    stacked = field.acceleration(TIMES, positions, velocities)
    assert stacked.shape == (9, 3) and np.all(stacked == 0.0)
    assert np.all(field.potential.energy(positions) == 0.0)


def test_space_fixed_gravity_on_a_vertical_axis():
    frame = Frame(Z_HAT, 1.0)
    gravity = np.array([0.0, 0.0, -2.5])
    field = UniformGravitySpaceFixed(gravity, frame)
    assert field.closed_form == 'parabola'
    assert field.potential.frames == {'inertial', 'rotating'}
    positions, velocities = random_states(9)
    assert np.allclose(field.acceleration(TIMES, positions, velocities),
                       gravity, atol=TOLERANCE)
    assert np.allclose(field.acceleration(1.0, positions[0],
                                          velocities[0]), gravity)
    assert np.allclose(field.potential.energy(positions),
                       -positions @ gravity, atol=TOLERANCE)


def test_space_fixed_gravity_on_a_tilted_axis_is_inertial_only():
    frame = Frame([1.0, 0.0, 1.0], 1.0)
    field = UniformGravitySpaceFixed([0.0, 0.0, -1.0], frame)
    assert field.potential.frames == {'inertial'}


def test_frame_fixed_gravity_is_constant_in_rotating_components():
    frame = Frame(Z_HAT, 1.0)
    latitude = np.radians(45.0)
    gravity_rot = -9.0 * np.array([np.cos(latitude), 0.0, np.sin(latitude)])
    approximation = Approximation(UNIFORM_APPROXIMATION_NOTE, 100.0)
    field = UniformGravityFrameFixed(gravity_rot, frame, approximation)
    assert field.closed_form == 'rotating_parabola'
    assert field.potential.frames == {'rotating'}
    positions, velocities = random_states(9)
    # In inertial components it is the rotated constant vector.
    expected = np.einsum('nij,j->ni', frame.rotation(TIMES), gravity_rot)
    assert np.allclose(field.acceleration(TIMES, positions, velocities),
                       expected, atol=TOLERANCE)
    # In rotating components it is the constant vector at every time:
    # the defining property.
    rotating = field.acceleration_rotating(frame, TIMES, positions,
                                           velocities)
    assert np.allclose(rotating, gravity_rot, atol=TOLERANCE)
    assert np.allclose(field.acceleration_rotating(frame, 2.0, positions[3],
                                                   velocities[3]),
                       gravity_rot, atol=TOLERANCE)
    assert np.allclose(field.potential.energy(positions),
                       -positions @ gravity_rot, atol=TOLERANCE)


def test_the_two_kinds_coincide_on_a_vertical_axis_and_not_otherwise():
    frame = Frame(Z_HAT, 1.0)
    positions, velocities = random_states(9)
    vertical = np.array([0.0, 0.0, -3.0])
    space = UniformGravitySpaceFixed(vertical, frame)
    fixed = UniformGravityFrameFixed(vertical, frame, None)
    assert np.allclose(space.acceleration(TIMES, positions, velocities),
                       fixed.acceleration(TIMES, positions, velocities),
                       atol=TOLERANCE)
    latitude = np.radians(45.0)
    tilted = -3.0 * np.array([np.cos(latitude), 0.0, np.sin(latitude)])
    space = UniformGravitySpaceFixed(tilted, frame)
    fixed = UniformGravityFrameFixed(tilted, frame, None)
    difference = np.linalg.norm(
        space.acceleration(TIMES, positions, velocities)
        - fixed.acceleration(TIMES, positions, velocities), axis=1)
    perpendicular = 3.0 * np.cos(latitude)
    # The chord of the turned perpendicular part: 2 |g_perp| sin(t/2).
    assert np.allclose(difference, 2.0 * perpendicular * np.sin(TIMES / 2),
                       atol=1e-13)


def test_acceleration_rotating_is_the_transpose_of_the_direct_call():
    frame = Frame([0.3, -0.2, 0.9], 0.8)
    positions, velocities = random_states(9)
    for field in (NoForce(),
                  UniformGravitySpaceFixed([0.1, -0.4, -1.0], frame),
                  UniformGravityFrameFixed([0.2, 0.0, -1.0], frame, None)):
        position_in, velocity_in = frame.to_inertial(TIMES, positions,
                                                     velocities)
        direct = np.einsum('nji,nj->ni', frame.rotation(TIMES),
                           field.acceleration(TIMES, position_in,
                                              velocity_in))
        assert np.allclose(field.acceleration_rotating(frame, TIMES,
                                                       positions,
                                                       velocities),
                           direct, atol=TOLERANCE)


def test_the_approximation_estimate_and_sentence():
    approximation = Approximation(UNIFORM_APPROXIMATION_NOTE,
                                  timescale=100.0)
    assert approximation.estimate(10.0) == pytest.approx(0.5 * 0.01)
    # The Earth's t_E of 805.5 s at the sidereal rate, a five-second
    # drop: 1.9e-5 (design 3.4.2).
    rate = 7.2921150e-5
    earth = Approximation(UNIFORM_APPROXIMATION_NOTE,
                          timescale=805.5 * rate)
    assert earth.estimate(5.0 * rate) == pytest.approx(1.93e-5, rel=1e-2)
    assert '1.9e-05' in earth.sentence(5.0 * rate)
    assert 'launch point' in earth.sentence(5.0 * rate)


def test_every_closed_form_name_is_one_the_provider_knows():
    frame = Frame(Z_HAT, 1.0)
    for field in (NoForce(), UniformGravitySpaceFixed([0, 0, -1], frame),
                  UniformGravityFrameFixed([0, 0, -1], frame, None)):
        assert field.closed_form in CLOSED_FORM_NAMES


def test_make_field():
    frame = Frame(Z_HAT, 1.0)
    assert isinstance(make_field('none', None, None, frame), NoForce)
    assert isinstance(make_field('uniform', 'space', [0, 0, -1], frame),
                      UniformGravitySpaceFixed)
    assert isinstance(make_field('uniform', 'frame', [0, 0, -1], frame,
                                 None), UniformGravityFrameFixed)
    with pytest.raises(ValueError, match='force: kind'):
        make_field('uniform', None, [0, 0, -1], frame)
    with pytest.raises(ValueError, match='force: kind'):
        make_field('magnetic', 'space', [0, 0, -1], frame)
