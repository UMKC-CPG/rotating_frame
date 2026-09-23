"""The three first-version fields and the factory that builds one
from a resolved run (pseudocode 3.2; design 3.2 to 3.4).

No force is the turntable's: the disc's normal force cancels gravity
and the puck stays in its plane. Space-fixed uniform gravity is the
room's on a merry-go-round: a constant vector in inertial components,
which is constant in rotating components too whenever the axis is
parallel to it, as a platform's vertical axis is. Frame-fixed uniform
gravity is the Earth's, by the uniform approximation of design 3.4:
the central field replaced by its value at the launch point, which
rides the frame, so the field is a constant vector in rotating
components and a rotating vector in inertial ones. Its magnitude is
the bare attraction, not the measured g, so that the centrifugal term
the tool draws is not counted twice (ARCHITECTURE 4.2).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np

from rotating_frame.forces.force_interface import (Approximation,
                                                   ForceField, Potential)

# The text every Earth run shows (design 3.4.2), with the run's own
# estimate written in by Approximation.sentence.
UNIFORM_APPROXIMATION_NOTE = (
    "Gravity is uniform here by approximation: the Earth's central "
    "field is replaced by its value at the launch point. Good while "
    "the flight is short compared with sqrt(R_E/g0) ~ 805 s; the "
    "relative error in the deflections for this run is {estimate:.1e}.")


def _broadcast_constant(vector, like):
    """A constant vector broadcast to the leading shape of `like`."""
    like = np.asarray(like, dtype=float)
    return np.broadcast_to(vector, like.shape).copy()


class NoForce(ForceField):
    """Nothing acts: the puck on the frictionless turntable."""

    closed_form = 'line'
    potential = Potential(frames=frozenset({'inertial', 'rotating'}),
                          energy=lambda position: np.zeros(
                              np.shape(position)[:-1]))

    def acceleration(self, time, position_in, velocity_in):
        return np.zeros_like(np.asarray(position_in, dtype=float))


class UniformGravitySpaceFixed(ForceField):
    """The room's gravity: the constant vector `gravity_in` in
    inertial components. Its potential is fixed in the inertial frame
    always, and in the rotating frame too when the axis is parallel
    to the field, in which case the two kinds of uniform gravity
    coincide (design 3.3)."""

    closed_form = 'parabola'

    def __init__(self, gravity_in, frame):
        self.gravity_in = np.asarray(gravity_in, dtype=float)
        parallel = (np.linalg.norm(np.cross(frame.axis, self.gravity_in))
                    < 1e-12 * np.linalg.norm(self.gravity_in))
        frames = {'inertial'} | ({'rotating'} if parallel else set())
        gravity = self.gravity_in
        self.potential = Potential(
            frames=frozenset(frames),
            energy=lambda position: -(np.asarray(position, dtype=float)
                                      @ gravity))

    def acceleration(self, time, position_in, velocity_in):
        return _broadcast_constant(self.gravity_in, position_in)


class UniformGravityFrameFixed(ForceField):
    """The Earth's gravity by the uniform approximation: the constant
    vector `gravity_rot` in rotating components, a rotating vector in
    inertial ones (design 3.4). Holds the frame, because it is defined
    through it, and an `Approximation` for the screen."""

    closed_form = 'rotating_parabola'

    def __init__(self, gravity_rot, frame, approximation):
        self.gravity_rot = np.asarray(gravity_rot, dtype=float)
        self.frame = frame
        self.approximation = approximation
        gravity = self.gravity_rot
        self.potential = Potential(
            frames=frozenset({'rotating'}),
            energy=lambda position_rot: -(np.asarray(position_rot,
                                                     dtype=float)
                                          @ gravity))

    def acceleration(self, time, position_in, velocity_in):
        rotation = self.frame.rotation(time)
        return np.einsum('...ij,j->...i', rotation, self.gravity_rot)


def make_field(kind, fixed_in, gravity_vector, frame, approximation=None):
    """Build the field a resolved run asks for (pseudocode 8.4).
    `gravity_vector` is in inertial components for "space" and in
    rotating components for "frame"; at `t = 0` the two coincide,
    which is why one run-file key serves both."""
    if kind == 'none':
        return NoForce()
    if kind == 'uniform' and fixed_in == 'space':
        return UniformGravitySpaceFixed(gravity_vector, frame)
    if kind == 'uniform' and fixed_in == 'frame':
        return UniformGravityFrameFixed(gravity_vector, frame,
                                        approximation)
    raise ValueError(f'force: kind {kind!r} with fixed_in {fixed_in!r} '
                     'is not a field this version has')
