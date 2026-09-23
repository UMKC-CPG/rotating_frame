"""Verifies pseudocode 6.6 for `analysis/error_budget.py`: the three
columns filled from their sources, and the assertion, by reading the
source, that no code combines two of them."""

import ast
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from rotating_frame.analysis import (CheckSettings, ErrorBudget, budget_at,
                                     compare, ghost_path, monitor,
                                     run_check)
from rotating_frame.analysis.error_budget import COLUMN_NAMES
from rotating_frame.core.frame import Frame
from rotating_frame.forces import Approximation, UniformGravityFrameFixed
from rotating_frame.forces.fields import UNIFORM_APPROXIMATION_NOTE
from rotating_frame.motion.closed_forms import sample_closed_form

PACKAGE = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame'
Z_HAT = np.array([0.0, 0.0, 1.0])


def combines_two_columns(tree):
    """True if any binary operation has, on both sides, an attribute
    access named for two different columns."""
    def column_of(node):
        if isinstance(node, ast.Attribute) and node.attr in COLUMN_NAMES:
            return node.attr
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp):
            left, right = column_of(node.left), column_of(node.right)
            if left and right and left != right:
                return True
    return False


def test_no_module_combines_two_columns():
    for directory in ('analysis', 'render'):
        for path in sorted((PACKAGE / directory).rglob('*.py')):
            assert not combines_two_columns(ast.parse(path.read_text())), \
                f'{path.relative_to(PACKAGE)} combines two error columns'


def test_the_assertion_catches_a_planted_violation():
    planted = ast.parse('total = budget.numerical + budget.distortion\n')
    assert combines_two_columns(planted)
    harmless = ast.parse('x = budget.numerical + budget.numerical\n')
    assert not combines_two_columns(harmless)


def test_budget_at_fills_the_three_columns():
    frame = Frame(Z_HAT, 1.0)
    latitude = np.radians(45.0)
    gravity_rot = -2.0 * np.array([np.cos(latitude), 0.0, np.sin(latitude)])
    approximation = Approximation(UNIFORM_APPROXIMATION_NOTE, 50.0)
    field = UniformGravityFrameFixed(gravity_rot, frame, approximation)
    launch_point = 5.0 * np.array([np.cos(latitude), 0.0, np.sin(latitude)])
    launch = frame.launch_to_inertial(launch_point + [0.1, 0.0, 0.1],
                                      np.zeros(3))
    times = np.linspace(0.0, 0.5, 11)
    positions_in, velocities_in = sample_closed_form(
        'rotating_parabola', field, frame, *launch, times)
    rotating = frame.to_rotating(times, positions_in, velocities_in)
    settings = CheckSettings()
    check = run_check(field, frame, launch, times, settings)
    ghost = ghost_path(field, frame, launch, launch_point, times, settings)
    comparison = compare(*rotating, *check, ghost, launch_point)
    conserved = monitor(field, frame, launch, times,
                        (positions_in, velocities_in), rotating, check)
    spec = SimpleNamespace(duration=0.5, exaggeration=3.0)
    scene = SimpleNamespace(arrow_ratio=120.0, camera_follows=True)
    budget = budget_at(comparison, conserved, field, spec, 4, scene)
    assert isinstance(budget, ErrorBudget)
    assert budget.numerical['delta'] == pytest.approx(comparison.delta[4])
    assert budget.numerical['drift'] == pytest.approx(
        conserved.jacobi_check[4])
    assert budget.numerical['max_eta'] == comparison.max_eta
    assert budget.approximation['estimate'] == pytest.approx(
        0.5 * (0.5 / 50.0) ** 2)
    assert 'launch point' in budget.approximation['note']
    assert budget.distortion == {'exaggeration': 3.0, 'arrow_ratio': 120.0,
                                 'camera_follows': True}
    without_check = budget_at(None, conserved, field, spec, 4, scene)
    assert without_check.numerical['delta'] is None
