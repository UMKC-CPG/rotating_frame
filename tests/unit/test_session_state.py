"""Verifies pseudocode 10.7 for `ui/session_state.py`: the initial
state from each packaged run's [view] table, and every transition,
with no window."""

from pathlib import Path

import pytest

from rotating_frame.run import build_store, load_rc, load_run_file
from rotating_frame.ui.session_state import (ARROW_NAMES, OTHER_COMMANDS,
                                             RATES, RUN_COMMANDS,
                                             VIEWING_COMMANDS, VIEWS,
                                             initial_state, tick,
                                             transition)

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])
NAMES = ('turntable', 'merry_go_round', 'earth_drop', 'earth_throw',
         'earth_vertical')


@pytest.fixture(scope='module')
def runs():
    result = {}
    for name in NAMES:
        spec = load_run_file(EXAMPLES / f'{name}.toml',
                             ['run.samples=30', 'check.enabled=false'], RC)
        result[name] = (spec, build_store(spec, RC))
    return result


@pytest.mark.parametrize('name', NAMES)
def test_initial_state_matches_the_view_table(runs, name):
    spec, _ = runs[name]
    state = initial_state(spec)
    view = spec.view
    assert state.k == 0 and not state.playing and state.rate == 1
    assert state.view == view.views
    assert state.arrows == frozenset(view.arrows)
    assert ('ghost' in state.paths) == view.ghost
    assert ('check' in state.paths) == view.check_path
    assert ('overlay' in state.paths) == (view.overlay != 'off')
    assert ('triads' in state.scenery) == view.triads
    assert ('stage' in state.scenery) == view.stage
    assert state.panels == view.panels and state.legend == view.legend
    assert state.palette == view.palette
    assert state.tracked == view.tracked
    assert state.camera_mode == ('follow' if view.camera['follow']
                                 else 'fixed')
    assert state.arrow_mode == view.arrow_scale


def test_play_step_and_reverse(runs):
    spec, store = runs['turntable']
    state = initial_state(spec)
    playing = transition(state, 'play_pause', store)
    assert playing.playing
    paused = transition(playing, 'play_pause', store)
    assert paused.k == state.k and not paused.playing
    forward = transition(state, 'step_forward', store)
    assert forward.k == 1 and not forward.playing
    assert transition(forward, 'step_back', store).k == 0
    assert transition(state, 'step_back', store).k == 0
    reversed_state = transition(forward, 'reverse', store)
    assert reversed_state.direction == -1
    running = transition(reversed_state, 'play_pause', store)
    assert tick(running, store).k == 0


def test_tick_holds_or_wraps_at_the_end(runs):
    spec, store = runs['turntable']
    n = store.n_samples
    state = initial_state(spec)
    at_end = transition(transition(state, 'jump_end', store), 'play_pause',
                        store)
    held = tick(at_end, store)
    assert held.k == n - 1 and not held.playing
    looping = transition(at_end, 'loop', store)
    assert tick(looping, store).k == 0
    assert tick(state, store) == state              # paused: no change
    fast = transition(transition(state, 'faster', store), 'play_pause',
                      store)
    assert tick(fast, store).k == 2


def test_rate_saturates(runs):
    spec, store = runs['turntable']
    state = initial_state(spec)
    for _ in range(10):
        state = transition(state, 'faster', store)
    assert state.rate == RATES[-1]
    for _ in range(10):
        state = transition(state, 'slower', store)
    assert state.rate == 1
    assert transition(transition(state, 'faster', store), 'normal',
                      store).rate == 1


def test_every_toggle_is_its_own_inverse(runs):
    spec, store = runs['earth_throw']
    state = initial_state(spec)
    toggles = [c for c in VIEWING_COMMANDS if c.startswith('toggle_')]
    for command in toggles:
        once = transition(state, command, store)
        assert once != state, command
        assert transition(once, command, store) == state, command
    emptied = transition(state, 'toggle_all_arrows', store)
    assert emptied.arrows == frozenset()
    assert transition(emptied, 'toggle_all_arrows', store).arrows == \
        frozenset(ARROW_NAMES)
    partial = transition(state, 'toggle_arrow_euler', store)
    assert transition(partial, 'toggle_all_arrows', store).arrows == \
        frozenset(ARROW_NAMES)


def test_cycles_wrap(runs):
    spec, store = runs['turntable']
    state = initial_state(spec)
    seen = []
    for _ in range(len(VIEWS)):
        seen.append(state.view)
        state = transition(state, 'cycle_view', store)
    assert seen == list(VIEWS) and state.view == VIEWS[0]
    palettes = set()
    for _ in range(3):
        palettes.add(state.palette)
        state = transition(state, 'cycle_palette', store)
    assert palettes == {'light', 'dark', 'colorblind'}
    for _ in range(store.n_particles):
        state = transition(state, 'next_tracked', store)
    assert state.tracked == 0


def test_jump_event_and_set_sample(runs):
    spec, store = runs['merry_go_round']
    state = initial_state(spec)
    stop = store.stop_of(0)
    jumped = transition(state, 'jump_event', store)
    assert jumped.k == (store.n_samples - 1 if stop is None else stop.index)
    spec_t, store_t = runs['turntable']
    tracked = 0
    assert store_t.stop_of(tracked) is not None
    assert transition(initial_state(spec_t), 'jump_event', store_t).k == \
        store_t.stop_of(tracked).index
    clipped = transition(state, 'set_sample', store, 10_000)
    assert clipped.k == store.n_samples - 1 and not clipped.playing
    assert transition(state, 'set_sample', store, -5).k == 0
    assert transition(state, 'set_sample', store, 7).k == 7


def test_other_commands_leave_the_state(runs):
    spec, store = runs['turntable']
    state = transition(initial_state(spec), 'step_forward', store)
    for command in RUN_COMMANDS + OTHER_COMMANDS + ('reset_camera',):
        assert transition(state, command, store) == state
    with pytest.raises(ValueError, match='unknown command'):
        transition(state, 'dance', store)
