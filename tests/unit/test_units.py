"""Verifies pseudocode 2.5 for `core/units.py`: parsing dimensioned
strings, refusing the wrong dimension with the key named, and
formatting readouts."""

import numpy as np
import pytest

from rotating_frame.core.units import (UnitsError, format_real, parse,
                                       parse_vector)


def test_parsing_the_run_file_examples():
    assert parse('33.3 rpm', 'rate', 'frame.rate') == pytest.approx(
        3.4872, rel=1e-4)
    assert parse('39 deg', 'angle', 'frame.latitude') == pytest.approx(
        0.68068, rel=1e-4)
    assert parse('9.820 m/s^2', 'acceleration', 'force.magnitude') == \
        pytest.approx(9.820)
    assert parse('1.2 m', 'length', 'frame.length_scale') == 1.2
    assert parse('0.2 kg', 'mass', 'launch.mass') == 0.2
    assert parse('10 s', 'time', 'run.duration') == 10.0
    assert parse('3 m/s', 'speed', 'launch.speed') == 3.0


def test_the_wrong_dimension_is_refused_naming_the_key():
    with pytest.raises(UnitsError) as refusal:
        parse('3 m/s', 'length', 'launch.position[0]')
    assert refusal.value.key == 'launch.position[0]'
    assert 'launch.position[0]' in str(refusal.value)
    assert 'is not a length' in str(refusal.value)
    assert '1.2 m' in str(refusal.value)          # the example offered


def test_an_unreadable_string_is_refused_naming_the_key():
    with pytest.raises(UnitsError, match='frame.rate: cannot read'):
        parse('three', 'rate', 'frame.rate')
    with pytest.raises(ValueError, match='unknown kind'):
        parse('1 m', 'colour', 'x')


def test_parse_vector():
    vector = parse_vector(['1 m', '2 m', '300 cm'], 'length',
                          'launch.position')
    assert np.allclose(vector, [1.0, 2.0, 3.0])
    with pytest.raises(UnitsError, match=r'launch.position\[1\]'):
        parse_vector(['1 m', '2 s', '3 m'], 'length', 'launch.position')
    with pytest.raises(UnitsError, match='three components'):
        parse_vector(['1 m', '2 m'], 'length', 'launch.position')


def test_format_real():
    assert format_real(0.0155, 'length', 'cm') == '1.55 cm'
    assert format_real(1.0, 'angle', 'deg') == '57.3 deg'
    assert format_real(13713.44, 'time', 'h') == '3.809 h'
