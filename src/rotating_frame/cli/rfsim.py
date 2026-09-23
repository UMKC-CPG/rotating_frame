"""rfsim -- pseudo-forces in a rotating frame, on screen.

Loads a run file, computes the run, and opens a window with two
views of it: the inertial frame, where the stage turns and the path
is what the true force alone makes; and the rotating frame, where the
stage stands still and the path bends under the centrifugal,
Coriolis, and Euler terms, each drawn as a labeled arrow. Settings
arrive from three places, each overriding the one before: the
resource-control file rfsimrc.py (machine-local, never physics), the
run file (self-contained physics), and --set overrides on the
command line. Every run is appended to a `command` file in the
working directory so the exact call can be recovered later.

    rfsim --check                 can this computer run and draw it?
    rfsim turntable               a packaged example, by bare name
    rfsim --examples              copy the example run files here
    rfsim earth_drop.toml         your own (edited) copy
    rfsim earth_drop.toml --set frame.exaggeration=100
    rfsim earth_throw --view rotating --palette dark
    rfsim turntable --offscreen --frames 5 --screenshot out.png
    rfsim turntable --offscreen --script "5:play_pause,40:reverse"
    rfsim earth_drop --write-resolved drop-resolved.toml
    rfsim --write-rc              copy the rc defaults here, to edit

In the window, every key is a Ctrl chord; Ctrl+h shows the legend.
"""

# WHERE THIS CODE LIVES, AND WHY. This module is the body of the
# `rfsim` command. It is inside the package, not in src/scripts/,
# because the command is reached in two ways that must run the same
# code (physdemo contract C5): the executable src/scripts/rfsim.py,
# which the physdemo suite links and a clone runs directly; and the
# console script that `pip install` creates from pyproject.toml, which
# calls console_main() below. The docstring above is the --help text.
# Governed by this tool's pseudocode 10.5; the seams from the
# skeleton's version are listed in pseudocode 10.6.

import argparse
import sys

from rotating_frame.cli.support import (copy_examples, copy_rc_file,
                                        locate_run_file, record_command,
                                        self_check)
from rotating_frame.core.units import UnitsError
from rotating_frame.render.palettes import PALETTE_NAMES
from rotating_frame.run import (RC_FILENAME, RunFileError, build_store,
                                estimate_bytes, load_rc, load_run_file,
                                write_resolved)
from rotating_frame.ui.session_state import VIEWS

COMMAND_NAME = 'rfsim'

# The packages `--check` reports on: the ones this tool imports, by
# the names `pip` knows them by. pyproject.toml declares the same set
# (minus the Python 3.10 TOML backport), and a test keeps the two in
# agreement. It lives here and not in support.py because it differs
# per tool and the shared module must not.
CHECKED_DISTRIBUTIONS = ('numpy', 'scipy', 'matplotlib', 'vedo', 'vtk',
                         'pint', 'tomli_w')


def parse_command_line(command_line_args=None):
    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        epilog=f'Defaults are given in ./{RC_FILENAME} or '
               f'$ROTATING_FRAME_RC/{RC_FILENAME}; --write-rc makes the '
               'first.')
    parser.add_argument('runfile', nargs='?', default=None,
                        help='TOML run file, or the bare name of a '
                             'packaged example')
    parser.add_argument('--set', dest='overrides', action='append',
                        default=[], metavar='TABLE.KEY=VALUE',
                        help='override one run-file key; repeatable '
                             '(launch[0].speed addresses a launch)')
    parser.add_argument('--offscreen', action='store_true',
                        help='render without a window')
    parser.add_argument('--frames', type=int, default=0, metavar='N',
                        help='run N ticks from the initial state, then '
                             'exit')
    parser.add_argument('--script', default=None,
                        metavar='"TICK:COMMAND,..."',
                        help='commands to issue at ticks, as the keys '
                             'would (e.g. "5:play_pause,40:reverse")')
    parser.add_argument('--screenshot', default=None, metavar='PATH',
                        help='write an image after the last frame')
    parser.add_argument('--palette', default=None, choices=PALETTE_NAMES,
                        help='override [view].palette')
    parser.add_argument('--view', default=None, choices=VIEWS,
                        help='override [view].views')
    parser.add_argument('--write-resolved', default=None, metavar='PATH',
                        help='write the resolved run file and exit '
                             'without drawing')
    parser.add_argument('--examples', nargs='?', const='.', default=None,
                        metavar='DIR',
                        help='copy the packaged example run files into '
                             'DIR (default: here) and exit; never '
                             'overwrites')
    parser.add_argument('--write-rc', action='store_true',
                        help=f'copy the shipped {RC_FILENAME} here, to '
                             'edit, and exit')
    parser.add_argument('--check', action='store_true',
                        help='check that this computer can run and draw '
                             'the tool, and exit')
    args = parser.parse_args(command_line_args)
    # Exactly one thing to do: a run, or one utility.
    requested = [args.runfile is not None, args.examples is not None,
                 args.write_rc, args.check]
    if sum(requested) != 1:
        parser.error('give a run file, or exactly one of --examples, '
                     '--write-rc, --check')
    if args.offscreen and not (args.frames or args.script
                               or args.write_resolved):
        # A window nobody can see would wait forever to be closed;
        # refuse before any work.
        parser.error('--offscreen needs --frames N or --script so that '
                     'the run knows when to stop')
    return args


