"""The loop, the run controls, and the save (pseudocode 10.4; design
10.1, 10.3, 10.4).

A session holds the run's spec and store, the scrubber's state, a
controls source, and a renderer. Each tick it applies the queued
commands, advances the clock, and redraws when anything changed. A
viewing command is a pure transition (session_state). A run control
edits the run's WORDS, the same TOML the student wrote, and resolves
and rebuilds them, so that what the keys did is exactly what a run
file could say, and `save` writes that file (design 10.1, G6).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import copy
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

from rotating_frame.analysis import budget_at
from rotating_frame.core.natural_units import factor
from rotating_frame.launch import expand_ring
from rotating_frame.render.panels import (budget_lines, cursor_fraction,
                                          render_panel)
from rotating_frame.render.scene_description import Strip, describe
from rotating_frame.run import ViewSettings, build_store, resolve
from rotating_frame.run.serialization import write_resolved
from rotating_frame.ui.controls import legend_lines
from rotating_frame.ui.session_state import (RUN_COMMANDS,
                                             VIEWING_COMMANDS,
                                             initial_state, tick,
                                             transition)
from rotating_frame.ui.vedo_controls import VedoControls

TICK_MILLISECONDS = 33               # thirty ticks a second
ANGLE_STEP_DEG = 15.0
PANEL_SIZE = (400, 300)
PLOTTED_PANELS = ('terms', 'conservation')
FRAME_WINDOW = 30                    # redraws the rate is measured over


def _si_text(spec, value_natural, kind, unit):
    """A natural-unit number as an exact SI string for the words."""
    return f'{float(value_natural * factor(spec.scales, kind))!r} {unit}'


def _natural(spec, value, kind, key):
    """A word (string with units, or a bare number in natural units)
    as a natural-unit float, through the same boundary the loader
    uses."""
    from rotating_frame.core import units
    if isinstance(value, str):
        return units.parse(value, kind, key) / factor(spec.scales, kind)
    return float(value)


class Session:
    """One run on screen: see the module docstring."""

    def __init__(self, spec, store, rc, controls, renderer,
                 run_name='run'):
        self.spec = spec
        self.store = store
        self.rc = rc
        self.controls = controls
        self.renderer = renderer
        self.run_name = run_name
        self.state = initial_state(spec)
        self.scenes = []
        self.dirty = True
        self.panel_cache = {}         # (name, id(store), tracked,
                                      #   palette) -> rgb image
        self.redrawing = False
        self.frame_stamps = deque(maxlen=FRAME_WINDOW)
        self.last_frame_seconds = None
        self.last_split = {}          # describe, panels, actors, render

    # -- commands ---------------------------------------------------

    def handle(self, command, argument=None):
        if command in VIEWING_COMMANDS:
            self.state = transition(self.state, command, self.store,
                                    argument)
            self.dirty = True
            if command == 'reset_camera':
                self.apply_cameras()
        elif command in RUN_COMMANDS:
            self.run_control(command)
        elif command == 'save':
            self.save()
        # 'quit' is read by the loop through the controls source.

    def _words_with_ring_expanded(self):
        """The run's words, with a ring written out as explicit
        launches when the tracked particle is one of its members, so
        that one member can be edited and written back. The members
        are written as bare numbers, which a run file reads in the
        run's natural units, because a number sent through SI and
        back is not always the same number in floating point, and
        the untouched members must reproduce bit for bit."""
        words = copy.deepcopy(self.spec.words)
        explicit = len(words.get('launch', []))
        if self.state.tracked >= explicit and 'ring' in words:
            members = []
            for member in expand_ring(self.spec.ring):
                members.append({
                    'position': [float(part) for part in member.position],
                    'velocity': [float(part) for part in member.velocity],
                    'frame': member.frame, 'label': member.label})
            words['launch'] = words.get('launch', []) + members
            del words['ring']
        return words

    def _to_speed_form(self, launch, key):
        """Put a launch's words in speed form: a velocity becomes a
        speed, an azimuth from north, and an elevation."""
        if 'velocity' not in launch:
            launch.setdefault('speed', '0.0 m/s')
            launch.setdefault('azimuth', '0.0 deg')
            launch.setdefault('elevation', '0.0 deg')
            return
        east, north, up = [_natural(self.spec, part, 'speed',
                                    f'{key}.velocity')
                           for part in launch['velocity']]
        speed = float(np.hypot(np.hypot(east, north), up))
        azimuth = float(np.degrees(np.arctan2(east, north))) % 360.0
        elevation = (0.0 if speed == 0.0
                     else float(np.degrees(np.arcsin(up / speed))))
        del launch['velocity']
        launch['speed'] = _si_text(self.spec, speed, 'speed', 'm/s')
        launch['azimuth'] = f'{azimuth!r} deg'
        launch['elevation'] = f'{elevation!r} deg'

    def run_control(self, command):
        """Edit the words, resolve, rebuild; keep the view."""
        words = self._words_with_ring_expanded()
        tracked = self.state.tracked
        key = f'launch[{tracked}]'
        if command.startswith('exaggeration'):
            frame = words['frame']
            frame['exaggeration'] = float(frame['exaggeration']) * (
                2.0 if command.endswith('up') else 0.5)
        elif command.startswith('substeps'):
            check = words['check']
            if command.endswith('up'):
                check['substeps'] = int(check['substeps']) * 2
            else:
                check['substeps'] = max(1, int(check['substeps']) // 2)
        else:
            launch = words['launch'][tracked]
            self._to_speed_form(launch, key)
            if command.startswith('speed'):
                speed = _natural(self.spec, launch['speed'], 'speed',
                                 f'{key}.speed')
                speed *= 2.0 if command.endswith('up') else 0.5
                launch['speed'] = _si_text(self.spec, speed, 'speed',
                                           'm/s')
            elif command.startswith('azimuth'):
                azimuth = float(np.degrees(_natural(
                    self.spec, launch['azimuth'], 'angle',
                    f'{key}.azimuth')))
                azimuth += (ANGLE_STEP_DEG if command.endswith('right')
                            else -ANGLE_STEP_DEG)
                launch['azimuth'] = f'{azimuth % 360.0!r} deg'
            else:
                elevation = float(np.degrees(_natural(
                    self.spec, launch['elevation'], 'angle',
                    f'{key}.elevation')))
                elevation += (ANGLE_STEP_DEG if command.endswith('up')
                              else -ANGLE_STEP_DEG)
                elevation = float(min(max(elevation, -90.0), 90.0))
                launch['elevation'] = f'{elevation!r} deg'
        try:
            new_spec = resolve(words, self.rc)
            new_store = build_store(new_spec, self.rc)
        except Exception as problem:               # noqa: BLE001
            # A run control that makes an impossible run (a launch
            # into the ground, a ring the stage refuses) is one line
            # and no change, never a dead window.
            print(f'note: {command}: {problem}', file=sys.stderr)
            return
        self.spec, self.store = new_spec, new_store
        self.panel_cache.clear()      # the images were of the old run
        self.state = transition(self.state, 'set_sample', self.store,
                                self.state.k)
        self.dirty = True

    def view_settings(self):
        """The `[view]` table the state amounts to."""
        state = self.state
        overlay = self.spec.view.overlay
        if 'overlay' in state.paths:
            overlay = 'on' if overlay == 'off' else overlay
        else:
            overlay = 'off'
        camera = dict(self.spec.view.camera)
        camera['follow'] = state.camera_mode == 'follow'
        return ViewSettings(
            palette=state.palette, views=state.view, arrows=state.arrows,
            ghost='ghost' in state.paths, check_path='check' in state.paths,
            overlay=overlay, triads='triads' in state.scenery,
            stage='stage' in state.scenery, panels=state.panels,
            legend=state.legend, arrow_scale=state.arrow_mode,
            tracked=state.tracked, camera=camera)

    def save(self):
        """Write the resolved run file with the view, next to the run,
        and say where."""
        path = Path(self.rc.output_dir) / f'{self.run_name}-resolved.toml'
        if write_resolved(self.spec, path, self.view_settings()):
            print(f'wrote {path}', file=sys.stderr)
        return path

    # -- drawing ----------------------------------------------------

    def frame_note(self):
        """The drawing rate over the last redraws, once there are
        two, so that a slow display is seen and not guessed."""
        if len(self.frame_stamps) < 2:
            return None
        span = self.frame_stamps[-1] - self.frame_stamps[0]
        if span <= 0.0:
            return None
        rate = (len(self.frame_stamps) - 1) / span
        split = ', '.join(f'{name} {1000.0 * seconds:.0f}'
                          for name, seconds in self.last_split.items())
        return (f'drawing {rate:.1f} frames/s '
                f'({1000.0 * self.last_frame_seconds:.0f} ms per frame: '
                f'{split})')

    def plotted_panel(self, name):
        """A plotted panel's image, drawn once per run, tracked
        particle, and palette, and kept (design 9.6)."""
        state = self.state
        key = (name, id(self.store), state.tracked, state.palette)
        if key not in self.panel_cache:
            self.panel_cache[key] = render_panel(name, self.store,
                                                 state.tracked, state.palette,
                                                 size=PANEL_SIZE)
        return self.panel_cache[key]

    def strip(self):
        """What the panel strip shows at this sample."""
        state = self.state
        sample = min(state.k, self.store.valid_samples(state.tracked) - 1)
        comparison = (None if self.store.comparison is None
                      else self.store.comparison[state.tracked])
        budget = budget_at(comparison, self.store.conserved[state.tracked],
                           self.spec.field, self.spec, sample,
                           self.scenes[-1].info)
        cursor = cursor_fraction(self.store, state.tracked, state.k)
        return Strip(images=[(self.plotted_panel(name), cursor)
                             for name in PLOTTED_PANELS],
                     lines=tuple(budget_lines(budget)))

    def redraw(self):
        """Draw the frame, timing its four parts for the frame note:
        describe, panels, actors, render (the last two from the
        renderer), so that a slow display says where its time goes."""
        started = time.perf_counter()
        state = self.state
        self.scenes = describe(self.store, self.spec, state, self.rc,
                               legend_lines() if state.legend else (),
                               self.frame_note())
        described = time.perf_counter()
        strip = self.strip() if state.panels else None
        panels_done = time.perf_counter()
        self.renderer.realize(self.scenes, state.palette, strip)
        self.renderer.set_slider(state.k)
        self.dirty = False
        finished = time.perf_counter()
        renderer_seconds = getattr(self.renderer, 'last_seconds', {})
        self.last_split = {'describe': described - started,
                           'panels': panels_done - described,
                           'actors': renderer_seconds.get('actors', 0.0),
                           'render': renderer_seconds.get('render', 0.0)}
        self.last_frame_seconds = finished - started
        self.frame_stamps.append(finished)

    def apply_cameras(self):
        """Place every view's camera as the run file says."""
        if not self.scenes:
            self.redraw()
        for index, scene in enumerate(self.scenes):
            self.renderer.set_camera(index, self.spec.view.camera,
                                     scene.info)

    def on_tick(self, tick_number):
        if self.redrawing:
            # A timer event that arrives while a frame is still being
            # drawn is dropped, never queued; the keys stay in the
            # controls' queue for the next tick.
            return
        self.redrawing = True
        try:
            for command, argument in self.controls.commands_at(tick_number):
                self.handle(command, argument)
            advanced = tick(self.state, self.store)
            if advanced != self.state:
                self.state = advanced
                self.dirty = True
            if self.dirty:
                self.redraw()
        finally:
            self.redrawing = False
        if self.controls.wants_to_stop():
            self.renderer.stop()


def run_session(spec, store, rc, controls, renderer, run_name='run'):
    """Run until the controls want to stop; return the final state.
    With window controls the renderer's timer drives the ticks and
    `interactive` blocks; with a script the loop is here."""
    session = Session(spec, store, rc, controls, renderer, run_name)
    session.redraw()
    session.apply_cameras()
    if isinstance(controls, VedoControls):
        renderer.on_tick(session.on_tick, TICK_MILLISECONDS)
        renderer.interactive()
    else:
        tick_number = 0
        while not controls.wants_to_stop():
            session.on_tick(tick_number)
            tick_number += 1
    return session.state
