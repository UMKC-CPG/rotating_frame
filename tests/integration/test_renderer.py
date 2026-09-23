"""Verifies pseudocode 9.7 for `render/vedo_renderer.py`, skipping
without an offscreen context: two views, one view, the panel strip,
and pixels that change between samples."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from rotating_frame.analysis import budget_at
from rotating_frame.render.panels import (budget_lines, cursor_fraction,
                                          render_panel)
from rotating_frame.render.scene_description import Strip, describe
from rotating_frame.run import build_store, load_rc, load_run_file

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])


def state(**changes):
    base = dict(k=0, tracked=0, view='both',
                arrows=frozenset({'true', 'centrifugal', 'coriolis', 'euler',
                                  'sum', 'velocity'}),
                paths=frozenset({'ghost', 'check'}),
                scenery=frozenset({'triads', 'stage'}), legend=False,
                camera_mode='follow', arrow_mode='auto', palette='light')
    base.update(changes)
    return SimpleNamespace(**base)


@pytest.fixture(scope='module')
def turntable():
    spec = load_run_file(EXAMPLES / 'turntable.toml', ['run.samples=40'],
                         RC)
    return spec, build_store(spec, RC)


def render_at(renderer, spec, store, the_state, strip=None):
    scenes = describe(store, spec, the_state, RC)
    for index, scene in enumerate(scenes):
        renderer.set_camera(index, spec.view.camera, scene.info)
    renderer.realize(scenes, the_state.palette, strip)
    return renderer.screenshot(as_array=True)


def test_two_views_draw_and_change_between_samples(offscreen_context,
                                                   turntable):
    from rotating_frame.render.vedo_renderer import TwoViewRenderer
    spec, store = turntable
    renderer = TwoViewRenderer((640, 400), True, 2, 'light')
    first = render_at(renderer, spec, store, state(k=0))
    later = render_at(renderer, spec, store, state(k=30))
    renderer.close()
    assert first.min() != first.max()
    assert not np.array_equal(first, later)


def test_one_view_and_the_panel_strip(offscreen_context, turntable):
    from rotating_frame.render.vedo_renderer import TwoViewRenderer
    spec, store = turntable
    budget = budget_at(store.comparison[0], store.conserved[0], spec.field,
                       spec, 0, SimpleNamespace(arrow_ratio=None,
                                                camera_follows=True))
    cursor = cursor_fraction(store, 0, 10)
    strip = Strip(images=[(render_panel(name, store, 0, 'dark',
                                        size=(200, 150)), cursor)
                          for name in ('terms', 'conservation')],
                  lines=tuple(budget_lines(budget)))
    renderer = TwoViewRenderer((640, 480), True, 1, 'dark',
                               with_panels=True)
    image = render_at(renderer, spec, store, state(view='rotating',
                                                   palette='dark'), strip)
    assert image.min() != image.max()
    assert renderer.layout == (1, True)
    without = render_at(renderer, spec, store, state(view='rotating',
                                                     palette='dark'))
    assert renderer.layout == (1, False)
    assert not np.array_equal(image, without)
    renderer.close()
