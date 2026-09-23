"""When a run ends early, and the exact event (pseudocode 4.4; design
4.5).

A stopping rule is a scalar function of the rotating-frame position
that is positive before the event and zero at it: the height above
the ground for "lands", the distance to the rim for "leaves", and
infinity for a run that ends only by its duration. The provider finds
the first sample at which the rule holds, then locates the crossing
between the bracketing samples by Brent's method on the rule's
function evaluated on the exact motion (or the integrator's dense
output), so that a landing offset is an exact number and not one
that depends on the sample count. The event state becomes the last
stored sample, flagged, and samples past it are dropped.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

RULE_NAMES = ('duration', 'lands', 'leaves')
CROSSING_TOLERANCE = 1e-12


class StoppingRule:
    """The contract: `value(position_rot)` is positive before the
    event, zero at it, and negative after, for one position of shape
    (3,) or many of shape (..., 3)."""

    name = 'duration'

    def value(self, position_rot):
        raise NotImplementedError


class DurationRule(StoppingRule):
    """Never fires: the run ends at its duration."""

    name = 'duration'

    def value(self, position_rot):
        leading = np.shape(np.asarray(position_rot, dtype=float))[:-1]
        return np.full(leading, np.inf) if leading else np.inf


class LandsRule(StoppingRule):
    """Fires when the height above the ground, the displacement from
    the launch point along the local up, reaches zero."""

    name = 'lands'

    def __init__(self, launch_point_rot, up):
        self.launch_point_rot = np.asarray(launch_point_rot, dtype=float)
        self.up = np.asarray(up, dtype=float)

    def value(self, position_rot):
        displacement = np.asarray(position_rot, dtype=float) \
            - self.launch_point_rot
        return displacement @ self.up


class LeavesRule(StoppingRule):
    """Fires when the horizontal distance from the launch point, which
    is the disc's center, reaches the disc's radius (one, in natural
    units, when the length scale is the radius)."""

    name = 'leaves'

    def __init__(self, launch_point_rot, axis, radius=1.0):
        self.launch_point_rot = np.asarray(launch_point_rot, dtype=float)
        self.axis = np.asarray(axis, dtype=float)
        self.radius = float(radius)

    def value(self, position_rot):
        displacement = np.asarray(position_rot, dtype=float) \
            - self.launch_point_rot
        axial = (displacement @ self.axis)[..., np.newaxis] * self.axis
        horizontal = displacement - axial
        return self.radius - np.linalg.norm(horizontal, axis=-1)


def make_rule(name, launch_point_rot, up, axis):
    """The rule called `name`, or a ValueError naming the three."""
    if name == 'duration':
        return DurationRule()
    if name == 'lands':
        return LandsRule(launch_point_rot, up)
    if name == 'leaves':
        return LeavesRule(launch_point_rot, axis)
    raise ValueError(f'run.stop: {name!r} is not a rule; one of '
                     f'{", ".join(RULE_NAMES)}')


@dataclass(frozen=True)
class StopEvent:
    """The first sample index at or past which the rule held, the
    exact time of the crossing, and the inertial state there."""

    index: int
    time: float
    position_in: np.ndarray
    velocity_in: np.ndarray
    kind: str


def locate_event(rule, frame, times, positions_in, evaluate):
    """Find the rule's first crossing, or None if it never fires.

    `evaluate(time)` returns the inertial six-state at `time`, from a
    closed form or an integrator's dense output. The search begins
    after the first sample, and only once the rule has been positive
    at some sample before the crossing, so that a launch from the
    ground with an upward velocity takes off before it can land."""
    times = np.asarray(times, dtype=float)
    positions_rot, _ = frame.to_rotating(times, positions_in,
                                         np.zeros_like(positions_in))
    values = np.asarray(rule.value(positions_rot), dtype=float)
    positive_before = False
    bracket_start = None
    crossing_index = None
    for index in range(len(values)):
        if values[index] > 0.0:
            positive_before = True
            bracket_start = index
        elif positive_before and index >= 1:
            crossing_index = index
            break
    if crossing_index is None:
        return None

    def crossing(time):
        state = evaluate(time)
        position_rot, _ = frame.to_rotating(time, state[:3], state[3:])
        return float(rule.value(position_rot))

    stop_time = brentq(crossing, times[bracket_start],
                       times[crossing_index], xtol=CROSSING_TOLERANCE)
    state = evaluate(stop_time)
    return StopEvent(index=crossing_index, time=float(stop_time),
                     position_in=state[:3], velocity_in=state[3:],
                     kind=rule.name)


def apply_event(times, positions, velocities, event):
    """Keep the samples before the event's index, append the event
    state as the last sample, flag it, and drop the rest."""
    keep = event.index
    times = np.concatenate((times[:keep], [event.time]))
    positions = np.concatenate((positions[:keep], [event.position_in]))
    velocities = np.concatenate((velocities[:keep], [event.velocity_in]))
    is_event_sample = np.zeros(keep + 1, dtype=bool)
    is_event_sample[-1] = True
    return times, positions, velocities, is_event_sample
