"""Verifies pseudocode 8.7 for `run/schema.py`: every refusal of 8.1
with a minimal run file each, the shipped examples passing, and the
overrides."""

import copy
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:                      # Python 3.10
    import tomli as tomllib

from rotating_frame.run.schema import (RunFileError, apply_overrides,
                                       check_latitude, validate_raw)

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'

MINIMAL = {'schema': 1, 'frame': {'preset': 'turntable'},
           'launch': [{'position': ['0.1 m', '0 m', '0 m']}],
           'run': {'duration': '1 s'}}


def altered(**changes):
    data = copy.deepcopy(MINIMAL)
    for dotted, value in changes.items():
        table, name = dotted.split('__')
        if table == 'launch0':
            data['launch'][0][name] = value
        else:
            data.setdefault(table, {})[name] = value
    return data


def test_the_shipped_examples_pass():
    for path in sorted(EXAMPLES.glob('*.toml')):
        if path.stem == 'circle':               # the placeholder, until
            continue                            #   section 10 removes it
        validate_raw(tomllib.loads(path.read_text()))
    validate_raw(MINIMAL)


@pytest.mark.parametrize('data, key', [
    ({**MINIMAL, 'schema': 2}, 'schema = 1'),
    ({**MINIMAL, 'flavour': {}}, r'\[flavour\]: unknown table'),
    (altered(frame__colour='red'), 'frame.colour: unknown key'),
    (altered(frame__preset='moon'), 'frame.preset'),
    (altered(frame__rate=3.5), 'frame.rate: needs units'),
    (altered(frame__exaggeration='big'), 'frame.exaggeration: expected'),
    (altered(frame__exaggeration=0.0), 'frame.exaggeration: must'),
    (altered(frame__latitude='39 deg'), 'only the earth preset'),
    (altered(run__samples=1), 'run.samples'),
    (altered(run__stop='explodes'), 'run.stop'),
    (altered(check__substeps=0), 'check.substeps'),
    (altered(check__enabled='yes'), 'check.enabled: expected true'),
    (altered(view__tracked=-1), 'view.tracked'),
    (altered(view__arrows=['true', 'gravity']), 'view.arrows'),
    (altered(view__camera={'zoom': 2.0}), 'view.camera.zoom: unknown'),
    (altered(launch0__position=['1 m', '2 m']), r'launch\[0\].position'),
    (altered(launch0__position=['1 m', 2.0, '3 m']),
     'three strings with units, or three bare'),
    (altered(launch0__speed='1 m/s', launch0__velocity=['0', '0', '0']),
     'velocity or speed'),
    (altered(launch0__elevation='10 deg'), r'launch\[0\].elevation: needs'),
    (altered(launch0__frame='sideways'), r'launch\[0\].frame'),
    (altered(ring__count=3), 'ring.radius: required'),
    (altered(ring__count=0, ring__radius='1 m', ring__speed='1 m/s'),
     'ring.count: must'),
])
def test_each_refusal_names_the_key(data, key):
    with pytest.raises(RunFileError, match=key):
        validate_raw(data)


def test_a_missing_required_key_and_a_missing_latitude():
    data = copy.deepcopy(MINIMAL)
    del data['run']['duration']
    with pytest.raises(RunFileError, match='run.duration: required'):
        validate_raw(data)
    earth = altered(frame__preset='earth')
    with pytest.raises(RunFileError, match='frame.latitude: required'):
        validate_raw(earth)
    with pytest.raises(RunFileError, match='frame.latitude: must lie'):
        check_latitude(1.57)


def test_apply_overrides():
    data = copy.deepcopy(MINIMAL)
    apply_overrides(data, ['frame.exaggeration=10', 'run.samples=50',
                           'launch[0].speed="2 m/s"', 'view.ghost=false'])
    assert data['frame']['exaggeration'] == 10
    assert data['run']['samples'] == 50
    assert data['launch'][0]['speed'] == '2 m/s'
    assert data['view']['ghost'] is False
    with pytest.raises(RunFileError, match='TABLE.KEY=VALUE'):
        apply_overrides(data, ['nonsense'])
    with pytest.raises(RunFileError, match='cannot read the value'):
        apply_overrides(data, ['run.samples=[1,'])
