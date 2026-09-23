#!/usr/bin/env python3

"""Resource-control defaults for rfsim (pseudocode 8.2; design 8.3).

This file holds the MACHINE-LOCAL settings of the interactive tool:
things that depend on the computer, the display, or personal taste,
and that never affect a computed result. Physics defaults are not
here; they live in the run-file schema (`rotating_frame.run.schema`)
so that a run file is self-contained (physdemo ARCHITECTURE 5).

It is looked up first in the current working directory, then in
$ROTATING_FRAME_RC, then here, inside the package. A user who wants a
bigger window or a dark palette by default runs `rfsim --write-rc`,
which copies this file into the working directory, and edits the
copy; nobody needs to know where the package is.

This file has no main() and is never run as an entry point, so it
does not log to `command` the way rfsim does.
"""


def parameters_and_defaults():
    """Return the dictionary of rc settings. Every key here is one
    the command reads; a misspelled key is reported once and never
    read, so keep the spelling of the shipped copy."""

    param_dict = {
        # Window size in pixels, (width, height): two views side by
        # side and the panel strip along the bottom.
        'window_size': [1280, 800],

        # Palette used when a run file does not name one; see
        # rotating_frame.render.palettes for the names.
        'default_palette': 'light',

        # A factor on every arrow's length, for a small screen or a
        # projector; the stated arrow ratio is unaffected.
        'arrow_scale': 1.0,

        # Radius of a particle's glyph, as a fraction of the scene's
        # extent; the tracked particle is drawn larger.
        'glyph_radius': 0.02,

        # Width of the trails, in pixels.
        'trail_width': 2,

        # The largest results store the tool will build, in bytes; a
        # run that needs more is refused with its size named.
        'max_store_bytes': 500_000_000,

        # Where screenshots and saved run files go.
        'output_dir': '.',
    }

    return param_dict


if __name__ == '__main__':
    # Running this file directly prints the defaults, which is a
    # convenient way to check what rfsim will start from.
    print(parameters_and_defaults())
