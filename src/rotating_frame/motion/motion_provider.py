"""The motion provider: a launch, a field, a frame, and a duration
become inertial samples (pseudocode 4.5; design 4.1; ARCHITECTURE
6.2).

The provider takes the closed form whenever the field declares one
and integrates otherwise; a run may force either, and forcing the
numerical route on a field with a closed form is how a student sees
an integrator's error against an exact answer. Every consumer sees
only the samples, and never which route produced them (VISION P10).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass

import numpy as np

from rotating_frame.motion.closed_forms import sample_closed_form
from rotating_frame.motion.equations_of_motion import inertial_derivative
from rotating_frame.motion.integrators import integrate
from rotating_frame.motion.stopping import apply_event, locate_event

METHODS = ('auto', 'closed_form', 'numerical')


@dataclass(frozen=True)
class Trajectory:
    """The inertial samples of one particle: uniform in time up to a
    stop event, whose exact state is then the flagged last sample."""

    times: np.ndarray
    positions_in: np.ndarray
    velocities_in: np.ndarray
    stop: object
    is_event_sample: np.ndarray


def provide(launch, field, frame, duration, samples, rule, method='auto',
            integrator='rk4', substeps=4, rtol=1e-10, atol=1e-12):
    """Sample the motion from `launch`, an inertial (position,
    velocity) at time zero, under `field` in `frame`, at `samples`
    uniform times over `duration`, cut short by `rule` if it fires."""
    if method not in METHODS:
        raise ValueError(f'run.method: {method!r} is not a method; one '
                         f'of {", ".join(METHODS)}')
    position0 = np.asarray(launch[0], dtype=float)
    velocity0 = np.asarray(launch[1], dtype=float)
    times = np.linspace(0.0, duration, samples)
    if method == 'closed_form' and field.closed_form is None:
        raise ValueError("this field has no closed form; use method = "
                         "'numerical' or 'auto'")
    use_closed = (method == 'closed_form'
                  or (method == 'auto' and field.closed_form is not None))
    if use_closed:
        positions, velocities = sample_closed_form(
            field.closed_form, field, frame, position0, velocity0, times)

        def evaluate(time):
            position, velocity = sample_closed_form(
                field.closed_form, field, frame, position0, velocity0,
                np.array([time]))
            return np.concatenate((position[0], velocity[0]))
    else:
        integration = integrate(inertial_derivative(field),
                                np.concatenate((position0, velocity0)),
                                times, integrator, substeps, rtol, atol)
        positions = integration.states[:, :3]
        velocities = integration.states[:, 3:]
        evaluate = integration.evaluate
    event = locate_event(rule, frame, times, positions, evaluate)
    if event is None:
        return Trajectory(times=times, positions_in=positions,
                          velocities_in=velocities, stop=None,
                          is_event_sample=np.zeros(samples, dtype=bool))
    times, positions, velocities, flag = apply_event(times, positions,
                                                     velocities, event)
    return Trajectory(times=times, positions_in=positions,
                      velocities_in=velocities, stop=event,
                      is_event_sample=flag)
