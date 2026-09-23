"""Verifies pseudocode 9.7 for `render/palettes.py`: every palette
has every role, and the colorblind palette's arrow colors are
pairwise distinguishable under the two common deficiencies, by a
fixed simulation table."""

import numpy as np

from rotating_frame.render.palettes import (PALETTE_NAMES, PALETTES, ROLES,
                                            color)

ARROW_ROLES = ('true', 'centrifugal', 'coriolis', 'euler', 'sum',
               'velocity')

# Simulated deficiency: linear maps on RGB in [0, 1], the Machado 2009
# matrices at full severity, as the scattering tool uses.
PROTANOPIA = np.array([[0.152286, 1.052583, -0.204868],
                       [0.114503, 0.786281, 0.099216],
                       [-0.003882, -0.048116, 1.051998]])
DEUTERANOPIA = np.array([[0.367322, 0.860646, -0.227968],
                         [0.280085, 0.672501, 0.047413],
                         [-0.011820, 0.042940, 0.968881]])


def rgb(name):
    from matplotlib.colors import to_rgb
    return np.array(to_rgb(name))


def test_every_palette_has_every_role():
    assert set(PALETTE_NAMES) == {'light', 'dark', 'colorblind'}
    for name, palette in PALETTES.items():
        assert set(palette) == set(ROLES), name
        for role in ROLES:
            assert color(name, role)


def test_colorblind_arrows_are_distinguishable_under_deficiency():
    colors = np.array([rgb(color('colorblind', role)) for role in
                       ARROW_ROLES])
    for matrix in (PROTANOPIA, DEUTERANOPIA, np.eye(3)):
        seen = np.clip(colors @ matrix.T, 0.0, 1.0)
        for i in range(len(seen)):
            for j in range(i + 1, len(seen)):
                assert np.linalg.norm(seen[i] - seen[j]) > 0.2, \
                    (ARROW_ROLES[i], ARROW_ROLES[j])
