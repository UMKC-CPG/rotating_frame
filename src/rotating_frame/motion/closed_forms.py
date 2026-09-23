"""The exact motions of the first version's fields, sampled at any
times (pseudocode 4.1; design 4.2 and 4.3).

In natural units per unit mass, with `r0`, `v0` the launch and `g`
the field's vector: the line, the parabola, and the rotating
parabola, which is the motion under a gravity vector that turns with
the frame. Splitting that vector into its part along the axis, which
the rotation leaves alone, and its part across it, which turns, and
integrating twice gives

##    r(t) = r0 + v0 t + (1/2) g_par t^2
##           + ((1 - cos th) / W^2) g_perp + ((th - sin th) / W^2) n x g_perp

with `th = W t`. The two small-angle coefficients are the point: for
a five-second drop on the Earth `th` is about 3.6e-4 and `th - sin th`
computed as a difference keeps seven of its sixteen digits, so
`1 - cos th` is evaluated as `2 sin^2(th/2)`, which is exact, and
`th - sin th` by its series below 0.1. That protects the very
quantity the tool exists to show, the eastward deflection, which
lives in the cubic term.

Every function evaluates each sample directly from its own time;
nothing is stepped and nothing accumulates, and the times need not
be uniform, which is what lets the stopping search evaluate a form
at an arbitrary time.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np

CLOSED_FORM_NAMES = ('line', 'parabola', 'rotating_parabola')
SERIES_BELOW = 0.1        # theta below which the series is used


def one_minus_cos(theta):
    """`1 - cos(theta)` without cancellation: `2 sin^2(theta/2)`."""
    return 2.0 * np.sin(np.asarray(theta, dtype=float) / 2.0) ** 2


def theta_minus_sin(theta):
    """`theta - sin(theta)` without cancellation: the Taylor series
    through the ninth power below `SERIES_BELOW`, where the next term
    is below 1e-16 relative, and the direct difference above."""
    theta = np.asarray(theta, dtype=float)
    theta_squared = theta ** 2
    series = theta ** 3 / 6.0 * (
        1.0 - theta_squared / 20.0 * (
            1.0 - theta_squared / 42.0 * (1.0 - theta_squared / 72.0)))
    return np.where(np.abs(theta) < SERIES_BELOW, series,
                    theta - np.sin(theta))


def line(position0, velocity0, times):
    """No force: `r = r0 + v0 t`, `v = v0` (equation 4.2)."""
    times = np.asarray(times, dtype=float)
    positions = position0 + np.outer(times, velocity0)
    velocities = np.broadcast_to(velocity0, positions.shape).copy()
    return positions, velocities


def parabola(position0, velocity0, gravity, times):
    """A constant field: `r = r0 + v0 t + g t^2 / 2` (equation 4.3)."""
    times = np.asarray(times, dtype=float)
    positions = (position0 + np.outer(times, velocity0)
                 + 0.5 * np.outer(times ** 2, gravity))
    velocities = velocity0 + np.outer(times, gravity)
    return positions, velocities


def rotating_parabola(position0, velocity0, gravity_rot, frame, times):
    """A field constant in rotating components, turning at the
    frame's rate in inertial ones (equation 4.4)."""
    times = np.asarray(times, dtype=float)
    axis = frame.axis
    rate = frame.rate
    gravity_parallel = np.dot(gravity_rot, axis) * axis
    gravity_perpendicular = gravity_rot - gravity_parallel
    axis_cross_gravity = np.cross(axis, gravity_perpendicular)
    theta = frame.angle(times)
    coefficient_cos = one_minus_cos(theta) / rate ** 2
    coefficient_sin = theta_minus_sin(theta) / rate ** 2
    positions = (position0 + np.outer(times, velocity0)
                 + 0.5 * np.outer(times ** 2, gravity_parallel)
                 + np.outer(coefficient_cos, gravity_perpendicular)
                 + np.outer(coefficient_sin, axis_cross_gravity))
    velocities = (velocity0 + np.outer(times, gravity_parallel)
                  + np.outer(np.sin(theta) / rate, gravity_perpendicular)
                  + np.outer(one_minus_cos(theta) / rate,
                             axis_cross_gravity))
    return positions, velocities


def sample_closed_form(name, field, frame, position0, velocity0, times):
    """Dispatch on the field's declared closed form. The seam with
    the fields (pseudocode 4, preamble): the parabola reads
    `field.gravity_in` and the rotating parabola `field.gravity_rot`,
    the attributes the two uniform fields hold. An unknown name is a
    programming error, never a run-file one."""
    position0 = np.asarray(position0, dtype=float)
    velocity0 = np.asarray(velocity0, dtype=float)
    if name == 'line':
        return line(position0, velocity0, times)
    if name == 'parabola':
        return parabola(position0, velocity0, field.gravity_in, times)
    if name == 'rotating_parabola':
        return rotating_parabola(position0, velocity0, field.gravity_rot,
                                 frame, times)
    raise KeyError(f'no closed form named {name!r}')
