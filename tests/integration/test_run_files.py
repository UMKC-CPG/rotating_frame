"""Every packaged example loads, builds, writes back, and reloads to
an equal spec (pseudocode 8.7)."""

from pathlib import Path

import numpy as np
import pytest

from rotating_frame.core.presets import (EARTH_ATTRACTION, EARTH_RADIUS,
                                         EARTH_ROTATION_RATE)
from rotating_frame.run import build_store, load_rc, load_run_file, \
    write_resolved

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])
NAMES = ('turntable', 'merry_go_round', 'earth_drop', 'earth_throw',
         'earth_vertical')


@pytest.mark.parametrize('name', NAMES)
def test_the_example_runs_end_to_end(name, tmp_path):
    spec = load_run_file(EXAMPLES / f'{name}.toml', (), RC)
    store = build_store(spec, RC)
    assert store.n_particles == len(spec.launches)
    assert np.all(store.mask[:, 0])
    target = tmp_path / f'{name}.toml'
    assert write_resolved(spec, target)
    again = load_run_file(target, (), RC)
    assert again.duration == pytest.approx(spec.duration, rel=1e-12)
    for first, second in zip(again.launches, spec.launches):
        assert np.allclose(first.position_in, second.position_in)
        assert np.allclose(first.velocity_in, second.velocity_in)


def test_the_earth_drop_lands_where_the_spike_said():
    spec = load_run_file(EXAMPLES / 'earth_drop.toml', (), RC)
    store = build_store(spec, RC)
    stop = store.stop_of(0)
    displacement = (store.positions_rot[0, stop.index]
                    - spec.axes.launch_point) * spec.scales.length
    landing_time = stop.time * spec.scales.time
    textbook = (EARTH_ATTRACTION * EARTH_ROTATION_RATE * landing_time ** 3
                * np.cos(np.radians(39.0)) / 3.0)
    correction = 1.0 - EARTH_ROTATION_RATE ** 2 * EARTH_RADIUS \
        / EARTH_ATTRACTION
    assert displacement @ spec.axes.east == pytest.approx(
        textbook * correction, rel=1e-5)
    assert displacement @ spec.axes.east == pytest.approx(0.0170, abs=2e-4)
    assert abs(displacement @ spec.axes.up) < 1e-9
