"""Verifies pseudocode 8.7 for `run/serialization.py`: the same run
in SI and in natural units, the Earth example's resolution, the
write-back that reloads equal, the refusals, and a write that fails
as one line."""

import copy
import os
from pathlib import Path

import numpy as np
import pytest

from rotating_frame.core.presets import EARTH_ATTRACTION, EARTH_ROTATION_RATE
from rotating_frame.run import (RunFileError, load_rc, load_run_file,
                                resolve, write_resolved)
from rotating_frame.run.serialization import OVERLAY_OFF_NOTE

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])           # the built-in defaults

SI_RUN = {'schema': 1,
          'frame': {'preset': 'turntable', 'rate': '1 rad/s',
                    'length_scale': '2 m'},
          'launch': [{'position': ['0.5 m', '0 m', '0 m'],
                      'speed': '4 m/s', 'azimuth': '90 deg'}],
          'run': {'duration': '3 s', 'stop': 'duration'}}
NATURAL_RUN = {'schema': 1,
               'frame': {'preset': 'turntable', 'rate': '1 rad/s',
                         'length_scale': '2 m'},
               'launch': [{'position': [0.25, 0.0, 0.0], 'speed': 2.0,
                           'azimuth': np.pi / 2}],
               'run': {'duration': 3.0, 'stop': 'duration'}}


def specs_agree(one, other):
    assert one.duration == pytest.approx(other.duration, rel=1e-12)
    assert one.scales == other.scales
    assert one.stop == other.stop and one.samples == other.samples
    assert len(one.launches) == len(other.launches)
    for first, second in zip(one.launches, other.launches):
        assert np.allclose(first.position_in, second.position_in,
                           rtol=1e-12, atol=1e-15)
        assert np.allclose(first.velocity_in, second.velocity_in,
                           rtol=1e-12, atol=1e-15)


def test_si_and_natural_units_resolve_alike():
    specs_agree(resolve(SI_RUN, RC), resolve(NATURAL_RUN, RC))


def test_the_earth_example_resolves_as_the_design_says():
    spec = load_run_file(EXAMPLES / 'earth_drop.toml', (), RC)
    assert spec.frame.rate == 1.0
    assert spec.scales.rate == pytest.approx(EARTH_ROTATION_RATE)
    assert spec.field.closed_form == 'rotating_parabola'
    gravity_natural = np.linalg.norm(spec.field.gravity_rot)
    assert gravity_natural == pytest.approx(
        EARTH_ATTRACTION / spec.scales.acceleration, rel=1e-12)
    assert spec.field.approximation.timescale * spec.scales.time == \
        pytest.approx(805.5, abs=0.1)
    assert spec.latitude == pytest.approx(np.radians(39.0))
    assert spec.launches[0].spec.label == 'stone'
    assert spec.words['frame']['rate'].endswith('rad/s')


def test_write_back_reloads_equal(tmp_path):
    for name in ('turntable', 'merry_go_round', 'earth_drop', 'earth_throw',
                 'earth_vertical'):
        spec = load_run_file(EXAMPLES / f'{name}.toml', (), RC)
        target = tmp_path / f'{name}-resolved.toml'
        assert write_resolved(spec, target)
        text = target.read_text()
        assert text.startswith('# Resolved by rfsim')
        assert 'Omega =' in text
        specs_agree(load_run_file(target, (), RC), spec)


def test_overrides_reach_the_resolved_copy(tmp_path):
    spec = load_run_file(EXAMPLES / 'earth_drop.toml',
                         ['frame.exaggeration=10'], RC)
    assert spec.exaggeration == 10.0
    assert spec.scales.rate == pytest.approx(10.0 * EARTH_ROTATION_RATE)
    target = tmp_path / 'resolved.toml'
    write_resolved(spec, target)
    assert load_run_file(target, (), RC).exaggeration == 10.0
    with pytest.raises(RunFileError, match='frame.exaggeration'):
        load_run_file(EXAMPLES / 'earth_drop.toml',
                      ['frame.exaggeration="lots"'], RC)


@pytest.mark.parametrize('changes, key', [
    ({('run', 'stop'): 'leaves'}, 'run.stop'),
    ({('view', 'tracked'): 5}, 'view.tracked'),
    ({('frame', 'latitude'): '90 deg'}, 'frame.latitude: must lie'),
    ({('run', 'duration'): '0 s'}, 'run.duration: must be positive'),
    ({('frame', 'rate'): '3 m'}, 'frame.rate: .* is not a rate'),
])
def test_resolution_refusals_name_the_key(changes, key):
    data = {'schema': 1, 'frame': {'preset': 'earth', 'latitude': '39 deg'},
            'launch': [{'position': ['0 m', '0 m', '10 m']}],
            'run': {'duration': '2 s'}}
    for (table, name), value in changes.items():
        data.setdefault(table, {})[name] = value
    with pytest.raises(RunFileError, match=key):
        resolve(data, RC)


def test_nothing_to_throw_and_the_overlay_note():
    data = {'schema': 1, 'frame': {'preset': 'turntable'},
            'run': {'duration': '1 s'}}
    with pytest.raises(RunFileError, match='nothing to throw'):
        resolve(data, RC)
    data['launch'] = [{'position': ['0.1 m', '0 m', '0 m']}]
    data['view'] = {'overlay': 'on'}
    spec = resolve(data, RC)                    # a turn: not an error
    assert spec.overlay_note == OVERLAY_OFF_NOTE


def test_a_failed_write_is_one_line(tmp_path, capsys):
    locked = tmp_path / 'shared'
    locked.mkdir()
    locked.chmod(0o555)
    if os.access(locked, os.W_OK):
        pytest.skip('this user can write a read-only directory')
    spec = load_run_file(EXAMPLES / 'turntable.toml', (), RC)
    try:
        assert not write_resolved(spec, locked / 'out.toml')
    finally:
        locked.chmod(0o755)
    assert 'cannot write' in capsys.readouterr().err
