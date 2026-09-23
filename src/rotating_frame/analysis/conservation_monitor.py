"""Energy and the Jacobi integral, along the exact path and the
check's (pseudocode 6.3; design 6.3).

##    E = |v_in|^2 / 2 + U_in(r_in)                      inertial frame
##    J = |v_rot|^2 / 2 + U_rot(r_rot) - |Omega x r|^2 / 2   rotating frame

Which is conserved is what the field declares: a potential fixed in
the inertial frame conserves E; one fixed in the rotating frame
conserves J, whose last term is the centrifugal potential and which
has no Coriolis contribution because that term does no work. Frame-
fixed gravity conserves J only, and its E is not conserved because
the inertial-frame force depends on time; the monitor says so in
words rather than reporting a drift as if it were an error. Drifts
are scaled by the size of the terms that go into the quantity, so a
large-radius Earth run does not flatter itself.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
Jacobi integral is Goldstein, Poole, and Safko, section 4.10.
"""

from dataclasses import dataclass

import numpy as np

NOT_CONSERVED = {
    'E': ('E is not conserved here: the force in the inertial frame '
          'depends on time (frame-fixed gravity).'),
    'J': ('J is not conserved here: the potential is not fixed in the '
          'rotating frame (space-fixed gravity on a tilted axis).')}


def energy(field, positions_in, velocities_in):
    """`E` per unit mass at every sample, or None when the field
    declares no inertial-frame potential."""
    if field.potential is None or 'inertial' not in field.potential.frames:
        return None
    velocities_in = np.asarray(velocities_in, dtype=float)
    return (0.5 * np.sum(velocities_in ** 2, axis=-1)
            + field.potential.energy(positions_in))


def jacobi(field, frame, positions_rot, velocities_rot):
    """`J` per unit mass at every sample, or None when the field
    declares no rotating-frame potential."""
    if field.potential is None or 'rotating' not in field.potential.frames:
        return None
    positions_rot = np.asarray(positions_rot, dtype=float)
    velocities_rot = np.asarray(velocities_rot, dtype=float)
    omega = frame.angular_velocity(0.0)
    rim = np.cross(omega, positions_rot)
    return (0.5 * np.sum(velocities_rot ** 2, axis=-1)
            + field.potential.energy(positions_rot)
            - 0.5 * np.sum(rim ** 2, axis=-1))


def scale(frame, field, launch_in, positions_rot):
    """The size of the terms that enter E or J for this run (design
    6.3), never zero, so that a drift can be reported as a fraction
    of something meaningful."""
    positions_rot = np.asarray(positions_rot, dtype=float)
    speed0 = np.linalg.norm(launch_in[1])
    gravity = np.linalg.norm(field.acceleration(0.0, *launch_in))
    displacement = positions_rot - positions_rot[0]
    rho_max = np.max(np.linalg.norm(displacement, axis=-1))
    axial = (positions_rot @ frame.axis)[..., np.newaxis] * frame.axis
    r_perp_max = np.max(np.linalg.norm(positions_rot - axial, axis=-1))
    return (0.5 * speed0 ** 2 + gravity * rho_max
            + 0.5 * frame.rate ** 2 * r_perp_max ** 2 + 1e-30)


@dataclass(frozen=True)
class Conserved:
    """Drifts, `(Q_k - Q_0) / scale`, along the exact path and the
    check for each quantity the field conserves (None otherwise), the
    scale, and the sentences for the quantities not reported."""

    energy_exact: object
    energy_check: object
    jacobi_exact: object
    jacobi_check: object
    scale: float
    notes: tuple


def monitor(field, frame, launch_in, times, inertial, rotating, check):
    """The `Conserved` record for one particle. `inertial` and
    `rotating` are (positions, velocities) pairs of the exact path in
    each description; `check` is the check's rotating pair, or None
    when the check is off; `times` carry the check's states out."""
    quantity_scale = scale(frame, field, launch_in, rotating[0])

    def drift(values):
        if values is None:
            return None
        return (values - values[0]) / quantity_scale

    energy_exact = drift(energy(field, *inertial))
    jacobi_exact = drift(jacobi(field, frame, *rotating))
    if check is None:
        energy_check = jacobi_check = None
    else:
        check_inertial = frame.to_inertial(np.asarray(times, dtype=float),
                                           *check)
        energy_check = drift(energy(field, *check_inertial))
        jacobi_check = drift(jacobi(field, frame, *check))
    notes = tuple(NOT_CONSERVED[name] for name, value
                  in (('E', energy_exact), ('J', jacobi_exact))
                  if value is None)
    return Conserved(energy_exact=energy_exact, energy_check=energy_check,
                     jacobi_exact=jacobi_exact, jacobi_check=jacobi_check,
                     scale=quantity_scale, notes=notes)
