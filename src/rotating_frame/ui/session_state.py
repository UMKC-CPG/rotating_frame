"""The scrubber's state and its pure transitions (pseudocode 10.1;
design 10.2 and 10.3).

Every viewing command is a function from a state to a state, with no
window in sight, so that the whole keyboard can be tested without
one and a scripted session produces exactly the frames a student's
keys would. Pacing is by ticks: one tick advances `rate` samples in
the current direction, whatever the wall clock does, so that "slow
motion" is a property of the run and not of the computer (design
10.8).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
state machine follows the scattering tool's `ui/session_state.py`.
"""

from dataclasses import dataclass, replace

from rotating_frame.render.palettes import PALETTE_NAMES

RATES = (1, 2, 4, 8, 16)
VIEWS = ('both', 'inertial', 'rotating')
ARROW_NAMES = ('true', 'centrifugal', 'coriolis', 'euler', 'sum',
               'velocity')
PATH_NAMES = ('check', 'ghost', 'overlay')
SCENERY_NAMES = ('triads', 'stage')

VIEWING_COMMANDS = (
    'play_pause', 'step_forward', 'step_back', 'faster', 'slower',
    'normal', 'reverse', 'jump_start', 'jump_end', 'jump_event', 'loop',
    'next_tracked', 'toggle_all_arrows', 'toggle_arrow_true',
    'toggle_arrow_centrifugal', 'toggle_arrow_coriolis',
    'toggle_arrow_euler', 'toggle_arrow_sum', 'toggle_arrow_velocity',
    'toggle_ghost', 'toggle_check', 'toggle_overlay', 'toggle_triads',
    'toggle_stage', 'toggle_camera_mode', 'toggle_arrow_mode',
    'toggle_panels', 'toggle_legend', 'cycle_view', 'cycle_palette',
    'reset_camera', 'set_sample')
RUN_COMMANDS = ('exaggeration_up', 'exaggeration_down', 'substeps_up',
                'substeps_down', 'speed_up', 'speed_down', 'azimuth_right',
                'azimuth_left', 'elevation_up', 'elevation_down')
OTHER_COMMANDS = ('save', 'quit')


@dataclass(frozen=True)
class SessionState:
    """Everything the scrubber remembers (design 10.2)."""

    k: int = 0                        # the shown sample
    playing: bool = False
    direction: int = 1                # +1 forward, -1 back
    rate: int = 1                     # samples per tick
    loop: bool = False
    view: str = 'both'
    arrows: frozenset = frozenset(ARROW_NAMES)
    paths: frozenset = frozenset()
    scenery: frozenset = frozenset(SCENERY_NAMES)
    panels: bool = True
    legend: bool = True
    palette: str = 'light'
    tracked: int = 0
    camera_mode: str = 'follow'       # follow | fixed
    arrow_mode: str = 'auto'          # auto | same


def initial_state(spec):
    """The state the run file's `[view]` table asks for."""
    view = spec.view
    paths = set()
    if view.ghost:
        paths.add('ghost')
    if view.check_path:
        paths.add('check')
    if view.overlay != 'off':
        paths.add('overlay')
    scenery = set()
    if view.triads:
        scenery.add('triads')
    if view.stage:
        scenery.add('stage')
    return SessionState(
        k=0, playing=False, direction=1, rate=1, loop=False,
        view=view.views, arrows=frozenset(view.arrows),
        paths=frozenset(paths), scenery=frozenset(scenery),
        panels=view.panels, legend=view.legend, palette=view.palette,
        tracked=view.tracked,
        camera_mode='follow' if view.camera.get('follow', True) else 'fixed',
        arrow_mode=view.arrow_scale)


def _toggled(members, name):
    return frozenset(members ^ {name})


def _cycled(sequence, current):
    return sequence[(sequence.index(current) + 1) % len(sequence)]


def transition(state, command, store, argument=None):
    """The state after one viewing command. A run command, `save`, or
    `quit` returns the state unchanged: the session handles those."""
    last = store.n_samples - 1
    if command == 'play_pause':
        return replace(state, playing=not state.playing)
    if command == 'step_forward':
        return replace(state, k=min(state.k + 1, last), playing=False)
    if command == 'step_back':
        return replace(state, k=max(state.k - 1, 0), playing=False)
    if command == 'faster':
        index = min(RATES.index(state.rate) + 1, len(RATES) - 1)
        return replace(state, rate=RATES[index])
    if command == 'slower':
        index = max(RATES.index(state.rate) - 1, 0)
        return replace(state, rate=RATES[index])
    if command == 'normal':
        return replace(state, rate=1)
    if command == 'reverse':
        return replace(state, direction=-state.direction)
    if command == 'jump_start':
        return replace(state, k=0)
    if command == 'jump_end':
        return replace(state, k=last)
    if command == 'jump_event':
        stop = store.stop_of(state.tracked)
        return replace(state, k=last if stop is None else stop.index)
    if command == 'loop':
        return replace(state, loop=not state.loop)
    if command == 'next_tracked':
        return replace(state,
                       tracked=(state.tracked + 1) % store.n_particles)
    if command == 'toggle_all_arrows':
        full = state.arrows == frozenset(ARROW_NAMES)
        return replace(state, arrows=frozenset() if full
                       else frozenset(ARROW_NAMES))
    if command.startswith('toggle_arrow_'):
        return replace(state, arrows=_toggled(state.arrows,
                                              command[len('toggle_arrow_'):]))
    if command in ('toggle_ghost', 'toggle_check', 'toggle_overlay'):
        return replace(state, paths=_toggled(state.paths,
                                             command[len('toggle_'):]))
    if command in ('toggle_triads', 'toggle_stage'):
        return replace(state, scenery=_toggled(state.scenery,
                                               command[len('toggle_'):]))
    if command == 'toggle_camera_mode':
        return replace(state, camera_mode='fixed'
                       if state.camera_mode == 'follow' else 'follow')
    if command == 'toggle_arrow_mode':
        return replace(state, arrow_mode='same'
                       if state.arrow_mode == 'auto' else 'auto')
    if command == 'toggle_panels':
        return replace(state, panels=not state.panels)
    if command == 'toggle_legend':
        return replace(state, legend=not state.legend)
    if command == 'cycle_view':
        return replace(state, view=_cycled(VIEWS, state.view))
    if command == 'cycle_palette':
        return replace(state, palette=_cycled(PALETTE_NAMES, state.palette))
    if command == 'reset_camera':
        return state
    if command == 'set_sample':
        wanted = int(argument) if argument is not None else state.k
        return replace(state, k=min(max(wanted, 0), last), playing=False)
    if command in RUN_COMMANDS or command in OTHER_COMMANDS:
        return state
    raise ValueError(f'unknown command {command!r}')


def tick(state, store):
    """One tick of the clock: advance `rate` samples in the current
    direction; at an end, wrap when looping, else stop and hold."""
    if not state.playing:
        return state
    n = store.n_samples
    k = state.k + state.direction * state.rate
    if 0 <= k < n:
        return replace(state, k=k)
    if state.loop:
        return replace(state, k=k % n)
    return replace(state, k=min(max(k, 0), n - 1), playing=False)
