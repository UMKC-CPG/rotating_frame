"""The ring's symmetry over a whole run (design 7.5, ARCHITECTURE
8.2): member i is member 0 rotated by its share of a turn, sample by
sample, and every member stops at the same time."""

from pathlib import Path

import numpy as np
import pytest

from rotating_frame.core.frame import rodrigues
from rotating_frame.run import build_store, load_rc, load_run_file

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])


def test_the_turntable_ring_is_symmetric():
    spec = load_run_file(EXAMPLES / 'turntable.toml', (), RC)
    store = build_store(spec, RC)
    members = [index for index, launch in enumerate(spec.launches)
               if launch.spec.label.startswith('ring')]
    assert len(members) == 12
    first = members[0]
    valid = store.valid_samples(first)
    for count, member in enumerate(members):
        rotation = rodrigues(spec.frame.axis, -2.0 * np.pi * count / 12)
        assert store.valid_samples(member) == valid
        expected = store.positions_rot[first, :valid] @ rotation.T
        assert np.allclose(store.positions_rot[member, :valid], expected,
                           atol=1e-12)
        assert store.stop_of(member).time == pytest.approx(
            store.stop_of(first).time, abs=1e-12)
