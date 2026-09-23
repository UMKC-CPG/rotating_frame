"""The trails: each particle's path through its stored samples up to
the current one, and the extra paths drawn for the tracked particle
in the rotating view (pseudocode 9.2; design 9.3).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np

TRAIL_ROLES = 12


def trail(store, particle, sample, view):
    """The points of the particle's trail through sample `sample`, in
    this view's description, masked to valid samples, and its palette
    role."""
    valid = store.valid_samples(particle)
    last = min(sample, valid - 1) + 1
    positions = (store.positions_in if view == 'inertial'
                 else store.positions_rot)
    return positions[particle, :last], f'trail_{particle % TRAIL_ROLES}'


def ghost_now(store, spec, particle, sample):
    """Where the ghost, the ball the rider expected, is at `sample`:
    rotating components, past the stop held at the stop."""
    valid = store.valid_samples(particle)
    return spec.axes.launch_point + store.ghost[particle,
                                                min(sample, valid - 1)]


def extra_trails(store, spec, particle, shown):
    """The check's path, the ghost path, and the first-order overlay
    for `particle`, each whole over its valid samples (design 9.3),
    rotating components, as a list of (points, role, style, label)
    for those that the store holds and `shown` names ("check",
    "ghost", "overlay")."""
    valid = store.valid_samples(particle)
    last = valid
    launch_point = spec.axes.launch_point
    extras = []
    if 'check' in shown and store.check_positions is not None:
        extras.append((store.check_positions[particle, :last], 'check',
                       'dashed', 'check'))
    if 'ghost' in shown:
        extras.append((launch_point + store.ghost[particle, :last], 'ghost',
                       'dotted', 'ghost'))
    if 'overlay' in shown and store.overlay is not None:
        extras.append((launch_point + store.ghost[particle, :last]
                       + store.overlay[particle, :last], 'overlay', 'thin',
                       'first order'))
    return [(np.asarray(points), role, style, label)
            for points, role, style, label in extras]
