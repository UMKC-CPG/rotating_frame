"""The visual encodings a run file may name (physdemo PSEUDOCODE 4.6).

A palette maps each thing drawn to a color. Light and dark are the
minimum; a tool adds a color-blind-safe palette and whatever its
scene needs, and keeps the rule that no distinction carrying meaning
rests on color alone. This module imports nothing from vedo so that
the command can validate a palette name before the renderer, and so
VTK, is imported.

Attribution: this module is part of the Rotating Frame teaching tool.
"""

PALETTES = {
    'light': {'background': 'white', 'trail': 'steelblue',
              'glyph': 'tomato'},
    'dark': {'background': 'black', 'trail': 'lightblue',
             'glyph': 'orange'},
}

PALETTE_NAMES = tuple(PALETTES)
