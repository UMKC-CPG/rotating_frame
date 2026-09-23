"""The determinism guarantee, ARCHITECTURE 8.6(4): two builds of one
run file are equal bit for bit, and reading the store in any order
leaves it unchanged."""

import hashlib
from pathlib import Path

import numpy as np

from rotating_frame.run import build_store, load_rc, load_run_file

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])


def checksum(store):
    digest = hashlib.sha256()
    for array in store._arrays():
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def test_two_builds_are_equal_bit_for_bit():
    spec = load_run_file(EXAMPLES / 'turntable.toml', ['run.samples=120'],
                         RC)
    first, second = build_store(spec, RC), build_store(spec, RC)
    assert checksum(first) == checksum(second)
    assert np.array_equal(first.positions_rot, second.positions_rot,
                          equal_nan=True)


def test_reading_in_a_scrambled_order_changes_nothing():
    spec = load_run_file(EXAMPLES / 'turntable.toml', ['run.samples=120'],
                         RC)
    store = build_store(spec, RC)
    before = checksum(store)
    random = np.random.default_rng(1)
    for _ in range(200):
        particle = int(random.integers(store.n_particles))
        sample = int(random.integers(store.n_samples))
        store.state_at(particle, sample)
        store.terms_at(particle, sample)
        store.error_at(particle, sample)
        store.conserved_at(particle, sample)
        store.time_at(particle, sample)
        store.stop_of(particle)
    assert checksum(store) == before
