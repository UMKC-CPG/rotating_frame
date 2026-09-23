"""The results store: the precomputed run, held once and read many
times (pseudocode 8.5; design 8.5; ARCHITECTURE 6.4).

Every array is created writeable, filled once by the driver, then
flagged read-only, which is the mechanical half of the determinism
guarantee: scrubbing touches nothing that computes. A particle that
stopped has its event state at its stop index, with its own time
there, and NaN past it under a false mask. The accessors below are
the only way anything outside `run/` reads the arrays, so that the
display cannot depend on the layout.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass

import numpy as np

# At most thirty-six numbers per particle and sample: four states of
# three, nine terms, the true force, the ghost, the check's six, and the
# overlay's three (design 8.5).
BYTES_PER_SAMPLE = 36 * 8


def estimate_bytes(n_particles, samples):
    """The store's size before it is built."""
    return n_particles * samples * BYTES_PER_SAMPLE


@dataclass(frozen=True)
class StopRecord:
    """Where and when a particle's run ended early."""

    index: int
    time: float
    kind: str


class ResultsStore:
    """The arrays of one run and their read interface."""

    def __init__(self, times, positions_in, velocities_in, positions_rot,
                 velocities_rot, terms, true_force, ghost, check_positions,
                 check_velocities, comparison, conserved, overlay, stops,
                 mask, spec):
        self.times = times
        self.positions_in = positions_in
        self.velocities_in = velocities_in
        self.positions_rot = positions_rot
        self.velocities_rot = velocities_rot
        self.terms = terms
        self.true_force = true_force
        self.ghost = ghost
        self.check_positions = check_positions
        self.check_velocities = check_velocities
        self.comparison = comparison
        self.conserved = conserved
        self.overlay = overlay
        self.stops = stops
        self.mask = mask
        self.spec = spec
        for array in self._arrays():
            array.flags.writeable = False

    def _arrays(self):
        candidates = [self.times, self.positions_in, self.velocities_in,
                      self.positions_rot, self.velocities_rot, self.terms,
                      self.true_force, self.ghost, self.check_positions,
                      self.check_velocities, self.overlay, self.mask]
        return [array for array in candidates if array is not None]

    @property
    def n_particles(self):
        return self.positions_in.shape[0]

    @property
    def n_samples(self):
        return self.times.shape[0]

    def sample_times(self):
        """The uniform grid."""
        return self.times

    def time_at(self, particle, sample):
        """The time of a sample: the grid time, or the event's own
        time when the sample is the particle's stop."""
        stop = self.stops[particle]
        if stop is not None and sample == stop.index:
            return stop.time
        return float(self.times[sample])

    def state_at(self, particle, sample):
        """Both descriptions of the state: inertial position and
        velocity, rotating position and velocity."""
        return (self.positions_in[particle, sample],
                self.velocities_in[particle, sample],
                self.positions_rot[particle, sample],
                self.velocities_rot[particle, sample])

    def terms_at(self, particle, sample):
        """The three pseudo-force vectors (stacked in TERM_NAMES
        order) and the true force, rotating components."""
        return (self.terms[particle, sample],
                self.true_force[particle, sample])

    def error_at(self, particle, sample):
        """The check's position error and its fraction of the effect,
        or None when the check is off."""
        if self.comparison is None or not self.mask[particle, sample]:
            return None
        comparison = self.comparison[particle]
        return (float(comparison.delta[sample]),
                float(comparison.eta[sample]))

    def conserved_at(self, particle, sample):
        """The drifts at a sample and the notes: a dictionary with the
        four drifts (None where not reported) and the sentences; None
        for a sample past the particle's stop."""
        if not self.mask[particle, sample]:
            return None
        record = self.conserved[particle]

        def pick(values):
            return None if values is None else float(values[sample])
        return {'energy_exact': pick(record.energy_exact),
                'energy_check': pick(record.energy_check),
                'jacobi_exact': pick(record.jacobi_exact),
                'jacobi_check': pick(record.jacobi_check),
                'notes': record.notes}

    def stop_of(self, particle):
        return self.stops[particle]

    def valid_samples(self, particle):
        """The number of valid samples of a particle: the grid, or
        the stop index plus one."""
        return int(np.count_nonzero(self.mask[particle]))

    def size_bytes(self):
        return int(sum(array.nbytes for array in self._arrays()))
