"""Verifies pseudocode 4.6 for `motion/integrators.py`: the orders of
the fixed-step schemes on the rotating-frame equation of the free
particle, whose exact answer is the transform of a line; the
adaptive scheme; and `evaluate` between samples."""

import numpy as np
import pytest

from rotating_frame.core.frame import Frame
from rotating_frame.forces import NoForce
from rotating_frame.motion.equations_of_motion import (inertial_derivative,
                                                       rotating_derivative)
from rotating_frame.motion.integrators import integrate

Z_HAT = np.array([0.0, 0.0, 1.0])
FRAME = Frame(Z_HAT, 1.0)
POSITION0 = np.array([1.0, 0.0, 0.0])
VELOCITY0 = np.array([0.0, 0.5, 0.3])
TIMES = np.linspace(0.0, 2.0, 21)


def exact_rotating_states(times):
    positions_in = POSITION0 + np.outer(times, VELOCITY0)
    velocities_in = np.broadcast_to(VELOCITY0, positions_in.shape)
    positions_rot, velocities_rot = FRAME.to_rotating(times, positions_in,
                                                      velocities_in)
    return np.hstack((positions_rot, velocities_rot))


def rotating_launch():
    position_rot, velocity_rot = FRAME.to_rotating(0.0, POSITION0, VELOCITY0)
    return np.concatenate((position_rot, velocity_rot))


def maximum_error(method, substeps):
    derivative = rotating_derivative(NoForce(), FRAME)
    integration = integrate(derivative, rotating_launch(), TIMES, method,
                            substeps)
    return np.max(np.abs(integration.states[:, :3]
                         - exact_rotating_states(TIMES)[:, :3]))


def test_rk4_is_fourth_order():
    ratio = maximum_error('rk4', 4) / maximum_error('rk4', 8)
    assert 14.0 <= ratio <= 18.0


def test_euler_is_first_order():
    ratio = maximum_error('euler', 4) / maximum_error('euler', 8)
    assert 1.8 <= ratio <= 2.2


def test_dop853_reaches_its_tolerance():
    derivative = rotating_derivative(NoForce(), FRAME)
    integration = integrate(derivative, rotating_launch(), TIMES, 'dop853',
                            rtol=1e-11, atol=1e-13)
    assert np.allclose(integration.states, exact_rotating_states(TIMES),
                       atol=1e-9, rtol=0.0)


def test_an_unknown_method_and_a_bad_substep_count_are_refused():
    with pytest.raises(ValueError, match='euler, rk4, dop853'):
        integrate(lambda t, s: s, np.zeros(6), TIMES, 'leapfrog')
    with pytest.raises(ValueError, match='substeps'):
        integrate(lambda t, s: s, np.zeros(6), TIMES, 'rk4', substeps=0)


def test_evaluate_at_and_between_the_samples():
    derivative = inertial_derivative(NoForce())
    state0 = np.concatenate((POSITION0, VELOCITY0))
    for method in ('rk4', 'euler', 'dop853'):
        integration = integrate(derivative, state0, TIMES, method, 4)
        for index in (0, 7, 20):
            assert np.allclose(integration.evaluate(TIMES[index]),
                               integration.states[index], atol=1e-13)
        between = 0.5 * (TIMES[3] + TIMES[4])
        exact = np.concatenate((POSITION0 + between * VELOCITY0, VELOCITY0))
        # A line is integrated exactly by every scheme.
        assert np.allclose(integration.evaluate(between), exact, atol=1e-12)


def test_evaluate_between_samples_has_the_schemes_order():
    derivative = rotating_derivative(NoForce(), FRAME)
    coarse = integrate(derivative, rotating_launch(), TIMES, 'rk4', 4)
    between = 0.5 * (TIMES[9] + TIMES[10])
    exact = exact_rotating_states(np.array([between]))[0]
    error = np.max(np.abs(coarse.evaluate(between) - exact))
    assert error < 1e-6
    assert error < 2.0 * maximum_error('rk4', 4) + 1e-12
