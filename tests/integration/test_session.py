"""Verifies pseudocode 10.7 for the session: a scripted session
offscreen, every viewing command leaving the store untouched, the
run controls doing what design 10.1 says, and the scripted clock
matching the pure state machine. Skips without an offscreen
context."""

import hashlib
import random
from pathlib import Path

import numpy as np
import pytest

from rotating_frame.run import build_store, load_rc, load_run_file
from rotating_frame.run.serialization import resolved_words
from rotating_frame.ui import (ScriptedControls, Session, initial_state,
                               run_session, tick, transition)
from rotating_frame.ui.session_state import VIEWING_COMMANDS

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
NAMES = ('turntable', 'merry_go_round', 'earth_drop', 'earth_throw',
         'earth_vertical')
SMALL = ['run.samples=40']


@pytest.fixture
def rc(tmp_path):
    settings = load_rc([Path(__file__).parent])
    return settings.__class__(**{**settings.__dict__,
                                 'output_dir': str(tmp_path)})


def make_renderer(offscreen_context, n_views=2):
    from rotating_frame.render.vedo_renderer import TwoViewRenderer
    return TwoViewRenderer((320, 240), True, n_views, 'light')


def checksum(store):
    digest = hashlib.sha256()
    for array in (store.positions_in, store.velocities_in,
                  store.positions_rot):
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


_BUILT = {}                       # (name, extras) -> (spec, store)


def load(name, rc, extra=()):
    """A run's spec and store, built once per module: a store is
    read-only and does not depend on the rc's output directory, so
    every test can share it."""
    key = (name, tuple(extra))
    if key not in _BUILT:
        spec = load_run_file(EXAMPLES / f'{name}.toml',
                             SMALL + list(extra), rc)
        _BUILT[key] = (spec, build_store(spec, rc))
    return _BUILT[key]


@pytest.mark.parametrize('name', NAMES)
def test_every_viewing_command_leaves_the_store_unchanged(
        offscreen_context, rc, name):
    spec, store = load(name, rc)
    before = checksum(store)
    commands = [c for c in VIEWING_COMMANDS if c != 'set_sample']
    random.Random(name).shuffle(commands)
    script = [(index, command, None)
              for index, command in enumerate(commands)]
    script.append((len(commands), 'set_sample', 3))
    renderer = make_renderer(offscreen_context)
    final = run_session(spec, store, rc,
                        ScriptedControls(script, len(commands) + 2),
                        renderer)
    renderer.close()
    assert checksum(store) == before
    assert final.k == 3 and not final.playing


def session_for(name, rc, offscreen_context, extra=()):
    spec, store = load(name, rc, extra)
    renderer = make_renderer(offscreen_context)
    session = Session(spec, store, rc, ScriptedControls([], 1), renderer,
                      run_name=name)
    session.redraw()
    return session


def saved_reloads_equal(session, rc):
    path = session.save()
    reloaded = load_run_file(path, (), rc)
    mine = resolved_words(session.spec)
    theirs = resolved_words(reloaded)
    mine.pop('view'), theirs.pop('view')
    assert theirs == mine
    assert np.allclose(reloaded.launches[0].velocity_in,
                       session.spec.launches[0].velocity_in)
    assert reloaded.exaggeration == session.spec.exaggeration


def test_exaggeration_up(offscreen_context, rc):
    session = session_for('earth_drop', rc, offscreen_context)
    session.handle('step_forward')
    session.handle('toggle_arrow_euler')
    before = session.state
    old_rate = session.spec.scales.rate
    session.handle('exaggeration_up')
    assert session.spec.exaggeration == 2.0
    assert session.spec.scales.rate == pytest.approx(2.0 * old_rate)
    assert session.state == before
    from rotating_frame.analysis import budget_at
    budget = budget_at(session.store.comparison[0],
                       session.store.conserved[0], session.spec.field,
                       session.spec, 1, session.scenes[-1].info)
    assert budget.distortion['exaggeration'] == 2.0
    saved_reloads_equal(session, rc)
    session.handle('exaggeration_down')
    assert session.spec.exaggeration == 1.0
    session.renderer.close()


def test_substeps_up(offscreen_context, rc):
    session = session_for('merry_go_round', rc, offscreen_context)
    old_store = session.store
    old_max = old_store.comparison[0].max_delta
    session.handle('substeps_up')
    assert session.spec.check.substeps == 8
    ratio = old_max / session.store.comparison[0].max_delta
    assert 14.0 <= ratio <= 18.0
    assert np.array_equal(session.store.positions_in,
                          old_store.positions_in, equal_nan=True)
    saved_reloads_equal(session, rc)
    session.handle('substeps_down')
    assert session.spec.check.substeps == 4
    session.renderer.close()


