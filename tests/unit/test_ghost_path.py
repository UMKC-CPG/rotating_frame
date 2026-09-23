"""Verifies pseudocode 6.6 for `analysis/ghost_path.py`: the
constant-force predicate, the ghost of a drop as a straight fall in
the rider's view, and the ghost as the integration with the terms
removed."""

import numpy as np

from rotating_frame.analysis import CheckSettings, ghost_path
from rotating_frame.analysis.ghost_path import (ghost_derivative,
                                                rotating_force_is_constant)
from rotating_frame.core.frame import Frame
from rotating_frame.forces import (NoForce, UniformGravityFrameFixed,
                                   UniformGravitySpaceFixed)
from rotating_frame.motion.integrators import integrate

Z_HAT = np.array([0.0, 0.0, 1.0])
SETTINGS = CheckSettings()


def test_the_constant_force_predicate():
    vertical = Frame(Z_HAT, 1.0)
    tilted = Frame([1.0, 0.0, 1.0], 1.0)
    assert rotating_force_is_constant(NoForce(), vertical)
    assert rotating_force_is_constant(
        UniformGravityFrameFixed([0.3, 0.0, -1.0], tilted, None), tilted)
    assert rotating_force_is_constant(
        UniformGravitySpaceFixed([0.0, 0.0, -1.0], vertical), vertical)
    assert not rotating_force_is_constant(
        UniformGravitySpaceFixed([0.0, 0.0, -1.0], tilted), tilted)


def test_the_ghost_of_a_drop_is_a_straight_fall():
    frame = Frame(Z_HAT, 1.0)
    latitude = np.radians(45.0)
    radial = np.array([np.cos(latitude), 0.0, np.sin(latitude)])
    gravity_rot = -2.0 * radial
    field = UniformGravityFrameFixed(gravity_rot, frame, None)
    launch_point = 5.0 * radial
    position_rot0 = launch_point + 0.5 * radial
    launch = frame.launch_to_inertial(position_rot0, np.zeros(3))
    times = np.linspace(0.0, 0.3, 7)
    ghost = ghost_path(field, frame, launch, launch_point, times, SETTINGS)
    expected = 0.5 * radial + 0.5 * np.outer(times ** 2, gravity_rot)
    assert np.allclose(ghost, expected, atol=1e-14)


def test_the_ghost_is_the_integration_with_the_terms_removed():
    frame = Frame([0.2, 0.1, 1.0], 1.0)
    field = UniformGravitySpaceFixed([0.0, 0.0, -1.0], frame)   # tilted:
                                                                #   integrated
    launch = (np.array([1.0, 0.0, 0.5]), np.array([0.1, 0.4, 0.0]))
    launch_point = np.zeros(3)
    times = np.linspace(0.0, 1.0, 11)
    ghost = ghost_path(field, frame, launch, launch_point, times, SETTINGS)
    position_rot0, velocity_rot0 = frame.to_rotating(0.0, *launch)
    reference = integrate(ghost_derivative(field, frame),
                          np.concatenate((position_rot0, velocity_rot0)),
                          times, 'dop853', rtol=1e-12, atol=1e-14)
    assert np.allclose(ghost, reference.states[:, :3] - launch_point,
                       atol=1e-9)
