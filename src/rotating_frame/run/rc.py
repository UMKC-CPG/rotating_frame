"""The rc file: what is machine-local and never affects a result
(pseudocode 8.2; design 8.3; ARCHITECTURE 7).

Window size, palette, arrow and glyph sizes, the store's memory cap,
the output directory. Looked for in the working directory, then in
`$ROTATING_FRAME_RC`, then inside the package, through the inherited
`cli/support.py`. Every key that can change a trajectory, an arrow,
or the comparison lives in the run file instead.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import sys
from dataclasses import dataclass

from rotating_frame.cli.support import load_rc_defaults

RC_FILENAME = 'rfsimrc.py'

BUILTIN_RC = {'window_size': [1280, 800], 'default_palette': 'light',
              'arrow_scale': 1.0, 'glyph_radius': 0.02, 'trail_width': 2,
              'max_store_bytes': 500_000_000, 'output_dir': '.'}


@dataclass(frozen=True)
class RcSettings:
    """The rc keys, resolved."""

    window_size: tuple
    default_palette: str
    arrow_scale: float
    glyph_radius: float
    trail_width: int
    max_store_bytes: int
    output_dir: str


def load_rc(search_path=None):
    """The rc settings from the first rc file found, with the built-in
    defaults behind them; an unknown key is dropped with a note."""
    values = load_rc_defaults(RC_FILENAME, BUILTIN_RC, search_path)
    unknown = sorted(set(values) - set(BUILTIN_RC))
    if unknown:
        print(f'note: {RC_FILENAME} has keys this tool does not read, '
              f'ignored: {", ".join(unknown)}', file=sys.stderr)
    merged = {**BUILTIN_RC, **{name: values[name] for name in BUILTIN_RC
                               if name in values}}
    merged['window_size'] = tuple(merged['window_size'])
    return RcSettings(**merged)
