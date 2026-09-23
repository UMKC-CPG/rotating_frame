"""The two equations of motion as derivative functions for the
integrators (pseudocode 4.2; design 4.4 and 6.1).

Each factory returns a function of a scalar time and a six-state,
position then velocity, that the integrators step. The inertial
equation is Newton's law with the field's force; the rotating-frame
equation adds the three pseudo-force terms of `pseudoforces/` at the
current rotating state, which is the equation the check of design 6
integrates to be compared with the exact transform.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np

from rotating_frame.pseudoforces import terms as pseudo_terms


def inertial_derivative(field):
    """`d/dt (r, v) = (v, f_in(t, r, v))` in inertial components."""
    def derivative(time, state):
        position, velocity = state[:3], state[3:]
        return np.concatenate((velocity,
                               field.acceleration(time, position,
                                                  velocity)))
    return derivative


def rotating_derivative(field, frame):
    """Equation (2.1): the true force in rotating components plus the
    centrifugal, Coriolis, and Euler terms, at the current state."""
    def derivative(time, state_rot):
        position_rot, velocity_rot = state_rot[:3], state_rot[3:]
        true_force = field.acceleration_rotating(frame, time, position_rot,
                                                 velocity_rot)
        centrifugal, coriolis, euler = pseudo_terms(frame, time,
                                                    position_rot,
                                                    velocity_rot)
        return np.concatenate((velocity_rot,
                               true_force + centrifugal + coriolis + euler))
    return derivative
