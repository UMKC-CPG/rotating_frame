"""Three kinds of error, never combined (pseudocode 6.5; design 6.4).

The screen's error panel has three columns, and nothing is added
across them: the numerical column holds the check's error and the
conserved quantities' drift; the approximation column holds the
field's declared estimate, on the Earth the uniform-gravity error;
the distortion column holds the exaggeration factor, the arrow-scale
ratio, and whether the camera follows. They have different causes
and different remedies, and a single number would let a large
labeled exaggeration hide a small numerical failure, or the reverse
(VISION P3, P12). A test parses every module under `analysis/` and
`render/` and asserts that no arithmetic combines two columns.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass

COLUMN_NAMES = ('numerical', 'approximation', 'distortion')


@dataclass(frozen=True)
class ErrorBudget:
    """The three columns at one sample, as dictionaries the panel
    prints; `approximation` is None for a field that approximates
    nothing."""

    numerical: dict
    approximation: object
    distortion: dict


def budget_at(comparison, conserved, field, spec, k, scene_info):
    """Fill the three columns from their three sources at sample `k`.
    `comparison` may be None when the check is off; `spec` supplies
    the duration and the exaggeration; `scene_info` the arrow ratio
    and the camera mode (pseudocode 9.1)."""
    if conserved.jacobi_check is not None:
        drift = conserved.jacobi_check
    elif conserved.energy_check is not None:
        drift = conserved.energy_check
    else:
        drift = None
    if comparison is None:
        numerical = {'delta': None, 'eta': None, 'drift': None,
                     'max_delta': None, 'max_eta': None, 'max_drift': None}
    else:
        numerical = {'delta': float(comparison.delta[k]),
                     'eta': float(comparison.eta[k]),
                     'drift': None if drift is None else float(drift[k]),
                     'max_delta': comparison.max_delta,
                     'max_eta': comparison.max_eta,
                     'max_drift': (None if drift is None
                                   else float(abs(drift).max()))}
    if field.approximation is None:
        approximation = None
    else:
        approximation = {
            'estimate': field.approximation.estimate(spec.duration),
            'note': field.approximation.sentence(spec.duration)}
    distortion = {'exaggeration': spec.exaggeration,
                  'arrow_ratio': scene_info.arrow_ratio,
                  'camera_follows': scene_info.camera_follows}
    return ErrorBudget(numerical=numerical, approximation=approximation,
                       distortion=distortion)
