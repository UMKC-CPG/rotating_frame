"""Verifies pseudocode 8.7 for `run/results_store.py` and the driver:
shapes, the mask, the event sample's time, read-only arrays, the size
estimate, and sample zero as the launch."""

from pathlib import Path

import numpy as np
import pytest

from rotating_frame.run import (RunFileError, build_store, estimate_bytes,
                                load_rc, load_run_file)
from rotating_frame.run.rc import RcSettings

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])


@pytest.fixture(scope='module')
def merry_go_round():
    spec = load_run_file(EXAMPLES / 'merry_go_round.toml',
                         ['run.samples=200'], RC)
    return spec, build_store(spec, RC)


def test_shapes_and_the_mask(merry_go_round):
    spec, store = merry_go_round
    n_p, n = store.n_particles, store.n_samples
    assert (n_p, n) == (1, 200)
    assert store.positions_in.shape == (1, 200, 3)
    assert store.terms.shape == (1, 200, 3, 3)
    assert store.check_positions.shape == (1, 200, 3)
    assert store.ghost.shape == (1, 200, 3)
    stop = store.stop_of(0)
    assert stop is not None and stop.kind == 'lands'
    assert np.all(store.mask[0, :stop.index + 1])
    assert not np.any(store.mask[0, stop.index + 1:])
    assert np.all(np.isnan(store.positions_in[0, stop.index + 1:]))
    assert store.valid_samples(0) == stop.index + 1


def test_the_event_samples_time(merry_go_round):
    spec, store = merry_go_round
    stop = store.stop_of(0)
    assert store.time_at(0, stop.index) == stop.time
    assert store.time_at(0, stop.index - 1) == store.sample_times()[
        stop.index - 1]
    assert stop.time < store.sample_times()[stop.index]


def test_every_array_is_read_only(merry_go_round):
    _, store = merry_go_round
    with pytest.raises(ValueError):
        store.positions_rot[0, 0, 0] = 1.0
    with pytest.raises(ValueError):
        store.mask[0, 0] = False


def test_sample_zero_is_the_launch(merry_go_round):
    spec, store = merry_go_round
    launch = spec.launches[0]
    position_in, velocity_in, position_rot, velocity_rot = store.state_at(
        0, 0)
    assert np.allclose(position_in, launch.position_in)
    assert np.allclose(velocity_in, launch.velocity_in)
    assert np.allclose(position_rot, launch.position_rot)
    assert np.allclose(velocity_rot, launch.velocity_rot)


def test_the_accessors(merry_go_round):
    _, store = merry_go_round
    terms, true_force = store.terms_at(0, 5)
    assert terms.shape == (3, 3) and true_force.shape == (3,)
    delta, eta = store.error_at(0, 5)
    assert delta >= 0.0 and eta >= 0.0
    conserved = store.conserved_at(0, 5)
    assert conserved['energy_exact'] is not None
    assert conserved['notes'] == ()


def test_size_estimate_and_cap():
    spec = load_run_file(EXAMPLES / 'turntable.toml', (), RC)
    store = build_store(spec, RC)
    assert abs(estimate_bytes(store.n_particles, store.n_samples)
               - store.size_bytes()) < 0.1 * store.size_bytes()
    tiny = RcSettings(**{**RC.__dict__, 'max_store_bytes': 1000})
    with pytest.raises(RunFileError, match='memory'):
        build_store(spec, tiny)
