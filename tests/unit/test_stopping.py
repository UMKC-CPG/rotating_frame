"""Verifies pseudocode 4.6 for `motion/stopping.py`: the rules'
values, exact landing and leaving events, the flagged last sample,
and a launch from the ground that takes off first."""

import numpy as np
import pytest

from rotating_frame.core.frame import Frame
from rotating_frame.motion.closed_forms import line, parabola
from rotating_frame.motion.stopping import (DurationRule, LandsRule,
                                            LeavesRule, apply_event,
                                            locate_event, make_rule)

Z_HAT = np.array([0.0, 0.0, 1.0])
FRAME = Frame(Z_HAT, 1.0)
ORIGIN = np.zeros(3)


def closed_form_evaluator(form, *arguments):
    def evaluate(time):
        position, velocity = form(*arguments, np.array([time]))
        return np.concatenate((position[0], velocity[0]))
    return evaluate


def test_the_rules_values():
    lands = LandsRule(ORIGIN, Z_HAT)
    assert lands.value(np.array([0.3, 0.2, 0.7])) == pytest.approx(0.7)
    assert np.allclose(lands.value(np.array([[0, 0, 1.0], [0, 0, -2.0]])),
                       [1.0, -2.0])
    leaves = LeavesRule(ORIGIN, Z_HAT)
    assert leaves.value(np.array([0.6, 0.8, 5.0])) == pytest.approx(0.0)
    assert leaves.value(np.array([0.3, 0.0, 0.0])) == pytest.approx(0.7)
    assert DurationRule().value(np.array([1.0, 2.0, 3.0])) == np.inf
    assert np.all(np.isinf(DurationRule().value(np.zeros((4, 3)))))
    assert isinstance(make_rule('lands', ORIGIN, Z_HAT, Z_HAT), LandsRule)
    with pytest.raises(ValueError, match='run.stop'):
        make_rule('explodes', ORIGIN, Z_HAT, Z_HAT)


def test_a_parabola_lands_at_root_two():
    gravity = np.array([0.0, 0.0, -1.0])
    position0 = np.array([0.0, 0.0, 1.0])
    velocity0 = np.zeros(3)
    times = np.linspace(0.0, 3.0, 31)
    positions, velocities = parabola(position0, velocity0, gravity, times)
    rule = LandsRule(ORIGIN, Z_HAT)
    event = locate_event(rule, FRAME, times, positions,
                         closed_form_evaluator(parabola, position0,
                                               velocity0, gravity))
    assert event.kind == 'lands'
    assert event.time == pytest.approx(np.sqrt(2.0), abs=1e-12)
    position_rot, _ = FRAME.to_rotating(event.time, event.position_in,
                                        event.velocity_in)
    assert abs(rule.value(position_rot)) < 1e-12
    kept_times, kept_positions, _, flag = apply_event(times, positions,
                                                      velocities, event)
    assert len(kept_times) == event.index + 1
    assert kept_times[-1] == event.time
    assert np.all(kept_times[:-1] < event.time)
    assert flag[-1] and not np.any(flag[:-1])
    assert np.allclose(kept_positions[-1], event.position_in)


def test_a_line_leaves_the_unit_disc_at_time_one():
    position0 = ORIGIN
    velocity0 = np.array([1.0, 0.0, 0.0])
    times = np.linspace(0.0, 2.0, 9)
    positions, _ = line(position0, velocity0, times)
    event = locate_event(LeavesRule(ORIGIN, Z_HAT), FRAME, times, positions,
                         closed_form_evaluator(line, position0, velocity0))
    assert event.time == pytest.approx(1.0, abs=1e-12)
    assert event.kind == 'leaves'


def test_a_launch_from_the_ground_takes_off_first():
    gravity = np.array([0.0, 0.0, -1.0])
    velocity0 = np.array([0.0, 0.0, 1.0])
    times = np.linspace(0.0, 3.0, 31)
    positions, _ = parabola(ORIGIN, velocity0, gravity, times)
    event = locate_event(LandsRule(ORIGIN, Z_HAT), FRAME, times, positions,
                         closed_form_evaluator(parabola, ORIGIN, velocity0,
                                               gravity))
    assert event.time == pytest.approx(2.0, abs=1e-12)


def test_no_event_when_the_rule_never_fires():
    times = np.linspace(0.0, 1.0, 5)
    positions, _ = line(np.array([0.0, 0.0, 1.0]), np.zeros(3), times)
    assert locate_event(LandsRule(ORIGIN, Z_HAT), FRAME, times, positions,
                        lambda t: np.zeros(6)) is None
