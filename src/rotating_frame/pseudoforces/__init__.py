"""The three pseudo-force terms, written once (pseudocode 5; design
5; ARCHITECTURE 3.5). Imported by the rotating-frame equation of
`motion/` and by the results store of `run/`, which is what makes the
arrows a student sees and the equation the check integrates the same
terms. Imports `core/` and nothing else.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from rotating_frame.pseudoforces.terms import (TERM_NAMES, stacked,
                                               terms, total)

__all__ = ['TERM_NAMES', 'stacked', 'terms', 'total']
