"""The visual encodings a run file may name (pseudocode 9.4; design
9.5).

Three palettes, light, dark, and colorblind, each a complete map
from role to color, with the same roles in each. Colors are the
second channel: every arrow carries its word, every extra path has a
style and a label, the tracked particle is larger and labeled, the
two triads differ by primes, and the two views are titled, so that
no distinction carrying meaning rests on color alone (VISION P6).
This module imports nothing from vedo so that a palette name can be
checked before VTK is imported.

The colorblind palette's arrow colors are the six of the Okabe-Ito
set (black, orange, sky blue, bluish green, blue, vermilion) that
stay farthest apart under simulated protanopia and deuteranopia,
which `tests/unit/test_palettes.py` checks; its trail cycle is a
categorical set of twelve.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
role list and the redundancy rule follow the scattering tool's
design section 11.
"""

TRAIL_CYCLE = 12

ROLES = ('background', 'text', 'inertial_axes', 'rotating_axes',
         'local_axes', 'stage', 'stage_marks', 'floor', 'check', 'ghost',
         'overlay', 'true', 'centrifugal', 'coriolis', 'euler', 'sum',
         'velocity', 'glyph', 'tracked_glyph') \
    + tuple(f'trail_{index}' for index in range(TRAIL_CYCLE))

_LIGHT_TRAILS = ['#1f77b4', '#d62728', '#2ca02c', '#9467bd', '#ff7f0e',
                 '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#7f7f7f',
                 '#393b79', '#843c39']
_DARK_TRAILS = ['#6baed6', '#fb6a4a', '#74c476', '#bcbddc', '#fdae6b',
                '#c49c94', '#f7b6d2', '#9edae5', '#dbdb8d', '#c7c7c7',
                '#9c9ede', '#e7969c']
_COLORBLIND_TRAILS = ['#0072b2', '#e69f00', '#009e73', '#cc79a7', '#56b4e9',
                      '#d55e00', '#f0e442', '#000000', '#999999',
                      '#332288', '#88ccee', '#aa4499']


def _with_trails(colors, trails):
    palette = dict(colors)
    for index, color in enumerate(trails):
        palette[f'trail_{index}'] = color
    return palette


PALETTES = {
    'light': _with_trails({
        'background': 'white', 'text': 'black',
        'inertial_axes': 'dimgray', 'rotating_axes': 'darkorange',
        'local_axes': 'darkorange', 'stage': 'lightsteelblue',
        'stage_marks': 'steelblue', 'floor': 'silver',
        'check': 'crimson', 'ghost': 'gray', 'overlay': 'seagreen',
        'true': 'black', 'centrifugal': 'darkorange',
        'coriolis': 'royalblue', 'euler': 'purple', 'sum': 'firebrick',
        'velocity': 'darkgreen', 'glyph': 'tomato',
        'tracked_glyph': 'red'}, _LIGHT_TRAILS),
    'dark': _with_trails({
        'background': 'black', 'text': 'white',
        'inertial_axes': 'lightgray', 'rotating_axes': 'orange',
        'local_axes': 'orange', 'stage': 'slategray',
        'stage_marks': 'lightsteelblue', 'floor': 'dimgray',
        'check': 'salmon', 'ghost': 'darkgray', 'overlay': 'lightgreen',
        'true': 'white', 'centrifugal': 'orange', 'coriolis': 'deepskyblue',
        'euler': 'violet', 'sum': 'lightcoral', 'velocity': 'palegreen',
        'glyph': 'gold', 'tracked_glyph': 'yellow'}, _DARK_TRAILS),
    'colorblind': _with_trails({
        'background': 'white', 'text': 'black',
        'inertial_axes': '#555555', 'rotating_axes': '#e69f00',
        'local_axes': '#e69f00', 'stage': '#dddddd', 'stage_marks': '#999999',
        'floor': '#cccccc', 'check': '#d55e00', 'ghost': '#777777',
        'overlay': '#009e73', 'true': '#000000', 'centrifugal': '#e69f00',
        'coriolis': '#0072b2', 'euler': '#56b4e9', 'sum': '#d55e00',
        'velocity': '#009e73', 'glyph': '#cc79a7',
        'tracked_glyph': '#f0e442'}, _COLORBLIND_TRAILS),
}

PALETTE_NAMES = tuple(PALETTES)


def color(palette_name, role):
    """The color of `role` in `palette_name`."""
    return PALETTES[palette_name][role]
