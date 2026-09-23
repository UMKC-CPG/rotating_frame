"""Is it right? The check, the comparison, the conserved quantities,
the first-order deflections, and the error budget (pseudocode 6;
design 6; ARCHITECTURE 3.6).

These are runtime components, not test helpers: the comparison's
number is what a student reads as "numerical error", the ghost path
is drawn, and the budget's three columns are on screen. The
rotating-frame integration lives here because its only purpose is
to be compared with the exact transform; nothing that draws imports
it (ARCHITECTURE 6.1).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from rotating_frame.analysis.comparison import (CheckSettings, Comparison,
                                                compare, run_check)
from rotating_frame.analysis.conservation_monitor import (Conserved,
                                                          monitor)
from rotating_frame.analysis.closed_form_deflections import (
    coriolis_deflection, first_order_deflection, first_order_tolerance,
    overlay_applies)
from rotating_frame.analysis.error_budget import ErrorBudget, budget_at
from rotating_frame.analysis.ghost_path import ghost_path

__all__ = ['CheckSettings', 'Comparison', 'compare', 'run_check',
           'Conserved', 'monitor', 'coriolis_deflection',
           'first_order_deflection',
           'first_order_tolerance', 'overlay_applies', 'ErrorBudget',
           'budget_at', 'ghost_path']
