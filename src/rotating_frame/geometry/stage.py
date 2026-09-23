"""The stage each preset moves over, with markings so that its
rotation can be seen (pseudocode 9.2; design 9.3).

The turntable is a disc with spokes and a rim; the merry-go-round a
platform disc flush with the floor, whose grid continues beyond the
rim; the Earth a square patch of ground through the launch point,
perpendicular to the plumb line, with a grid and a compass rose. A
part that belongs to the rotating frame (disc, platform, ground) is
rotated by `R(t)` in the inertial view; a part that belongs to the
room (the floor) is rotated by `R(t)^T` in the rotating view. Every
point is placed relative to the launch point as that view sees it,
which the caller subtracts.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np

RIM_POINTS = 64
SPOKES = 8
GRID_LINES = 9


def _disc(radius, center, basis):
    """A fan-triangulated disc of `radius` about `center` in the plane
    of the first two columns of `basis`: (points, faces)."""
    angles = np.linspace(0.0, 2.0 * np.pi, RIM_POINTS, endpoint=False)
    rim = (center + np.outer(radius * np.cos(angles), basis[:, 0])
           + np.outer(radius * np.sin(angles), basis[:, 1]))
    points = np.vstack((center, rim))
    faces = [[0, 1 + i, 1 + (i + 1) % RIM_POINTS] for i in range(RIM_POINTS)]
    return points, faces


def _disc_markings(radius, center, basis):
    """Spokes and the rim, as lists of points."""
    angles = np.linspace(0.0, 2.0 * np.pi, RIM_POINTS + 1)
    rim = (center + np.outer(radius * np.cos(angles), basis[:, 0])
           + np.outer(radius * np.sin(angles), basis[:, 1]))
    markings = [('stage_marks', rim)]
    for spoke in np.linspace(0.0, 2.0 * np.pi, SPOKES, endpoint=False):
        tip = (center + radius * np.cos(spoke) * basis[:, 0]
               + radius * np.sin(spoke) * basis[:, 1])
        markings.append(('stage_marks', np.vstack((center, tip))))
    return markings


def _square(side, center, basis):
    """A square of `side` about `center` in the plane of the first two
    columns of `basis`, with a grid: (points, faces, markings)."""
    half = side / 2.0
    corners = np.array([[-half, -half], [half, -half], [half, half],
                        [-half, half]])
    points = center + corners @ basis[:, :2].T
    faces = [[0, 1, 2, 3]]
    markings = []
    for offset in np.linspace(-half, half, GRID_LINES):
        along = np.vstack((center + offset * basis[:, 0] - half * basis[:, 1],
                           center + offset * basis[:, 0]
                           + half * basis[:, 1]))
        across = np.vstack((center + offset * basis[:, 1]
                            - half * basis[:, 0],
                            center + offset * basis[:, 1]
                            + half * basis[:, 0]))
        markings.append(('floor', along))
        markings.append(('floor', across))
    return points, faces, markings


def stage_surface(spec, view, time, extent):
    """The stage's surfaces as a list of dictionaries, each with
    `points`, `faces`, `role`, `markings` (a list of (role, points)),
    and `labels` (a list of (point, text)), all relative to the
    launch point as this view sees it."""
    rotation = spec.frame.rotation(time)
    to_view = rotation if view == 'inertial' else np.eye(3)
    room_to_view = np.eye(3) if view == 'inertial' else rotation.T
    name = spec.preset.name
    origin = np.zeros(3)
    if name == 'turntable':
        points, faces = _disc(1.0, origin, to_view)
        markings = _disc_markings(1.0, origin, to_view)
        return [{'points': points, 'faces': faces, 'role': 'stage',
                 'markings': markings, 'labels': []}]
    if name == 'merry_go_round':
        points, faces = _disc(1.0, origin, to_view)
        markings = _disc_markings(1.0, origin, to_view)
        floor_points, floor_faces, floor_marks = _square(4.0 * extent,
                                                         origin, room_to_view)
        return [{'points': floor_points, 'faces': floor_faces,
                 'role': 'floor', 'markings': floor_marks, 'labels': []},
                {'points': points, 'faces': faces, 'role': 'stage',
                 'markings': markings, 'labels': []}]
    # The Earth: the ground patch through P, perpendicular to up, in
    # the local (east, north) plane, rotated with the frame.
    local = to_view @ spec.axes.basis()
    points, faces, markings = _square(4.0 * extent, origin, local)
    markings = [('stage_marks', line) for _, line in markings]
    reach = 1.5 * extent
    rose = [(origin + reach * local[:, 0], 'E'),
            (origin + reach * local[:, 1], 'N'),
            (origin - reach * local[:, 0], 'W'),
            (origin - reach * local[:, 1], 'S')]
    meridian = np.vstack((origin - 2.0 * extent * local[:, 1],
                          origin + 2.0 * extent * local[:, 1]))
    markings.append(('rotating_axes', meridian))
    return [{'points': points, 'faces': faces, 'role': 'stage',
             'markings': markings, 'labels': rose}]
