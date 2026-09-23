"""Verifies pseudocode 9.7 for `render/panels.py`: each panel renders
to an array of the requested size for every packaged run, a budget
with an empty column renders and reads as text, and the cursor
fraction runs from 0 to 1 over the particle's valid samples."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from rotating_frame.analysis import budget_at
from rotating_frame.render.panels import (PANEL_NAMES, budget_lines,
                                          cursor_fraction, render_panel)
from rotating_frame.run import build_store, load_rc, load_run_file

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])
NAMES = ('turntable', 'merry_go_round', 'earth_drop', 'earth_throw',
         'earth_vertical')


@pytest.mark.parametrize('name', NAMES)
def test_every_panel_renders(name):
    spec = load_run_file(EXAMPLES / f'{name}.toml', ['run.samples=50'], RC)
    store = build_store(spec, RC)
    scene_info = SimpleNamespace(arrow_ratio=None, camera_follows=True)
    budget = budget_at(store.comparison[0], store.conserved[0], spec.field,
                       spec, 0, scene_info)
    for panel in PANEL_NAMES:
        for palette in ('light', 'dark'):
            image = render_panel(panel, store, 0, palette, budget=budget,
                                 size=(320, 240))
            assert image.shape == (240, 320, 3)
            assert image.dtype == np.uint8
            assert image.min() != image.max()
    valid = store.valid_samples(0)
    assert cursor_fraction(store, 0, 0) == 0.0
    assert cursor_fraction(store, 0, valid - 1) == 1.0
    assert cursor_fraction(store, 0, store.n_samples + 5) == 1.0
    middle = cursor_fraction(store, 0, valid // 2)
    assert 0.0 < middle < 1.0


def test_a_budget_with_empty_columns_renders():
    spec = load_run_file(EXAMPLES / 'turntable.toml',
                         ['run.samples=30', 'check.enabled=false'], RC)
    store = build_store(spec, RC)
    spec_full = load_run_file(EXAMPLES / 'turntable.toml',
                              ['run.samples=30'], RC)
    store_full = build_store(spec_full, RC)
    assert store.comparison is None
    budget = budget_at(None, store.conserved[0], spec.field, spec, 0,
                       SimpleNamespace(arrow_ratio=None,
                                       camera_follows=False))
    image = render_panel('budget', store, 0, 'colorblind', budget=budget)
    assert image.shape == (300, 400, 3)
    lines = budget_lines(budget)
    assert len(lines) == 4 and 'never combined' in lines[0]
    assert lines[1] == 'numerical      none'
    assert lines[2] == 'approximation  none'
    assert 'camera fixed' in lines[3]
    full = budget_at(store_full.comparison[0], store_full.conserved[0],
                     spec_full.field, spec_full, 3,
                     SimpleNamespace(arrow_ratio=2.5, camera_follows=True))
    full_lines = budget_lines(full)
    assert len(full_lines) == 5 and full_lines[1].startswith('numerical')
    assert 'max δ' in full_lines[2] and 'arrows × 2.5' in full_lines[4]
    with pytest.raises(KeyError):
        render_panel('weather', store, 0, 'light')
