"""The contract every force field satisfies (pseudocode 3.1; design
3.1; ARCHITECTURE 6.3).

A field answers with the acceleration per unit mass, in natural units
and in inertial components, for a time and an inertial state, and it
declares three capabilities that the rest of the tool asks for by
name: `closed_form`, the name of a motion the provider can sample
exactly; `potential`, the potential energy per unit mass and the
frames in which it is a function of position alone, which is what
decides whether energy or the Jacobi integral is conserved (design
6.3); and `approximation`, a note for the screen and an error
estimate, for a field that stands in for a truer one (design 3.4.2).

One method is concrete here so that no field repeats it:
`acceleration_rotating`, which carries a rotating-frame state out
through the frame, asks the field, and carries the answer back. The
check of design 6 calls it; the field itself never knows.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass
from typing import Callable

import numpy as np

CLOSED_FORM_NAMES = ('line', 'parabola', 'rotating_parabola')


@dataclass(frozen=True)
class Potential:
    """A potential energy per unit mass and the frames in which it is
    a function of position alone. `frames` holds "inertial" and/or
    "rotating"; when both are declared, the vector the energy dots
    with has the same components in both, so either frame's position
    may be passed to `energy`."""

    frames: frozenset
    energy: Callable


@dataclass(frozen=True)
class Approximation:
    """What the screen says about a field that approximates a truer
    one: one sentence, with `{estimate:.1e}` where the number goes,
    and the timescale `t_E` in natural units from which the estimate
    for a run of a given duration follows (design 3.4.2)."""

    note: str
    timescale: float

    def estimate(self, duration_natural):
        """The relative error in the deflections for a run of this
        duration: one half of the duration over the timescale,
        squared (equation 3.2)."""
        return 0.5 * (duration_natural / self.timescale) ** 2

    def sentence(self, duration_natural):
        """The note with the run's own estimate written in."""
        return self.note.format(estimate=self.estimate(duration_natural))


class ForceField:
    """The abstract field. Subclasses set the three capabilities and
    implement `acceleration`, which must accept a scalar time with a
    single state and a time array of shape (N,) with states of shape
    (N, 3), returning the same leading shape."""

    closed_form = None
    potential = None
    approximation = None

    def acceleration(self, time, position_in, velocity_in):
        """The force per unit mass in inertial components."""
        raise NotImplementedError

    def acceleration_rotating(self, frame, time, position_rot,
                              velocity_rot):
        """The same force in rotating components: carry the state out
        (design 1.3), ask, and carry the answer back with the
        transpose of the rotation."""
        position_in, velocity_in = frame.to_inertial(time, position_rot,
                                                     velocity_rot)
        rotation = frame.rotation(time)
        force_in = self.acceleration(time, position_in, velocity_in)
        return np.einsum('...ji,...j->...i', rotation, force_in)
