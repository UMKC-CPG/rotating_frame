"""The ring: shorthand for many launches at once (pseudocode 7.2 and
7.3; design 7.3).

Member `i` sits at azimuth `phase + 2 pi i / count` on a circle of
the given radius about a target point, in the horizontal plane at
the given height, and is launched at one speed toward the target
(inward) or away from it (outward), in the rotating frame. The ring
expands into ordinary launch specs and is then forgotten: nothing
downstream knows the particles came from a ring. The cyclone cartoon
is an inward ring on the turntable with the target at the center.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass

import numpy as np

from rotating_frame.launch.launch_spec import LaunchSpec

SENSE_NAMES = ('inward', 'outward')


@dataclass(frozen=True)
class RingSpec:
    """The seven keys of design 7.3, in natural units."""

    count: int
    radius: float
    speed: float
    target: np.ndarray = None
    sense: str = 'inward'
    phase: float = 0.0
    height: float = 0.0


def expand_ring(ring):
    """The ring's members as launch specs in the rotating frame, with
    component velocities and labels `ring 0`, `ring 1`, and so on.
    Azimuth is from north, clockwise seen from above, as for a
    launch, so member zero at zero phase sits north of the target."""
    target = (np.zeros(3) if ring.target is None
              else np.asarray(ring.target, dtype=float))
    launches = []
    for index in range(ring.count):
        azimuth = ring.phase + 2.0 * np.pi * index / ring.count
        offset = ring.radius * np.array([np.sin(azimuth), np.cos(azimuth),
                                         0.0])
        position = target + offset + np.array([0.0, 0.0, ring.height])
        toward_target = -offset / ring.radius
        if ring.sense == 'outward':
            toward_target = -toward_target
        launches.append(LaunchSpec(position=position,
                                   velocity=ring.speed * toward_target,
                                   frame='rotating',
                                   label=f'ring {index}'))
    return launches


def check_ring(ring, stage_rule):
    """The physical refusals of design 7.4 for a ring, each a
    ValueError naming the run-file key."""
    if ring.count < 1:
        raise ValueError('ring.count: must be at least one')
    if ring.radius <= 0.0:
        raise ValueError('ring.radius: must be positive')
    if ring.speed < 0.0:
        raise ValueError('ring.speed: must not be negative')
    if ring.sense not in SENSE_NAMES:
        raise ValueError(f'ring.sense: {ring.sense!r} is not one of '
                         f'{", ".join(SENSE_NAMES)}')
    if stage_rule == 'lands' and ring.height < 0.0:
        raise ValueError('ring.height: below the ground')
    if stage_rule == 'leaves':
        for launch in expand_ring(ring):
            if np.linalg.norm(launch.position[:2]) >= 1.0:
                raise ValueError('ring: a member would start outside '
                                 'the disc')