def test_speed_up_on_the_tracked_particle(offscreen_context, rc):
    session = session_for('turntable', rc, offscreen_context)
    old_store = session.store
    session.handle('speed_up')
    launch = session.spec.launches[0].spec
    assert launch.velocity is None
    assert launch.speed == pytest.approx(2.0 * np.linalg.norm(
        old_store.spec.launches[0].spec.velocity))
    for particle in range(1, session.store.n_particles):
        assert np.array_equal(session.store.positions_rot[particle],
                              old_store.positions_rot[particle],
                              equal_nan=True)
    saved_reloads_equal(session, rc)
    session.renderer.close()


def test_azimuth_right_on_a_ring_member(offscreen_context, rc):
    session = session_for('turntable', rc, offscreen_context)
    old_store = session.store
    member = 4                          # launch 0 is the puck
    session.handle('next_tracked')
    for _ in range(member - 1):
        session.handle('next_tracked')
    assert session.state.tracked == member
    session.handle('azimuth_right')
    assert 'ring' not in session.spec.words
    assert len(session.spec.words['launch']) == old_store.n_particles
    assert session.spec.ring is None
    turned = session.spec.launches[member].spec
    old = old_store.spec.launches[member].spec
    old_azimuth = np.degrees(np.arctan2(old.velocity[0], old.velocity[1]))
    assert np.degrees(turned.azimuth) == pytest.approx(
        (old_azimuth + 15.0) % 360.0)
    for particle in range(old_store.n_particles):
        same = np.array_equal(session.store.positions_rot[particle],
                              old_store.positions_rot[particle],
                              equal_nan=True)
        assert same == (particle != member)
    saved_reloads_equal(session, rc)
    session.renderer.close()


def test_elevation_saturates(offscreen_context, rc):
    session = session_for('earth_throw', rc, offscreen_context)
    for _ in range(5):
        session.handle('elevation_up')
    assert np.degrees(session.spec.launches[0].spec.elevation) == \
        pytest.approx(90.0)
    session.handle('elevation_down')
    assert np.degrees(session.spec.launches[0].spec.elevation) == \
        pytest.approx(75.0)
    saved_reloads_equal(session, rc)
    session.renderer.close()


def test_cycle_view_and_camera_mode(offscreen_context, rc):
    session = session_for('earth_drop', rc, offscreen_context)
    assert len(session.scenes) == 2
    session.handle('cycle_view')
    session.redraw()
    assert len(session.scenes) == 1 and session.scenes[0].view == 'inertial'
    session.handle('set_sample', 5)
    session.redraw()
    following = session.scenes[0].info.camera_target.copy()
    session.handle('toggle_camera_mode')
    session.redraw()
    fixed = session.scenes[0].info.camera_target
    assert np.allclose(fixed, session.spec.axes.launch_point)
    assert not np.allclose(following, fixed)
    session.handle('toggle_panels')
    session.redraw()
    assert session.renderer.layout == (1, False)
    session.renderer.close()


def test_panels_are_cached_and_the_frame_note_appears(offscreen_context,
                                                      rc):
    from rotating_frame.render.scene_description import Text
    session = session_for('merry_go_round', rc, offscreen_context)
    first = session.plotted_panel('terms')
    session.handle('step_forward')
    session.redraw()
    assert session.plotted_panel('terms') is first        # kept
    assert len(session.panel_cache) == 2                  # two plots
    session.handle('cycle_palette')
    session.redraw()
    assert len(session.panel_cache) == 4                  # per palette
    readout = [d for d in session.scenes[0].dynamic
               if isinstance(d, Text) and d.corner == 'top_left'][0]
    assert any('frames/s' in line for line in readout.lines)
    session.handle('substeps_up')                         # a new run
    assert session.panel_cache == {}
    session.redraw()
    assert session.plotted_panel('terms') is not first
    session.renderer.close()


def test_a_tick_during_a_redraw_is_dropped(offscreen_context, rc):
    session = session_for('turntable', rc, offscreen_context)
    session.handle('play_pause')
    ticks_seen = []
    original = session.redraw

    def nested_redraw():
        original()
        ticks_seen.append('drawn')
        session.on_tick(99)                     # arrives mid-frame
    session.redraw = nested_redraw
    session.on_tick(1)
    assert ticks_seen == ['drawn'] and session.state.k == 1


def test_the_scripted_clock_matches_the_state_machine(offscreen_context,
                                                      rc):
    spec, store = load('turntable', rc)
    script = [(5, 'play_pause', None), (20, 'reverse', None),
              (30, 'play_pause', None)]
    renderer = make_renderer(offscreen_context)
    final = run_session(spec, store, rc, ScriptedControls(script, 60),
                        renderer)
    renderer.close()
    expected = initial_state(spec)
    for when in range(60):
        for at, command, argument in script:
            if at == when:
                expected = transition(expected, command, store, argument)
        expected = tick(expected, store)
    assert final == expected
    assert final.k == 5 and not final.playing        # 15 on, 10 back
