"""Verifies pseudocode 4.6 for `motion/motion_provider.py`: the three
methods, the refusal of a closed form where none exists, and the
shape of a trajectory with and without a stop."""

import numpy as np
import pytest

from rotating_frame.core.frame import Frame
from rotating_frame.forces import NoForce, UniformGravitySpaceFixed
from rotating_frame.forces.force_interface import ForceField
from rotating_frame.motion import DurationRule, LandsRule, provide
from rotating_frame.motion.closed_forms import sample_closed_form

Z_HAT = np.array([0.0, 0.0, 1.0])
FRAME = Frame(Z_HAT, 1.0)


class Drag(ForceField):
    """A throwaway field with no closed form: linear drag."""

    def acceleration(self, time, position_in, velocity_in):
        return -0.1 * np.asarray(velocity_in, dtype=float)


def test_auto_takes_the_closed_form_exactly():
    field = UniformGravitySpaceFixed([0.0, 0.0, -1.0], FRAME)
    launch = (np.array([0.0, 0.0, 2.0]), np.array([0.3, 0.0, 0.0]))
    trajectory = provide(launch, field, FRAME, 1.0, 11, DurationRule())
    positions, velocities = sample_closed_form('parabola', field, FRAME,
                                               *launch, trajectory.times)
    assert np.array_equal(trajectory.positions_in, positions)
    assert np.array_equal(trajectory.velocities_in, velocities)
    assert trajectory.stop is None
    assert not np.any(trajectory.is_event_sample)
    assert len(trajectory.times) == 11


def test_numerical_differs_from_the_closed_form_by_a_small_amount():
    field = UniformGravitySpaceFixed([0.0, 0.0, -1.0], FRAME)
    launch = (np.array([0.0, 0.0, 2.0]), np.array([0.3, 0.0, 0.0]))
    exact = provide(launch, field, FRAME, 1.0, 11, DurationRule())
    numerical = provide(launch, field, FRAME, 1.0, 11, DurationRule(),
                        method='numerical', integrator='rk4', substeps=4)
    difference = np.max(np.abs(numerical.positions_in - exact.positions_in))
    assert difference < 1e-12       # a parabola is exact for RK4
    euler = provide(launch, field, FRAME, 1.0, 11, DurationRule(),
                    method='numerical', integrator='euler', substeps=4)
    assert np.max(np.abs(euler.positions_in - exact.positions_in)) > 1e-4


def test_a_field_without_a_closed_form_is_integrated_or_refused():
    launch = (np.zeros(3), np.array([1.0, 0.0, 0.0]))
    trajectory = provide(launch, Drag(), FRAME, 1.0, 6, DurationRule())
    assert trajectory.positions_in[-1, 0] == pytest.approx(
        10.0 * (1.0 - np.exp(-0.1)), rel=1e-8)
    with pytest.raises(ValueError, match='no closed form'):
        provide(launch, Drag(), FRAME, 1.0, 6, DurationRule(),
                method='closed_form')
    with pytest.raises(ValueError, match='run.method'):
        provide(launch, NoForce(), FRAME, 1.0, 6, DurationRule(),
                method='exact')


def test_a_stopped_trajectory_ends_on_its_event():
    field = UniformGravitySpaceFixed([0.0, 0.0, -1.0], FRAME)
    launch = (np.array([0.0, 0.0, 1.0]), np.zeros(3))
    rule = LandsRule(np.zeros(3), Z_HAT)
    trajectory = provide(launch, field, FRAME, 3.0, 31, rule)
    assert trajectory.stop is not None
    assert trajectory.times[-1] == pytest.approx(np.sqrt(2.0), abs=1e-12)
    assert trajectory.is_event_sample[-1]
    lengths = {len(trajectory.times), len(trajectory.positions_in),
               len(trajectory.velocities_in),
               len(trajectory.is_event_sample)}
    assert len(lengths) == 1
    assert np.allclose(np.diff(trajectory.times[:-1]), 0.1)
