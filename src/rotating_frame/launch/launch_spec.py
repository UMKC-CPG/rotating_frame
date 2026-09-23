"""One launch: where a particle starts and how it is thrown, in the
words a student would use, and its conversion to the inertial state
at time zero (pseudocode 7.1 and 7.3; design 7.1, 7.2, 7.4).

A launch is an offset from the launch point in local east, north,
and up, and a velocity as either components or a speed with an
azimuth (from north, clockwise seen from above) and an elevation
(from the horizontal), given in either frame. At time zero the two
frames share every position and the local triad is the same set of
numbers in both, so the only difference between a rotating launch
and an inertial one is the rim velocity `Omega x r`: "I pushed the
puck toward the center" is a rotating launch, "I rolled the ball
onto the turntable from the floor" an inertial one. The conversion
happens once, here, and the resolved state is kept beside the
student's words so the run file reads back as written.

Values arriving here are already in natural units.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass

import numpy as np

FRAME_NAMES = ('rotating', 'inertial')


@dataclass(frozen=True)
class LocalAxes:
    """The east, north, up triad at the launch point, and the launch
    point itself, in rotating components and natural units (built by
    `run/` from the preset, pseudocode 2.4)."""

    east: np.ndarray
    north: np.ndarray
    up: np.ndarray
    launch_point: np.ndarray

    def basis(self):
        """The matrix whose columns are east, north, up: local
        components in, rotating components out."""
        return np.column_stack((self.east, self.north, self.up))


@dataclass(frozen=True)
class LaunchSpec:
    """A launch in the student's words. `velocity` is (E, N, U)
    components or None; `speed` with `azimuth` and `elevation` (both
    in radians) is the other form; both None means at rest."""

    position: np.ndarray
    velocity: object = None
    speed: object = None
    azimuth: float = 0.0
    elevation: float = 0.0
    frame: str = 'rotating'
    mass: object = None
    label: str = ''


@dataclass(frozen=True)
class ResolvedLaunch:
    """The state at time zero in both descriptions, with the spec it
    came from."""

    position_in: np.ndarray
    velocity_in: np.ndarray
    position_rot: np.ndarray
    velocity_rot: np.ndarray
    spec: LaunchSpec


def local_velocity(spec):
    """The launch velocity in local (E, N, U) components, from
    whichever form the spec gives (equation 7.1)."""
    if spec.velocity is not None:
        return np.asarray(spec.velocity, dtype=float)
    if spec.speed is None:
        return np.zeros(3)
    cosine = np.cos(spec.elevation)
    return spec.speed * np.array([cosine * np.sin(spec.azimuth),
                                  cosine * np.cos(spec.azimuth),
                                  np.sin(spec.elevation)])


def resolve_launch(spec, axes, frame):
    """The inertial and rotating states at time zero for `spec` on
    the local axes `axes` in `frame`."""
    basis = axes.basis()
    position_rot = axes.launch_point + basis @ np.asarray(spec.position,
                                                          dtype=float)
    velocity_local = basis @ local_velocity(spec)
    if spec.frame == 'rotating':
        position_in, velocity_in = frame.launch_to_inertial(position_rot,
                                                            velocity_local)
        velocity_rot = velocity_local
    else:
        position_in, velocity_in = position_rot, velocity_local
        _, velocity_rot = frame.to_rotating(0.0, position_in, velocity_in)
    return ResolvedLaunch(position_in=position_in, velocity_in=velocity_in,
                          position_rot=position_rot,
                          velocity_rot=velocity_rot, spec=spec)


def check_launch(spec, stage_rule):
    """The physical refusals of design 7.4, each a ValueError naming
    the run-file key; the schema turns it into the run-file error."""
    if spec.velocity is not None and spec.speed is not None:
        raise ValueError('launch: give velocity or speed, not both')
    if spec.speed is None and spec.elevation != 0.0:
        raise ValueError('launch.elevation: needs launch.speed')
    if not -np.pi / 2 <= spec.elevation <= np.pi / 2:
        raise ValueError('launch.elevation: must lie between -90 and '
                         '90 degrees')
    if spec.speed is not None and spec.speed < 0.0:
        raise ValueError('launch.speed: must not be negative')
    if spec.frame not in FRAME_NAMES:
        raise ValueError(f'launch.frame: {spec.frame!r} is not one of '
                         f'{", ".join(FRAME_NAMES)}')
    position = np.asarray(spec.position, dtype=float)
    height = position[2]
    if stage_rule == 'lands':
        if height < 0.0:
            raise ValueError('launch.position[2]: below the ground')
        if height == 0.0 and local_velocity(spec)[2] <= 0.0:
            raise ValueError('launch.position[2]: on the ground with no '
                             'upward velocity')
    if stage_rule == 'leaves':
        if np.linalg.norm(position[:2]) >= 1.0:
            raise ValueError('launch.position: outside the disc')
