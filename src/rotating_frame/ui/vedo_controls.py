"""The two sources of commands: the window's keys and slider, and a
script (pseudocode 10.3; design 10.6).

Both feed the same dispatcher with the same command names, so that a
test drives every command a student can, and `--offscreen --script`
exercises the loop as the window does. This module imports no
graphics library: the window source is given a renderer that offers
`on_key` and `add_slider`.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import sys

from rotating_frame.ui.controls import command_for
from rotating_frame.ui.session_state import (OTHER_COMMANDS, RUN_COMMANDS,
                                             VIEWING_COMMANDS)

ALL_COMMANDS = VIEWING_COMMANDS + RUN_COMMANDS + OTHER_COMMANDS


class ControlsSource:
    """What the session asks of a controls source."""

    def commands_at(self, tick):
        raise NotImplementedError

    def wants_to_stop(self):
        raise NotImplementedError


class VedoControls(ControlsSource):
    """Keys and the slider of a window, queued until the next tick."""

    def __init__(self, renderer, n_samples, command_name='rfsim'):
        self.queue = []
        self.quit_requested = False
        self.command_name = command_name
        renderer.on_key(self._on_key)
        renderer.add_slider(self._on_slide, n_samples)

    def _on_key(self, key):
        command = command_for(key)
        if command is not None:
            self.queue.append((command, None))
            if command == 'quit':
                self.quit_requested = True
        elif key and key.startswith(('Ctrl+', 'Alt+')):
            # A chord the table does not know: say so, with the name
            # as it arrived, because key names differ between X
            # servers, remote desktops, and layouts, and this line is
            # how a mismatch is found.
            print(f'{self.command_name}: key {key!r} is not bound '
                  '(Ctrl+h: legend)', file=sys.stderr)

    def _on_slide(self, value):
        self.queue.append(('set_sample', int(round(value))))

    def commands_at(self, tick):
        commands, self.queue = self.queue, []
        return commands

    def wants_to_stop(self):
        return self.quit_requested


class ScriptedControls(ControlsSource):
    """A list of (tick, command, argument) and a frame count."""

    def __init__(self, script, frames):
        self.script = list(script)
        self.frames = int(frames)
        self.next_tick = 0

    def commands_at(self, tick):
        self.next_tick = tick + 1
        return [(command, argument) for when, command, argument
                in self.script if when == tick]

    def wants_to_stop(self):
        return self.next_tick >= self.frames


def parse_script(text):
    """`"5:play_pause,20:reverse,40:set_sample=7"` to a list of
    (tick, command, argument); an unknown command or a bad tick is a
    ValueError naming the entry."""
    script = []
    for entry in (text or '').split(','):
        entry = entry.strip()
        if not entry:
            continue
        if ':' not in entry:
            raise ValueError(f'script entry {entry!r}: expected '
                             'TICK:COMMAND[=ARGUMENT]')
        when, command = entry.split(':', 1)
        argument = None
        if '=' in command:
            command, argument = command.split('=', 1)
            try:
                argument = int(argument)
            except ValueError:
                raise ValueError(f'script entry {entry!r}: the argument '
                                 'must be an integer') from None
        try:
            when = int(when)
        except ValueError:
            raise ValueError(f'script entry {entry!r}: the tick must be '
                             'an integer') from None
        if when < 0:
            raise ValueError(f'script entry {entry!r}: the tick must not '
                             'be negative')
        if command not in ALL_COMMANDS:
            raise ValueError(f'script entry {entry!r}: unknown command '
                             f'{command!r}')
        script.append((when, command, argument))
    return script
