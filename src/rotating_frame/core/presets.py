"""The named frames with real units, and what each fixes about a run
(pseudocode 2.3 and 2.4; design 2.4, 3.4.1, 7.1).

A preset is a set of SI values a run file may select and partly
override: the axis, the rate, the length scale, the force field and
its kind, the stopping rules the stage offers, and the display units.
Three are shipped: a turntable, a merry-go-round, and the Earth at a
latitude. The preset also owns the launch point and the local east,
north, up axes at it, because it is the preset that knows where a
student stands: on the two platforms the local axes are the frame's
own; on the Earth they are built from the plumb line, the bare
attraction plus the centrifugal term at the launch point, so that
"vertical" on screen is what a student would measure (design 3.4.1).
The plumb line is computed at the run's rate, so that an exaggerated
Earth tilts it more, honestly (design 2.6).

Everything here is SI. `run/` scales the results to natural units.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
Earth's constants are the IERS sidereal rate and the IAU 2015 nominal
GM and mean radius; see dev/design/02-natural-units-and-presets.md.
"""

from dataclasses import dataclass

import numpy as np

EARTH_ROTATION_RATE = 7.2921150e-5      # rad/s, sidereal
EARTH_GM = 3.986004e14                  # m^3/s^2
EARTH_RADIUS = 6.371e6                  # m, the mean radius
EARTH_ATTRACTION = EARTH_GM / EARTH_RADIUS ** 2     # g0 = 9.820 m/s^2:
                                        #   the bare attraction, not the
                                        #   measured 9.81, which already
                                        #   holds the centrifugal term
STANDARD_GRAVITY = 9.81                 # m/s^2, the room's

Z_HAT = np.array([0.0, 0.0, 1.0])
DISPLAY_UNITS = {'length': 'm', 'time': 's', 'speed': 'm/s',
                 'acceleration': 'm/s^2', 'angle': 'deg', 'mass': 'kg'}


@dataclass(frozen=True)
class Preset:
    """One named frame and stage, in SI (design 2.4)."""

    name: str
    axis: np.ndarray
    rate_si: float
    length_si: float
    force_kind: str                 # "none" | "uniform"
    force_fixed_in: str | None      # "space" | "frame" | None
    gravity_si: float | None        # magnitude, m/s^2
    radius_si: float | None         # R_E for the Earth
    requires_latitude: bool
    stop_rules: tuple               # the rules the stage offers
    stage: str                      # "disc" | "platform" | "ground"
    display_units: dict


PRESETS = {
    'turntable': Preset(
        name='turntable', axis=Z_HAT,
        rate_si=(33.0 + 1.0 / 3.0) * 2.0 * np.pi / 60.0,    # 33 1/3 rpm
        length_si=0.30, force_kind='none', force_fixed_in=None,
        gravity_si=None, radius_si=None, requires_latitude=False,
        stop_rules=('duration', 'leaves'), stage='disc',
        display_units=DISPLAY_UNITS),
    'merry_go_round': Preset(
        name='merry_go_round', axis=Z_HAT, rate_si=0.50, length_si=2.0,
        force_kind='uniform', force_fixed_in='space',
        gravity_si=STANDARD_GRAVITY, radius_si=None,
        requires_latitude=False, stop_rules=('duration', 'lands'),
        stage='platform', display_units=DISPLAY_UNITS),
    'earth': Preset(
        name='earth', axis=Z_HAT, rate_si=EARTH_ROTATION_RATE,
        length_si=100.0, force_kind='uniform', force_fixed_in='frame',
        gravity_si=EARTH_ATTRACTION, radius_si=EARTH_RADIUS,
        requires_latitude=True, stop_rules=('duration', 'lands'),
        stage='ground', display_units=DISPLAY_UNITS),
}


def preset(name):
    """The preset called `name`, or a ValueError naming the three."""
    if name not in PRESETS:
        raise ValueError(f'frame.preset: no preset {name!r}; one of '
                         f'{", ".join(PRESETS)}')
    return PRESETS[name]


def _radial(latitude):
    """The unit vector from the Earth's center to the launch point,
    which the convention puts in the x-z plane (design 1.8)."""
    return np.array([np.cos(latitude), 0.0, np.sin(latitude)])


def launch_point_si(the_preset, latitude=None):
    """The launch point from the origin, rotating components, SI: on
    the Earth's surface at `latitude` (radians), or the origin itself
    for the two platforms, whose launch point is on the axis."""
    if the_preset.name == 'earth':
        return EARTH_RADIUS * _radial(latitude)
    return np.zeros(3)


def gravity_vector_si(the_preset, latitude=None):
    """The uniform gravity vector at the launch point, rotating
    components, SI, or None for a stage with no force: toward the
    center on the Earth (design 3.4), straight down on a platform."""
    if the_preset.force_kind == 'none':
        return None
    if the_preset.name == 'earth':
        return -the_preset.gravity_si * _radial(latitude)
    return np.array([0.0, 0.0, -the_preset.gravity_si])


def local_axes_si(the_preset, latitude=None, rate_si=None):
    """The local (east, north, up) triad at the launch point, rotating
    components. On a platform it is the frame's own axes. On the Earth
    `up` is the plumb line, the direction opposite to the bare
    attraction plus the centrifugal term at the launch point evaluated
    at the run's rate `rate_si`; `east` is along the axis crossed with
    the launch point; `north` completes the right-handed triad
    (design 3.4.1). Undefined at the poles, which the schema refuses."""
    if the_preset.name != 'earth':
        return np.eye(3)[0], np.eye(3)[1], np.eye(3)[2]
    if rate_si is None:
        rate_si = the_preset.rate_si
    launch_point = launch_point_si(the_preset, latitude)
    omega = rate_si * the_preset.axis
    centrifugal = -np.cross(omega, np.cross(omega, launch_point))
    effective_gravity = gravity_vector_si(the_preset, latitude) + centrifugal
    up = -effective_gravity / np.linalg.norm(effective_gravity)
    east = np.cross(the_preset.axis, launch_point)
    east = east / np.linalg.norm(east)
    north = np.cross(up, east)
    return east, north, up


def effective_gravity_si(the_preset, latitude=None, rate_si=None):
    """The magnitude of the effective gravity at the launch point: the
    attraction less the centrifugal term's outward part. On a platform
    it is the preset's gravity (or None with no force)."""
    if the_preset.force_kind == 'none':
        return None
    if the_preset.name != 'earth':
        return the_preset.gravity_si
    if rate_si is None:
        rate_si = the_preset.rate_si
    launch_point = launch_point_si(the_preset, latitude)
    omega = rate_si * the_preset.axis
    centrifugal = -np.cross(omega, np.cross(omega, launch_point))
    return np.linalg.norm(gravity_vector_si(the_preset, latitude)
                          + centrifugal)


def plumb_line_tilt(the_preset, latitude, rate_si=None):
    """The angle, in radians, between the plumb line and the radial
    direction at the launch point: about 0.1 degrees at mid-latitudes
    on the real Earth, and larger by the square of the exaggeration
    on a faster one."""
    _, _, up = local_axes_si(the_preset, latitude, rate_si)
    cosine = np.clip(np.dot(up, _radial(latitude)), -1.0, 1.0)
    return float(np.arccos(cosine))
