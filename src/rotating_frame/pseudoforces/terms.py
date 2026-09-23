"""The centrifugal, Coriolis, and Euler terms from the frame and the
rotating-frame state (pseudocode 5.1; design 5.1 and 5.2).

Per unit mass, in natural units, in rotating components:

##    f_cf = - Omega x (Omega x r_rot)      centrifugal, away from the axis
##    f_co = - 2 Omega x v_rot              Coriolis, perpendicular to v
##    f_eu = - (dOmega/dt) x r_rot          Euler, zero at constant rate

The centrifugal term depends on where the particle is and not on how
it moves; the Coriolis term on how it moves and not on where it is,
and it does no work in the rotating frame; the Euler term is carried
with a zero coefficient so that a varying rate turns it on without
touching any caller. Nothing here special-cases the Earth: the
centrifugal term at a surface point comes out of the same cross
product as on the turntable.

Every function broadcasts over any leading axes, so one call serves
a single state, a trajectory, or a whole run of particles.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
terms are Goldstein, Poole, and Safko, *Classical Mechanics*, 3rd
ed., section 4.10.
"""

import numpy as np

# The order of the store's term axis (pseudocode 8.5).
TERM_NAMES = ('centrifugal', 'coriolis', 'euler')


def terms(frame, time, position_rot, velocity_rot):
    """The three terms at the given rotating-frame state, each with
    the shape of `position_rot`. `time` is a scalar or matches the
    sample axis; the frame ignores it at constant rate."""
    position_rot = np.asarray(position_rot, dtype=float)
    velocity_rot = np.asarray(velocity_rot, dtype=float)
    omega = frame.angular_velocity(time)
    omega_dot = frame.angular_acceleration(time)
    centrifugal = -np.cross(omega, np.cross(omega, position_rot))
    coriolis = -2.0 * np.cross(omega, velocity_rot)
    euler = -np.cross(omega_dot, position_rot)
    return centrifugal, coriolis, euler


def stacked(frame, time, position_rot, velocity_rot):
    """The three terms on one axis, second from last, in `TERM_NAMES`
    order: shape (..., 3, 3)."""
    return np.stack(terms(frame, time, position_rot, velocity_rot),
                    axis=-2)


def total(frame, time, position_rot, velocity_rot):
    """The sum of the three, for the rotating-frame equation and for
    the "sum" arrow."""
    centrifugal, coriolis, euler = terms(frame, time, position_rot,
                                         velocity_rot)
    return centrifugal + coriolis + euler
