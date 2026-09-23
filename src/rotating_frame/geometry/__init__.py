"""Derived display geometry: what the constructions are, in scene
coordinates, computed from the store and the frame, and drawn by
nobody here (pseudocode 9.2; design 9.3; ARCHITECTURE 3.8). Imports
`core/` only, and never `motion/` (ARCHITECTURE 6.1).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from rotating_frame.geometry.frame_axes import moving_triad, triads
from rotating_frame.geometry.stage import stage_surface
from rotating_frame.geometry.trails import extra_trails, trail

__all__ = ['moving_triad', 'triads', 'stage_surface', 'extra_trails',
           'trail']