def _controls_for(args, store, renderer):
    """The scripted source for --frames or --script, else the
    window's keys and slider."""
    from rotating_frame.ui import ScriptedControls, VedoControls
    from rotating_frame.ui.vedo_controls import parse_script
    if args.script is not None or args.frames:
        script = parse_script(args.script)
        frames = args.frames or (max(when for when, _, _ in script) + 2
                                 if script else 1)
        return ScriptedControls(script, frames)
    return VedoControls(renderer, store.n_samples, COMMAND_NAME)


def _run(spec, store, rc, offscreen, controls_factory, window_size,
         run_name):
    """Open the renderer, run the session, return the renderer for a
    screenshot. Imported here so that `--help` and a run-file error
    never pay for VTK's import, which is slow on a shared
    filesystem."""
    from rotating_frame.render.vedo_renderer import TwoViewRenderer
    from rotating_frame.ui import run_session
    n_views = 2 if spec.view.views == 'both' else 1
    renderer = TwoViewRenderer(window_size, offscreen, n_views,
                               spec.view.palette, COMMAND_NAME,
                               with_panels=spec.view.panels)
    controls = controls_factory(store, renderer)
    run_session(spec, store, rc, controls, renderer, run_name)
    return renderer


def run_offscreen(run_file_path, frames):
    """Run `run_file_path` for `frames` ticks offscreen and return the
    last frame as an array. This is the ordinary code path, used by
    `--check` so that the self-check tests what a run does."""
    from rotating_frame.ui import ScriptedControls
    rc = load_rc()
    spec = load_run_file(run_file_path, ['run.samples=100'], rc)
    store = build_store(spec, rc)
    renderer = _run(spec, store, rc, True,
                    lambda store, renderer: ScriptedControls([], frames),
                    (640, 480), 'check')
    image = renderer.screenshot(as_array=True)
    renderer.close()
    return image


def _progress_bar(particle, count):
    """One line, rewritten, while a ring of many members is built."""
    if count >= 8:
        print(f'\rcomputing {particle + 1}/{count} particles',
              end='' if particle + 1 < count else '\n', file=sys.stderr)


def main(command_line_args=None):
    """Run the tool. Accepting an argument list lets the test suite
    drive this without touching sys.argv."""
    args = parse_command_line(command_line_args)
    if args.examples is not None:
        return copy_examples(args.examples, COMMAND_NAME)
    if args.write_rc:
        return copy_rc_file(RC_FILENAME, '.', COMMAND_NAME)
    if args.check:
        return self_check(run_offscreen, COMMAND_NAME,
                          CHECKED_DISTRIBUTIONS)

    overrides = list(args.overrides)
    if args.palette:
        overrides.append(f'view.palette="{args.palette}"')
    if args.view:
        overrides.append(f'view.views="{args.view}"')
    # A run file that is missing or wrong is the commonest mistake a
    # student makes; it earns a message and status 2, not a traceback.
    try:
        runfile = locate_run_file(args.runfile, COMMAND_NAME)
        rc = load_rc()
        spec = load_run_file(runfile, overrides, rc)
        estimate = estimate_bytes(len(spec.launches), spec.samples)
        print(f'{len(spec.launches)} particle(s) x {spec.samples} samples: '
              f'about {estimate / 1e6:.1f} MB', file=sys.stderr)
        if args.write_resolved:
            return 0 if write_resolved(spec, args.write_resolved) else 1
        if args.script is not None:
            from rotating_frame.ui.vedo_controls import parse_script
            parse_script(args.script)            # refuse before the work
        store = build_store(spec, rc, progress=_progress_bar)
    except (RunFileError, UnitsError, FileNotFoundError,
            ValueError) as problem:
        print(f'{COMMAND_NAME}: {problem}', file=sys.stderr)
        return 2

    if args.offscreen:
        # Before the renderer (and so VTK) is imported; this also
        # covers a DISPLAY that is set but dead.
        from rotating_frame.render.offscreen import prepare_offscreen
        prepare_offscreen()
    renderer = _run(spec, store, rc, args.offscreen,
                    lambda store, renderer: _controls_for(args, store,
                                                          renderer),
                    tuple(rc.window_size), runfile.stem)
    if args.screenshot:
        # A side-effect write that fails is one line, never a
        # traceback, and never undoes the run (physdemo contract C16).
        try:
            renderer.screenshot(args.screenshot)
        except OSError as problem:
            print(f'note: cannot write {args.screenshot} '
                  f'({problem.strerror})', file=sys.stderr)
    renderer.close()
    return 0


def console_main():
    """The front that `pip install` creates (pyproject.toml,
    [project.scripts]). It is the real entry point on that route, so
    it is where the invocation is logged; main() itself never logs."""
    record_command()
    sys.exit(main())
