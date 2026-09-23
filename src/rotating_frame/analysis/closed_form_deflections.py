"""The first-order deflections against the inertial expectation
(pseudocode 6.4; design 6.5).

The ghost of design 6.2 is the motion under the true force alone,
with nothing of the rotating frame in it. Against that ghost the
pseudo-force effect has two parts. Writing `C(u) = -Omega x (Omega x
u)` for the centrifugal operator, linear in its argument, and
integrating the rotating-frame equation twice with every pseudo-force
evaluated along the ghost, whose position is `r_P + v0 t + f t^2 / 2`
and whose velocity is `v0 + f t`,

##    Delta(t) = C(r_P) t^2/2 + C(v0) t^3/6 + C(f) t^4/24
##               - Omega x (v0 t^2 + f t^3 / 3).

The first line is the centrifugal part, exact along the ghost; the
second is the Coriolis part, the textbook deflection, offered on its
own because its special cases are the classroom formulas (the
dropped stone lands east, a ball thrown straight up lands west, a
horizontal throw deflects to the right and, if eastward, upward) and
because the readouts show the two parts separately. On the Earth the
centrifugal part is the larger by far: it is the difference between
falling along the bare attraction and falling along the plumb line,
which the rider never notices because it is already in their g.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
Coriolis part is Taylor, *Classical Mechanics*, section 9.9.
"""

import numpy as np

# Below this value of rate x duration the first-order formula is
# offered as an overlay (design 6.5).
OVERLAY_LIMIT = 0.1


def overlay_applies(frame, duration):
    """Whether the frame turns little enough during the run for the
    first-order formula to be worth drawing."""
    return abs(frame.rate) * duration < OVERLAY_LIMIT


def centrifugal_operator(frame, vectors):
    """`C(u) = -Omega x (Omega x u)`, over any leading axes."""
    omega = frame.angular_velocity(0.0)
    vectors = np.asarray(vectors, dtype=float)
    return -np.cross(omega, np.cross(omega, vectors))


def coriolis_deflection(frame, velocity_rot0, force_rot, times):
    """The Coriolis part: the Coriolis term integrated twice along the
    ghost's velocity `v0 + f t`, rotating components, shape (N, 3).
    `force_rot` is the true force per unit mass in rotating
    components, zero for no force."""
    times = np.asarray(times, dtype=float)
    velocity_rot0 = np.asarray(velocity_rot0, dtype=float)
    force_rot = np.asarray(force_rot, dtype=float)
    omega = frame.angular_velocity(0.0)
    ghost_displacement = (np.outer(times ** 2, velocity_rot0)
                          + np.outer(times ** 3 / 3.0, force_rot))
    return -np.cross(omega, ghost_displacement)


def first_order_deflection(frame, launch_point_rot, velocity_rot0,
                           force_rot, times):
    """The displacement from the ghost path at `times`, rotating
    components, shape (N, 3): the centrifugal part along the ghost
    plus the Coriolis part (equation 6.4)."""
    times = np.asarray(times, dtype=float)
    centrifugal_part = (
        np.outer(times ** 2 / 2.0,
                 centrifugal_operator(frame, launch_point_rot))
        + np.outer(times ** 3 / 6.0,
                   centrifugal_operator(frame, velocity_rot0))
        + np.outer(times ** 4 / 24.0,
                   centrifugal_operator(frame, force_rot)))
    return centrifugal_part + coriolis_deflection(frame, velocity_rot0,
                                                  force_rot, times)


def first_order_tolerance(frame, duration, earth_ratio):
    """The relative tolerance a test may hold the formula to:
    `Omega t + 2 (Omega^2 R_E / g0) + (Omega t)^2`. The first term is
    the Coriolis term acting on the centrifugal velocity, the second
    the effective-gravity and plumb-line corrections on the Earth,
    the third the second-order terms of the expansion. `earth_ratio`
    is `Omega^2 R_E / g0` on the Earth and zero on a platform."""
    turned = abs(frame.rate) * duration
    return turned + 2.0 * earth_ratio + turned ** 2
