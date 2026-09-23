"""The rotating frame, and the transform between its description of a
motion and the inertial one (pseudocode 1; design 1).

A rotating frame here is three things: an origin `O` on the axis,
shared with the inertial frame and never stored because every
position is measured from it; a unit axis `n_hat`, the same vector in
both frames; and a signed rate `Omega`, positive for counterclockwise
rotation seen from the tip of the axis. From these the `Frame` answers
four questions, and nothing else in the package computes them: the
angle turned since `t = 0`, the angular velocity, its rate of change
(zero in this version), and the rotation matrix `R(t)`.

The transform is exact and is applied sample by sample; nothing is
integrated here. With `R(t)` the right-handed rotation by `Omega t`
about `n_hat`,

##    r_in  = R(t) r_rot
##    v_rot = R(t)^T (v_in - Omega x r_in)

carry a position and a velocity from the rotating description to the
inertial one and back. The second line is the velocity a rotating
observer measures: the inertial velocity less the velocity of the
point of the frame the particle is passing through. Because the axis
is fixed, the angular velocity has the same components in both
frames, which is why the pseudo-force formulas elsewhere carry no
subscript on it (design 1.1).

The angle is computed from the time at every call and never
accumulated, so nothing drifts and reverse scrubbing reads the same
values (design 1.2). Every method that takes a time accepts a scalar
or an array of shape (N,), with the vector arguments of shape (3,) or
(N, 3), and returns the same leading shape.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
rotation follows Rodrigues' formula and the transform Goldstein,
Poole, and Safko, *Classical Mechanics*, 3rd ed., sections 4.9 and
4.10; see dev/design/01-frame-and-transform.md.
"""

import numpy as np

IDENTITY = np.eye(3)


def cross_matrix(vector):
    """The matrix `[v]_x` such that `cross_matrix(v) @ u` is the cross
    product `v x u`, for a vector of shape (3,)."""
    vector_x, vector_y, vector_z = np.asarray(vector, dtype=float)
    return np.array([[0.0, -vector_z, vector_y],
                     [vector_z, 0.0, -vector_x],
                     [-vector_y, vector_x, 0.0]])


def rodrigues(axis, angle):
    """The right-handed rotation by `angle` about the unit vector
    `axis`, in Rodrigues' form (design 1.2):

    ##    R = cos(a) I + sin(a) [n]_x + (1 - cos(a)) n n^T

    `angle` may be a scalar, giving a (3, 3) matrix, or an array of
    shape (N,), giving (N, 3, 3). The rotation is orthogonal with
    determinant one, leaves the axis fixed, and composes by adding
    angles, all of which the tests hold."""
    axis = np.asarray(axis, dtype=float)
    angle = np.asarray(angle, dtype=float)
    cosine = np.cos(angle)[..., np.newaxis, np.newaxis]
    sine = np.sin(angle)[..., np.newaxis, np.newaxis]
    return (cosine * IDENTITY + sine * cross_matrix(axis)
            + (1.0 - cosine) * np.outer(axis, axis))


def _apply(matrices, vectors):
    """`R @ v` over any shared leading axes: (…, 3, 3) with (…, 3)."""
    return np.einsum('...ij,...j->...i', matrices, vectors)


def _apply_transpose(matrices, vectors):
    """`R^T @ v` over any shared leading axes. The index order in the
    einsum is what makes this the transpose; it is the commonest thing
    to get backwards in this subject, so it is named."""
    return np.einsum('...ji,...j->...i', matrices, vectors)


class Frame:
    """A frame rotating at a constant signed rate about a fixed unit
    axis through the common origin (design 1.1).

    `axis` is normalized on construction; a zero or non-finite axis
    is refused, because no rotation is defined about it. `rate` is
    kept as given: the core works in natural units in which it is
    one, but the frame does not assume so, so that a varying rate
    (VISION future direction 2) changes only the bodies of `angle`
    and `angular_acceleration`.
    """

    def __init__(self, axis, rate):
        axis = np.asarray(axis, dtype=float)
        norm = np.linalg.norm(axis)
        if not np.isfinite(norm) or norm == 0.0:
            raise ValueError("the frame's axis must be a nonzero vector")
        self.axis = axis / norm
        self.rate = float(rate)

    # -- The four answers of design 1.1 -------------------------------

    def angle(self, time):
        """The angle the frame has turned since `t = 0`: `Omega t`."""
        return self.rate * np.asarray(time, dtype=float)

    def angular_velocity(self, time):
        """`Omega n_hat`, the same in both frames, broadcast to the
        shape of `time` plus (3,). `time` is accepted and ignored so
        that a varying rate changes this body and nothing that calls
        it."""
        leading_shape = np.shape(np.asarray(time, dtype=float))
        return np.broadcast_to(self.rate * self.axis,
                               leading_shape + (3,)).copy()

    def angular_acceleration(self, time):
        """`dOmega/dt`, zero at constant rate; present so that the
        Euler term exists with a zero coefficient (design 1.4)."""
        leading_shape = np.shape(np.asarray(time, dtype=float))
        return np.zeros(leading_shape + (3,))

    def rotation(self, time):
        """`R(t)`, the rotation by `angle(time)` about the axis."""
        return rodrigues(self.axis, self.angle(time))

    # -- The transforms of design 1.3 ---------------------------------

    def to_rotating(self, time, position_in, velocity_in):
        """Carry an inertial position and velocity into the rotating
        description (equations 1.1 and 1.2): `r_rot = R^T r_in` and
        `v_rot = R^T (v_in - Omega x r_in)`."""
        rotation = self.rotation(time)
        omega = self.angular_velocity(time)
        position_in = np.asarray(position_in, dtype=float)
        velocity_in = np.asarray(velocity_in, dtype=float)
        position_rot = _apply_transpose(rotation, position_in)
        velocity_rot = _apply_transpose(
            rotation, velocity_in - np.cross(omega, position_in))
        return position_rot, velocity_rot

    def to_inertial(self, time, position_rot, velocity_rot):
        """The inverse of `to_rotating`: `r_in = R r_rot` and
        `v_in = R v_rot + Omega x r_in`."""
        rotation = self.rotation(time)
        omega = self.angular_velocity(time)
        position_rot = np.asarray(position_rot, dtype=float)
        velocity_rot = np.asarray(velocity_rot, dtype=float)
        position_in = _apply(rotation, position_rot)
        velocity_in = (_apply(rotation, velocity_rot)
                       + np.cross(omega, position_in))
        return position_in, velocity_in

    def launch_to_inertial(self, position_rot, velocity_rot):
        """A launch given in the rotating frame at `t = 0` (design
        1.5). `R(0)` is the identity, so the position is the same in
        both descriptions and the velocity gains the rim speed
        `Omega x r`. Equal to `to_inertial(0, ...)`; kept under its
        own name because design 7.2 cites it."""
        position_rot = np.asarray(position_rot, dtype=float)
        velocity_rot = np.asarray(velocity_rot, dtype=float)
        rim_velocity = np.cross(self.rate * self.axis, position_rot)
        return position_rot, velocity_rot + rim_velocity

    # -- What the display asks (design 1.6) ---------------------------

    def rotating_triad_in_inertial(self, time):
        """The rotating frame's axes as the inertial observer sees
        them: the columns of `R(t)`."""
        return self.rotation(time)

    def inertial_triad_in_rotating(self, time):
        """The inertial axes as the rotating observer sees them: the
        columns of `R(t)^T`, turning the other way."""
        return np.swapaxes(self.rotation(time), -1, -2)
