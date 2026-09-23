"""The ghost path: where the rider expected the ball to go
(pseudocode 6.2; design 6.2).

The motion under the true force alone, in rotating components, from
the same rotating-frame launch, with no pseudo-forces at all. The gap
between it and the true rotating-frame path *is* the pseudo-forces,
and the check's error is judged against that gap. For the first
version's fields the true force is constant in rotating components
on every stage, so the ghost is a line or a parabola, a closed form;
for a future field it is integrated like the check. Returned as
displacements from the launch point, at the store's own sample times,
so that it lines up with the true path sample by sample.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np

from rotating_frame.motion.closed_forms import parabola
from rotating_frame.motion.integrators import integrate


def rotating_force_is_constant(field, frame):
    """True when the true force is a constant vector in rotating
    components: no force, frame-fixed gravity, or space-fixed gravity
    whose potential is declared fixed in the rotating frame, which is
    the parallel-axis case."""
    if field.closed_form in ('line', 'rotating_parabola'):
        return True
    return (field.potential is not None
            and 'rotating' in field.potential.frames)


def ghost_derivative(field, frame):
    """The rotating-frame derivative with the pseudo-forces omitted."""
    def derivative(time, state_rot):
        position_rot, velocity_rot = state_rot[:3], state_rot[3:]
        return np.concatenate((velocity_rot,
                               field.acceleration_rotating(
                                   frame, time, position_rot,
                                   velocity_rot)))
    return derivative


def ghost_path(field, frame, launch_in, launch_point_rot, times, settings):
    """The ghost's positions as displacements from the launch point,
    shape (M, 3), at `times`."""
    times = np.asarray(times, dtype=float)
    position_rot0, velocity_rot0 = frame.to_rotating(0.0, *launch_in)
    if rotating_force_is_constant(field, frame):
        force_rot = field.acceleration_rotating(frame, 0.0, position_rot0,
                                                velocity_rot0)
        positions, _ = parabola(position_rot0, velocity_rot0, force_rot,
                                times)              # a line when zero
    else:
        integration = integrate(ghost_derivative(field, frame),
                                np.concatenate((position_rot0,
                                                velocity_rot0)),
                                times, settings.integrator,
                                settings.substeps, settings.rtol,
                                settings.atol)
        positions = integration.states[:, :3]
    return positions - np.asarray(launch_point_rot, dtype=float)
