"""Verifies pseudocode 10.7 for `ui/controls.py` and `parse_script`:
every chord maps to a command, every non-alias chord is in the
legend, only `q` is a plain key, and a script parses or refuses."""

import pytest

from rotating_frame.ui.controls import (KEY_CHORDS, LEGEND, command_for,
                                        legend_lines)
from rotating_frame.ui.session_state import (OTHER_COMMANDS, RUN_COMMANDS,
                                             VIEWING_COMMANDS)
from rotating_frame.ui.vedo_controls import parse_script


def test_every_chord_maps_to_a_known_command():
    known = set(VIEWING_COMMANDS) | set(RUN_COMMANDS) | set(OTHER_COMMANDS)
    for chord, command in KEY_CHORDS.items():
        assert command in known, chord
    bound = set(KEY_CHORDS.values())
    assert bound == known - {'set_sample'}      # the slider's command


def test_only_q_is_a_plain_key():
    plain = [chord for chord in KEY_CHORDS if not chord.startswith('Ctrl+')]
    assert plain == ['q']
    assert command_for('q') == 'quit' and command_for('Ctrl+q') == 'quit'
    assert command_for('s') is None and command_for('Ctrl+s') == \
        'step_forward'
    assert command_for('Ctrl+S') == 'step_back'


def test_the_legend_lists_every_non_alias_chord():
    lines = legend_lines()
    for chord, help_text in LEGEND:
        if help_text:
            assert any(line.startswith(chord) and help_text in line
                       for line in lines), chord
        else:
            assert not any(line.startswith(chord + ' ') for line in lines)
    assert all(len(line) <= 80 for line in lines)


def test_parse_script():
    assert parse_script('5:play_pause,20:reverse,40:set_sample=7') == [
        (5, 'play_pause', None), (20, 'reverse', None),
        (40, 'set_sample', 7)]
    assert parse_script('') == [] and parse_script(None) == []
    assert parse_script(' 3:quit , ') == [(3, 'quit', None)]
    with pytest.raises(ValueError, match="'9:dance'.*unknown command"):
        parse_script('9:dance')
    with pytest.raises(ValueError, match='tick must be an integer'):
        parse_script('soon:play_pause')
    with pytest.raises(ValueError, match='TICK:COMMAND'):
        parse_script('play_pause')
    with pytest.raises(ValueError, match='must not be negative'):
        parse_script('-1:play_pause')
