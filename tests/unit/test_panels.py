"""Verifies pseudocode 9.7 for `render/panels.py`: each panel renders
to an array of the requested size, at the first and the last sample,
for every packaged run, and a budget with an empty column renders."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from rotating_frame.analysis import budget_at
from rotating_frame.render.panels import PANEL_NAMES, render_panel
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
    for sample in (0, store.n_samples - 1):
        budget = budget_at(store.comparison[0], store.conserved[0],
                           spec.field, spec, min(sample,
                                                 store.valid_samples(0) - 1),
                           scene_info)
        for panel in PANEL_NAMES:
            for palette in ('light', 'dark'):
                image = render_panel(panel, store, 0, sample, palette,
                                     budget=budget, size=(320, 240))
                assert image.shape == (240, 320, 3)
                assert image.dtype == np.uint8
                assert image.min() != image.max()


def test_a_budget_with_empty_columns_renders():
    spec = load_run_file(EXAMPLES / 'turntable.toml',
                         ['run.samples=30', 'check.enabled=false'], RC)
    store = build_store(spec, RC)
    assert store.comparison is None
    budget = budget_at(None, store.conserved[0], spec.field, spec, 0,
                       SimpleNamespace(arrow_ratio=None,
                                       camera_follows=False))
    image = render_panel('budget', store, 0, 0, 'colorblind', budget=budget)
    assert image.shape == (300, 400, 3)
    with pytest.raises(KeyError):
        render_panel('weather', store, 0, 0, 'light')
