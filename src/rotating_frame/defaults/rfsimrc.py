#!/usr/bin/env python3

"""Resource-control defaults for rfsim.

This file holds the MACHINE-LOCAL settings of the interactive tool:
things that depend on the computer, the display, or personal taste,
and that never affect a computed result. Physics defaults are not
here; they live in the run-file schema (`rotating_frame.run.run_file`) so
that a run file is self-contained (physdemo ARCHITECTURE 5).

It is looked up first in the current working directory, then in
$ROTATING_FRAME_RC, then here, inside the package. A user who wants a bigger
window or a dark palette by default runs `rfsim --write-rc`, which
copies this file into the working directory, and edits the copy;
nobody needs to know where the package is.

This file has no main() and is never run as an entry point, so it
does not log to `command` the way rfsim does.
"""


def parameters_and_defaults():
    """Return the dictionary of rc settings. Every key here is one
    the command reads; a misspelled key is simply never read, so
    keep the spelling of the shipped copy."""

    param_dict = {
        # Window size in pixels, (width, height).
        'window_size': [960, 720],

        # Palette used when a run file does not name one; see
        # rotating_frame.render.palettes for the names.
        'default_palette': 'light',

        # Radius of the moving glyph, in scene units.
        'glyph_radius': 0.05,

        # Where screenshots go.
        'output_dir': '.',
    }

    return param_dict


if __name__ == '__main__':
    # Running this file directly prints the defaults, which is a
    # convenient way to check what rfsim will start from.
    print(parameters_and_defaults())
