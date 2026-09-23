"""The check and the comparison (pseudocode 6.1; design 6.1 and 6.2).

The check integrates the rotating-frame equation, the true force
plus the three pseudo-force terms, from the same launch as the exact
motion, and reads nothing from the transform: only the launch, the
field, and the frame. The comparison then measures, sample by
sample, how far the check's trajectory is from the transform's, and
also how large that error is against the pseudo-force *effect*, the
gap between the true rotating-frame path and the ghost path of no
pseudo-forces at all. On the Earth the whole effect is a ten-
thousandth of the length scale, so the error as a fraction of the
scene would say nothing; the error as a fraction of the effect is
what tells a student whether what they see is physics or numerics
(VISION P3).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass

import numpy as np

from rotating_frame.motion.equations_of_motion import rotating_derivative
from rotating_frame.motion.integrators import integrate

# Keeps the error fraction finite at t = 0, where the effect is zero.
DELTA_FLOOR = 1e-9


@dataclass(frozen=True)
class CheckSettings:
    """The check's run-file table: whether it runs, and how."""

    enabled: bool = True
    integrator: str = 'rk4'
    substeps: int = 4
    rtol: float = 1e-10
    atol: float = 1e-12


def run_check(field, frame, launch_in, times, settings):
    """Integrate the rotating-frame equation from the inertial launch
    `launch_in`, recording at `times`; returns the rotating-frame
    positions and velocities, shape (N, 3) each."""
    position_rot0, velocity_rot0 = frame.to_rotating(0.0, *launch_in)
    state0 = np.concatenate((position_rot0, velocity_rot0))
    integration = integrate(rotating_derivative(field, frame), state0,
                            times, settings.integrator, settings.substeps,
                            settings.rtol, settings.atol)
    return integration.states[:, :3], integration.states[:, 3:]


@dataclass(frozen=True)
class Comparison:
    """Per sample: the position and velocity errors of the check, the
    size of the pseudo-force effect, and the error as a fraction of
    it; and the run's maxima."""

    delta: np.ndarray
    delta_velocity: np.ndarray
    effect: np.ndarray
    eta: np.ndarray
    max_delta: float
    max_eta: float


def compare(positions_rot, velocities_rot, check_positions,
            check_velocities, ghost_positions, launch_point_rot):
    """The comparison of the check against the transform, scaled by
    the effect. `ghost_positions` are displacements from the launch
    point (design 6.2), so the transform's positions have the launch
    point subtracted before the effect is measured."""
    delta = np.linalg.norm(check_positions - positions_rot, axis=-1)
    delta_velocity = np.linalg.norm(check_velocities - velocities_rot,
                                    axis=-1)
    effect = np.linalg.norm((positions_rot - launch_point_rot)
                            - ghost_positions, axis=-1)
    eta = delta / np.maximum(effect, DELTA_FLOOR)
    return Comparison(delta=delta, delta_velocity=delta_velocity,
                      effect=effect, eta=eta, max_delta=float(np.max(delta)),
                      max_eta=float(np.max(eta)))
