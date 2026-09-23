"""The resolved run: plain data, every physical value a dimensionless
number, plus the scale factors for the way back and the run file's
own words for the write-back (pseudocode 8.3; design 8.4).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ViewSettings:
    """The [view] table, resolved (design 8.1)."""

    palette: str
    views: str
    arrows: frozenset
    ghost: bool
    check_path: bool
    overlay: str
    triads: bool
    stage: bool
    panels: bool
    legend: bool
    arrow_scale: str
    tracked: int
    camera: dict


@dataclass(frozen=True)
class RunSpec:
    """One run, resolved. The frame has rate one because the core
    works in natural units; the presets' SI arithmetic happened
    before scaling."""

    preset: object
    frame: object
    scales: object
    latitude: object
    axes: object
    field: object
    launches: list
    ring: object
    duration: float
    stop: str
    samples: int
    method: str
    check: object
    view: ViewSettings
    exaggeration: float
    overlay_note: object
    words: dict
    version: str
