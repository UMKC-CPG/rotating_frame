"""Verifies pseudocode 9.7 for `geometry/`: the moving triad, the
Earth's local triads, the stage's turning parts, and the trails
stopping at the mask."""

from pathlib import Path

import numpy as np
import pytest

from rotating_frame.geometry import (extra_trails, ghost_now,
                                     moving_triad, stage_surface, trail,
                                     triads)
from rotating_frame.run import build_store, load_rc, load_run_file

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])


@pytest.fixture(scope='module')
def runs():
    result = {}
    for name in ('turntable', 'merry_go_round', 'earth_drop'):
        spec = load_run_file(EXAMPLES / f'{name}.toml',
                             ['run.samples=60'], RC)
        result[name] = (spec, build_store(spec, RC))
    return result


def test_the_moving_triad(runs):
    spec, _ = runs['turntable']
    time = 0.7
    assert np.allclose(moving_triad(spec.frame, time, 'inertial'),
                       spec.frame.rotation(time), atol=1e-14)
    assert np.allclose(moving_triad(spec.frame, time, 'rotating'),
                       spec.frame.rotation(time).T, atol=1e-14)


def test_the_platform_triads_and_the_earth_triads(runs):
    spec, _ = runs['turntable']
    pair, axis_arrow = triads(spec, 'inertial', 0.5, 2.0, np.zeros(3))
    (fixed, own_role, own_labels, _), (moving, other_role, _, is_moving) = \
        pair
    assert axis_arrow is None
    assert np.allclose(fixed, 0.5 * np.eye(3))
    assert np.allclose(moving, 0.5 * spec.frame.rotation(0.5))
    assert own_role == 'inertial_axes' and other_role == 'rotating_axes'
    assert is_moving
    earth, _ = runs['earth_drop']
    pair, axis_arrow = triads(earth, 'rotating', 0.5, 2.0, np.zeros(3))
    (fixed, _, labels, _), (moving, _, primed, _) = pair
    assert labels == ('E', 'N', 'U') and primed == ("E'", "N'", "U'")
    assert np.allclose(fixed, 0.5 * earth.axes.basis())
    assert np.allclose(moving, 0.5 * earth.frame.rotation(0.5).T
                       @ earth.axes.basis())
    assert axis_arrow[2] == 'Ω'
    assert np.allclose(axis_arrow[0], 0.5 * earth.frame.axis)


def test_the_stage_turns_in_the_right_view(runs):
    spec, _ = runs['turntable']
    at_rest = stage_surface(spec, 'inertial', 0.0, 1.0)[0]
    turned = stage_surface(spec, 'inertial', 0.9, 1.0)[0]
    rotation = spec.frame.rotation(0.9)
    # The points stay at rest; the rotation carries the turn.
    assert np.array_equal(turned['points'], at_rest['points'])
    assert np.allclose(at_rest['rotation'], np.eye(3))
    assert np.allclose(turned['rotation'], rotation, atol=1e-14)
    fixed = stage_surface(spec, 'rotating', 0.9, 1.0)[0]
    assert np.allclose(fixed['rotation'], np.eye(3))
    spec, _ = runs['merry_go_round']
    floor_rest = stage_surface(spec, 'rotating', 0.0, 1.0)[0]
    floor_turned = stage_surface(spec, 'rotating', 0.9, 1.0)[0]
    assert floor_rest['role'] == 'floor'
    assert np.allclose(floor_turned['rotation'], rotation.T, atol=1e-14)
    assert np.allclose(stage_surface(spec, 'inertial', 0.9, 1.0)[0]
                       ['rotation'], np.eye(3))
    earth, _ = runs['earth_drop']
    ground = stage_surface(earth, 'rotating', 0.0, 1.0)[0]
    assert ground['role'] == 'stage'
    assert {text for _, text in ground['labels']} == {'E', 'N', 'W', 'S'}
    up = earth.axes.up
    assert np.allclose((ground['points'] - ground['points'][0]) @ up, 0.0,
                       atol=1e-9)
    inertial_ground = stage_surface(earth, 'inertial', 0.9, 1.0)[0]
    assert np.allclose(inertial_ground['rotation'],
                       earth.frame.rotation(0.9))


def test_trails_stop_at_the_mask(runs):
    spec, store = runs['merry_go_round']
    valid = store.valid_samples(0)
    points, role = trail(store, 0, 1000, 'rotating')
    assert len(points) == valid
    assert role == 'trail_0'
    assert np.array_equal(points, store.positions_rot[0, :valid])
    short, _ = trail(store, 0, 3, 'inertial')
    assert len(short) == 4
    extras = extra_trails(store, spec, 0, {'check', 'ghost', 'overlay'})
    labels = [label for _, _, _, label in extras]
    assert 'check' in labels and 'ghost' in labels
    assert ('first order' in labels) == (store.overlay is not None)
    for points, _, _, _ in extras:
        assert len(points) == valid                 # whole paths
    assert extra_trails(store, spec, 0, set()) == []
    assert np.allclose(ghost_now(store, spec, 0, 0), spec.axes.launch_point
                       + store.ghost[0, 0])
    assert np.allclose(ghost_now(store, spec, 0, 10_000),
                       spec.axes.launch_point + store.ghost[0, valid - 1])
