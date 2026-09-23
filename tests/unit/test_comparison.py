"""Verifies pseudocode 6.6 for `analysis/comparison.py`: the check
against the transform of a free particle, the orders of the schemes,
the launch at sample zero, and `compare`."""

import numpy as np
import pytest

from rotating_frame.analysis import CheckSettings, compare, run_check
from rotating_frame.core.frame import Frame
from rotating_frame.forces import NoForce
from rotating_frame.motion.closed_forms import line

Z_HAT = np.array([0.0, 0.0, 1.0])
FRAME = Frame(Z_HAT, 1.0)
LAUNCH = (np.array([1.0, 0.0, 0.0]), np.array([-0.3, 0.6, 0.2]))
TIMES = np.linspace(0.0, 2.0, 21)


def exact_rotating():
    positions_in, velocities_in = line(*LAUNCH, TIMES)
    return FRAME.to_rotating(TIMES, positions_in, velocities_in)


def max_error(integrator, substeps):
    settings = CheckSettings(True, integrator, substeps, 1e-10, 1e-12)
    positions, _ = run_check(NoForce(), FRAME, LAUNCH, TIMES, settings)
    return np.max(np.abs(positions - exact_rotating()[0]))


def test_rk4_agrees_with_the_transform_and_is_fourth_order():
    # C = 0.02: the measured error at substeps 4 is about 3e-8 with
    # step 0.025, and 0.02 * 0.025^4 is 8e-9 per step, times the
    # eighty steps of the run.
    step = (TIMES[1] - TIMES[0]) / 4
    assert max_error('rk4', 4) < 0.02 * step ** 4 * 80
    ratio = max_error('rk4', 4) / max_error('rk4', 8)
    assert 14.0 <= ratio <= 18.0


def test_euler_is_first_order():
    ratio = max_error('euler', 4) / max_error('euler', 8)
    assert 1.8 <= ratio <= 2.2


def test_the_checks_first_sample_is_the_launch():
    settings = CheckSettings()
    positions, velocities = run_check(NoForce(), FRAME, LAUNCH, TIMES,
                                      settings)
    exact_positions, exact_velocities = exact_rotating()
    assert np.allclose(positions[0], exact_positions[0], atol=1e-15)
    assert np.allclose(velocities[0], exact_velocities[0], atol=1e-15)


def test_compare_on_identical_and_offset_arrays():
    positions, velocities = exact_rotating()
    launch_point = np.zeros(3)
    ghost = positions - launch_point                # the effect is zero
    same = compare(positions, velocities, positions, velocities, ghost,
                   launch_point)
    assert np.all(same.delta == 0.0) and np.all(same.eta == 0.0)
    assert same.max_delta == 0.0 and same.max_eta == 0.0
    offset = np.array([0.0, 0.0, 1e-3])
    ghost = np.zeros_like(positions)                # the effect is |r|
    shifted = compare(positions, velocities, positions + offset,
                      velocities, ghost, launch_point)
    assert np.allclose(shifted.delta, 1e-3)
    assert np.allclose(shifted.effect, np.linalg.norm(positions, axis=1))
    assert np.allclose(shifted.eta, 1e-3 / np.linalg.norm(positions,
                                                          axis=1))
    assert shifted.max_delta == pytest.approx(1e-3)
