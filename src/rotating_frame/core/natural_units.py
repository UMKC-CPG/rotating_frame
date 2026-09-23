"""The natural units of a run, and the way in and out of them
(pseudocode 2.1; design 2.1 to 2.3).

The core works in units built from the frame's rotation: time in
units of `1/Omega`, length in a scale `L` the run names, so that a
speed is in units of `Omega L` and an acceleration in `Omega^2 L`.
In these units the frame's rate is one and the rotating-frame
equation per unit mass has every coefficient equal to one, which is
what makes a turntable and the Earth the same computation (VISION
P11). `Omega` here is the run's rate after the exaggeration factor
(design 2.6), so the exaggerated run is simply a run with another
rate, and the readouts state the factor.

Mass is not a scale the motion depends on (design 2.2): it is kept
only so that a readout can be shown in newtons when the run file
gives one.

This module imports NumPy and nothing else, and knows nothing about
runs, presets, or pint: `run/` resolves a run file to SI numbers and
calls in here.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later); see
dev/design/02-natural-units-and-presets.md.
"""

from dataclasses import dataclass, field

import numpy as np

KINDS = ('time', 'length', 'speed', 'acceleration', 'angle', 'mass',
         'rate')


@dataclass(frozen=True)
class Scales:
    """The scale factors of one run: `rate` (rad/s, after the
    exaggeration), `length` (m), `mass` (kg or None), and the
    exaggeration itself, kept for the readouts. The derived units,
    `time = 1/rate`, `speed = rate * length`, and `acceleration =
    rate^2 * length`, are computed once."""

    rate: float
    length: float
    mass: float | None
    exaggeration: float
    time: float = field(init=False)
    speed: float = field(init=False)
    acceleration: float = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'time', 1.0 / self.rate)
        object.__setattr__(self, 'speed', self.rate * self.length)
        object.__setattr__(self, 'acceleration',
                           self.rate ** 2 * self.length)


def make_scales(rate_si, length_si, mass_si=None, exaggeration=1.0):
    """Build the `Scales` of a run from SI values, applying the
    exaggeration to the rate. Refuses a zero rate, a non-positive
    length, or a non-positive exaggeration, naming which."""
    if rate_si == 0.0:
        raise ValueError('frame.rate: the rate must not be zero')
    if length_si <= 0.0:
        raise ValueError('frame.length_scale: the length scale must be '
                         'positive')
    if exaggeration <= 0.0:
        raise ValueError('frame.exaggeration: the factor must be '
                         'positive')
    return Scales(rate=exaggeration * rate_si, length=length_si,
                  mass=mass_si, exaggeration=exaggeration)


def factor(scales, kind):
    """The SI value of one natural unit of `kind`."""
    if kind == 'time':
        return scales.time
    if kind == 'length':
        return scales.length
    if kind == 'speed':
        return scales.speed
    if kind == 'acceleration':
        return scales.acceleration
    if kind == 'rate':
        return scales.rate
    if kind == 'angle':
        return 1.0
    if kind == 'mass':
        if scales.mass is None:
            raise ValueError('no mass was given for this run')
        return scales.mass
    raise ValueError(f'unknown kind {kind!r}; one of {", ".join(KINDS)}')


def to_natural(scales, value_si, kind):
    """An SI value, or an array of them, in the run's natural units."""
    return np.asarray(value_si, dtype=float) / factor(scales, kind)


def to_real(scales, value_natural, kind):
    """A natural-unit value, or an array of them, back in SI."""
    return np.asarray(value_natural, dtype=float) * factor(scales, kind)


def speed_ratio(scales, speed_si):
    """The speed ratio of a launch, `epsilon = v0 / (Omega L)`: how
    fast the particle is compared with the frame at the scale `L`
    (design 2.3). Large means the frame barely turns during the
    motion; of order one means the spiral is the whole picture."""
    return speed_si / scales.speed
