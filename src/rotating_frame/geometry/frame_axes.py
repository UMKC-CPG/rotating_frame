"""The two triads each view draws: its own frame's axes fixed and the
other frame's axes turning (pseudocode 9.2; design 9.3; design 1.6).

In the inertial view the rotating frame's axes are the columns of
`R(t)`, turning; in the rotating view the inertial axes are the
columns of `R(t)^T`, turning the other way. On the Earth the triads
at the distant center are of no use to a student standing at the
launch point, so the view draws the local east, north, up triad
there instead: fixed in the rotating view, and carried by `R(t)` in
the inertial one, with the axis of rotation shown as a short arrow
tilted by the colatitude.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np

TRIAD_FRACTION = 0.25            # of the scene's extent (design 9.3)


def moving_triad(frame, time, view):
    """The other frame's axes as this view sees them, as columns."""
    if view == 'inertial':
        return frame.rotating_triad_in_inertial(time)
    return frame.inertial_triad_in_rotating(time)


def triads(spec, view, time, extent, origin):
    """The fixed and the moving triad at `origin` (the launch point as
    this view sees it), as a list of (axes, role, labels, is_moving)
    tuples with the axes as columns, scaled to length; and, on the
    Earth, the axis of rotation as a (vector, role, label) tuple."""
    length = TRIAD_FRACTION * extent
    rotation = spec.frame.rotation(time)
    if spec.preset.name == 'earth':
        local = spec.axes.basis()
        fixed = local
        moving = rotation @ local if view == 'inertial' else rotation.T @ local
        own_labels = ('E', 'N', 'U')
        other_labels = ("E'", "N'", "U'")
        axis_arrow = (length * spec.frame.axis, 'rotating_axes', 'Ω')
    else:
        fixed = np.eye(3)
        moving = moving_triad(spec.frame, time, view)
        own_labels = ('x', 'y', 'z')
        other_labels = ("x'", "y'", "z'")
        axis_arrow = None
    own_role = 'inertial_axes' if view == 'inertial' else 'rotating_axes'
    other_role = 'rotating_axes' if view == 'inertial' else 'inertial_axes'
    return ([(length * fixed, own_role, own_labels, False),
             (length * moving, other_role, other_labels, True)],
            axis_arrow)
