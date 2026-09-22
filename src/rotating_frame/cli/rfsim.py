"""rfsim -- the interactive Rotating Frame tool.

Loads a run file, computes the run, and opens a vedo window showing
it. Settings arrive from three places, each overriding the one
before: the resource-control file rfsimrc.py (machine-local, never
physics), the run file (self-contained physics), and --set overrides
on the command line. Every run is appended to a `command` file in the
working directory so the exact call can be recovered later.

    rfsim --check                 can this computer run and draw it?
    rfsim circle                  a packaged example, by bare name
    rfsim --examples              copy the example run files here
    rfsim circle.toml             your own (edited) copy
    rfsim circle.toml --set motion.n_steps=400
    rfsim circle.toml --offscreen --frames 5 --screenshot out.png
    rfsim --write-rc              copy the rc defaults here, to edit
"""

# WHERE THIS CODE LIVES, AND WHY. This module is the body of the
# `rfsim` command. It is inside the package, not in src/scripts/,
# because the command is reached in two ways that must run the same
# code (physdemo contract C5): the executable src/scripts/rfsim.py,
# which the physdemo suite links and a clone runs directly; and the
# console script that `pip install` creates from pyproject.toml, which
# calls console_main() below. The docstring above is the --help text.
# Governed by physdemo PSEUDOCODE 4.7 until this tool's own session
# section takes it over (dev/PSEUDOCODE.md, row 0).

import argparse
import sys

from rotating_frame.cli.support import (copy_examples, copy_rc_file,
                                 load_rc_defaults, locate_run_file,
                                 record_command, self_check)
from rotating_frame.core.motion import circular_motion_samples
from rotating_frame.render.palettes import PALETTE_NAMES
from rotating_frame.run import RunFileError, load_run_file

COMMAND_NAME = 'rfsim'
RC_FILENAME = 'rfsimrc.py'

# The packages `--check` reports on: the ones this tool imports, by
# the names `pip` knows them by. pyproject.toml declares the same set
# (minus the Python 3.10 TOML backport), and a test keeps the two in
# agreement. It lives here and not in support.py because it differs
# per tool and the shared module must not.
CHECKED_DISTRIBUTIONS = ('numpy', 'vedo', 'vtk')

# The fallback of last resort, so that a damaged installation still
# starts; the shipped defaults/rfsimrc.py is the documented source.
BUILTIN_RC = {'window_size': [960, 720], 'default_palette': 'light',
              'glyph_radius': 0.05, 'output_dir': '.'}


def parse_command_line(command_line_args=None):
    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        epilog=f'Defaults are given in ./{RC_FILENAME} or '
               f'$ROTATING_FRAME_RC/{RC_FILENAME}; --write-rc makes the first.')
    parser.add_argument('runfile', nargs='?', default=None,
                        help='TOML run file, or the bare name of a '
                             'packaged example')
    parser.add_argument('--set', dest='overrides', action='append',
                        default=[], metavar='TABLE.KEY=VALUE',
                        help='override one run-file key; repeatable')
    parser.add_argument('--offscreen', action='store_true',
                        help='render without a window')
    parser.add_argument('--frames', type=int, default=0,
                        help='draw N frames, then exit')
    parser.add_argument('--screenshot', default=None,
                        help='write an image after the last frame')
    parser.add_argument('--palette', default=None,
                        choices=PALETTE_NAMES,
                        help='override [view].palette')
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
    if args.offscreen and not args.frames:
        # A window nobody can see would wait forever to be closed;
        # refuse before any work.
        parser.error('--offscreen needs --frames N so that the run '
                     'knows when to stop')
    return args


def run_offscreen(run_file_path, frames):
    """Run `run_file_path` for `frames` frames offscreen and return the
    last frame as an array. This is the ordinary code path, used by
    `--check` so that the self-check tests what a run does."""
    resolved = load_run_file(run_file_path)
    rc = load_rc_defaults(RC_FILENAME, BUILTIN_RC)
    samples = circular_motion_samples(**resolved['motion'])
    # Imported here, after prepare_offscreen() has run in the caller.
    from rotating_frame.render.vedo_renderer import TrailRenderer
    renderer = TrailRenderer(resolved['view']['palette'], (640, 480),
                             offscreen=True,
                             glyph_radius=rc['glyph_radius'])
    renderer.run(samples, frames)
    image = renderer.screenshot(as_array=True)
    renderer.close()
    return image


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
    # A run file that is missing or wrong is the commonest mistake a
    # student makes; it earns a message and status 2, not a traceback.
    try:
        runfile = locate_run_file(args.runfile, COMMAND_NAME)
        rc = load_rc_defaults(RC_FILENAME, BUILTIN_RC)
        resolved = load_run_file(runfile, overrides)
        if resolved['view']['palette'] not in PALETTE_NAMES:
            raise RunFileError(f'view.palette must be one of '
                               f'{", ".join(PALETTE_NAMES)}')
        samples = circular_motion_samples(**resolved['motion'])
    except (RunFileError, FileNotFoundError, ValueError) as problem:
        print(f'{COMMAND_NAME}: {problem}', file=sys.stderr)
        return 2

    # Imported here so that `--help` and a run-file error never pay
    # for VTK's import, which is slow on a shared filesystem.
    from rotating_frame.render.offscreen import prepare_offscreen
    if args.offscreen:
        # Before the renderer (and so VTK) is imported; this also
        # covers a DISPLAY that is set but dead.
        prepare_offscreen()
    from rotating_frame.render.vedo_renderer import TrailRenderer
    renderer = TrailRenderer(resolved['view']['palette'],
                             rc['window_size'], offscreen=args.offscreen,
                             glyph_radius=rc['glyph_radius'])
    renderer.run(samples, args.frames)
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
