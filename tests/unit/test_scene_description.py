"""Verifies pseudocode 9.7 for `render/scene_description.py`, without
a renderer: the arrow sets of the two views, the labels, the scales
and the ratio, the camera target, and the readouts."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from rotating_frame.render.scene_description import (ARROW_FRACTION,
                                                     Arrow, Polyline, Text,
                                                     Triad, describe,
                                                     describe_view, extent)
from rotating_frame.run import build_store, load_rc, load_run_file

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])
PSEUDO_ROLES = {'centrifugal', 'coriolis', 'euler'}


def state(**changes):
    base = dict(k=0, tracked=0, view='both',
                arrows=frozenset({'true', 'centrifugal', 'coriolis', 'euler',
                                  'sum', 'velocity'}),
                paths=frozenset({'ghost', 'check', 'overlay'}),
                scenery=frozenset({'triads', 'stage'}), legend=True,
                camera_mode='follow', arrow_mode='auto', palette='light')
    base.update(changes)
    return SimpleNamespace(**base)


@pytest.fixture(scope='module')
def runs():
    result = {}
    for name in ('turntable', 'merry_go_round', 'earth_drop', 'earth_throw',
                 'earth_vertical'):
        spec = load_run_file(EXAMPLES / f'{name}.toml',
                             ['run.samples=80'], RC)
        result[name] = (spec, build_store(spec, RC))
    return result


def arrows_of(scene):
    return [d for d in scene.dynamic if isinstance(d, Arrow)]


@pytest.mark.parametrize('name', ['turntable', 'merry_go_round',
                                  'earth_drop', 'earth_throw',
                                  'earth_vertical'])
@pytest.mark.parametrize('k', [0, 40, 79])
def test_the_two_views_draw_the_right_arrows(runs, name, k):
    spec, store = runs[name]
    inertial = describe_view(store, spec, state(k=k), RC, 'inertial')
    rotating = describe_view(store, spec, state(k=k), RC, 'rotating')
    inertial_roles = {a.role for a in arrows_of(inertial)
                      if a.label != 'Ω'}
    assert inertial_roles == {'true', 'velocity'}
    assert not inertial_roles & PSEUDO_ROLES
    rotating_roles = {a.role for a in arrows_of(rotating) if a.label != 'Ω'}
    assert rotating_roles == {'true', 'centrifugal', 'coriolis', 'euler',
                              'sum', 'velocity'}
    for scene in (inertial, rotating):
        for arrow in arrows_of(scene):
            assert arrow.label
        for line in scene.dynamic:
            if isinstance(line, Polyline) and line.style != 'solid':
                assert line.label
    fewer = describe_view(store, spec, state(arrows=frozenset({'coriolis'})),
                          RC, 'rotating')
    assert {a.role for a in arrows_of(fewer) if a.label != 'Ω'} == \
        {'coriolis'}


def test_arrow_lengths_and_the_stated_ratio(runs):
    spec, store = runs['earth_throw']
    scene = describe_view(store, spec, state(), RC, 'rotating')
    info = scene.info
    assert info.arrow_ratio is not None and info.arrow_ratio > 100.0
    terms, force = store.terms_at(0, 0)
    lengths = {a.role: np.linalg.norm(a.tip - a.base)
               for a in arrows_of(scene) if a.label != 'Ω'}
    assert lengths['true'] == pytest.approx(ARROW_FRACTION * info.extent)
    largest_term = max(np.linalg.norm(terms, axis=-1))
    assert lengths['centrifugal'] == pytest.approx(
        ARROW_FRACTION * info.extent * np.linalg.norm(terms[0])
        / largest_term)
    same = describe_view(store, spec, state(arrow_mode='same'), RC,
                         'rotating')
    assert same.info.arrow_ratio is None
    assert same.info.scale_pseudo == same.info.scale_true
    turntable, store_t = runs['turntable']
    plain = describe_view(store_t, turntable, state(), RC, 'rotating')
    assert plain.info.arrow_ratio is None


def test_the_camera_target_follows_or_stays(runs):
    spec, store = runs['earth_drop']
    k = 40
    following = describe_view(store, spec, state(k=k), RC, 'inertial')
    fixed = describe_view(store, spec, state(k=k, camera_mode='fixed'), RC,
                          'inertial')
    time = store.time_at(0, k)                   # the grid's clock
    assert np.allclose(following.info.camera_target,
                       spec.frame.rotation(time) @ spec.axes.launch_point)
    assert np.allclose(fixed.info.camera_target, spec.axes.launch_point)
    assert following.info.camera_follows and not fixed.info.camera_follows
    rotating = describe_view(store, spec, state(k=k), RC, 'rotating')
    assert np.allclose(rotating.info.camera_target, spec.axes.launch_point)
    # Every dynamic point is relative to the target: the tracked
    # glyph sits near the origin of the scene.
    glyph_centers = [d.center for d in rotating.dynamic
                     if type(d).__name__ == 'Glyph']
    assert np.linalg.norm(glyph_centers[0]) < 2.0 * rotating.info.extent


def test_describe_returns_one_or_two_scenes(runs):
    spec, store = runs['turntable']
    assert len(describe(store, spec, state(), RC)) == 2
    assert len(describe(store, spec, state(view='inertial'), RC)) == 1
    assert describe(store, spec, state(view='rotating'), RC)[0].view == \
        'rotating'


def test_the_moving_triad_is_dynamic_and_the_fixed_one_static(runs):
    spec, store = runs['turntable']
    scene = describe_view(store, spec, state(k=10), RC, 'inertial')
    static_triads = [d for d in scene.static if isinstance(d, Triad)]
    dynamic_triads = [d for d in scene.dynamic if isinstance(d, Triad)]
    assert len(static_triads) == 1 and len(dynamic_triads) == 1
    time = store.time_at(0, 10)                  # the grid's clock
    assert np.allclose(dynamic_triads[0].axes,
                       0.25 * scene.info.extent * spec.frame.rotation(time))


def test_the_readouts_say_what_the_design_asks(runs):
    spec, store = runs['earth_drop']
    scene = describe_view(store, spec, state(k=20), RC, 'rotating')
    text = [d for d in scene.dynamic if isinstance(d, Text)
            and d.corner == 'top_left'][0]
    joined = '\n'.join(text.lines)
    assert '1 unit = 100 m' in joined
    assert 'launch point' in joined                 # the approximation note
    assert 'launch: at rest' in joined
    assert 'Coriolis' in joined and 'centrifugal' in joined
    assert 'Ω exaggerated' not in joined
    exaggerated_spec = load_run_file(EXAMPLES / 'earth_drop.toml',
                                     ['run.samples=80',
                                      'frame.exaggeration=10'], RC)
    exaggerated = describe_view(build_store(exaggerated_spec, RC),
                                exaggerated_spec, state(), RC, 'inertial')
    inertial_text = [d for d in exaggerated.dynamic if isinstance(d, Text)
                     and d.corner == 'top_left'][0]
    assert 'Ω exaggerated × 10' in '\n'.join(inertial_text.lines)
    assert 'camera follows P' in '\n'.join(inertial_text.lines)
    turntable, store_t = runs['turntable']
    plain = describe_view(store_t, turntable, state(), RC, 'rotating')
    plain_text = [d for d in plain.dynamic if isinstance(d, Text)][0]
    assert 'launch point' not in '\n'.join(plain_text.lines)


def test_labels_are_spread_at_a_landing(runs):
    spec, store = runs['earth_drop']
    landing = store.stop_of(0).index
    scene = describe_view(store, spec, state(k=landing), RC, 'rotating')
    anchors = [d.label_at for d in scene.dynamic
               if isinstance(d, (Arrow, Polyline)) and d.label]
    assert len(anchors) >= 6
    for i, first in enumerate(anchors):
        assert first is not None
        for second in anchors[i + 1:]:
            assert np.linalg.norm(first - second) >= \
                0.1 * scene.info.extent - 1e-12
    # A long arrow keeps its label at its tip.
    scene = describe_view(store, spec, state(k=0), RC, 'rotating')
    true = [a for a in arrows_of(scene) if a.role == 'true'][0]
    assert np.linalg.norm(true.label_at - true.tip) <= \
        0.05 * scene.info.extent


def test_extent_is_at_least_one(runs):
    spec, store = runs['turntable']
    assert extent(store, spec) >= 1.0
