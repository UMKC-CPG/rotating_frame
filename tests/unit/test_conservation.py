"""Verifies pseudocode 6.6 for `analysis/conservation_monitor.py`:
constancy along exact paths, drift along the check, the sentences
for what is not reported, and the scale."""

import numpy as np
import pytest

from rotating_frame.analysis import CheckSettings, monitor, run_check
from rotating_frame.analysis.conservation_monitor import (NOT_CONSERVED,
                                                          scale)
from rotating_frame.core.frame import Frame
from rotating_frame.forces import (NoForce, UniformGravityFrameFixed,
                                   UniformGravitySpaceFixed)
from rotating_frame.motion.closed_forms import sample_closed_form

Z_HAT = np.array([0.0, 0.0, 1.0])
TIMES = np.linspace(0.0, 3.0, 31)


def exact_run(field, frame, launch):
    positions_in, velocities_in = sample_closed_form(
        field.closed_form, field, frame, *launch, TIMES)
    inertial = (positions_in, velocities_in)
    rotating = frame.to_rotating(TIMES, positions_in, velocities_in)
    return inertial, rotating


@pytest.mark.parametrize('case', ['none', 'space', 'frame'])
def test_the_declared_quantity_is_constant_along_the_exact_path(case):
    frame = Frame(Z_HAT, 1.0)
    latitude = np.radians(30.0)
    if case == 'none':
        field = NoForce()
    elif case == 'space':
        field = UniformGravitySpaceFixed([0.0, 0.0, -1.5], frame)
    else:
        field = UniformGravityFrameFixed(
            -1.5 * np.array([np.cos(latitude), 0.0, np.sin(latitude)]),
            frame, None)
    launch = (np.array([1.0, 0.2, 0.5]), np.array([-0.3, 0.7, 0.4]))
    inertial, rotating = exact_run(field, frame, launch)
    conserved = monitor(field, frame, launch, TIMES, inertial, rotating,
                        None)
    assert conserved.scale > 0.0
    if case in ('none', 'space'):
        assert np.max(np.abs(conserved.energy_exact)) < 1e-13
        assert np.max(np.abs(conserved.jacobi_exact)) < 1e-13
        assert conserved.notes == ()
    else:
        assert conserved.energy_exact is None
        assert np.max(np.abs(conserved.jacobi_exact)) < 1e-13
        assert conserved.notes == (NOT_CONSERVED['E'],)
    assert conserved.energy_check is None
    assert conserved.jacobi_check is None


def test_the_check_drifts_by_the_integrators_error():
    frame = Frame(Z_HAT, 1.0)
    field = NoForce()
    launch = (np.array([1.0, 0.0, 0.0]), np.array([-0.3, 0.6, 0.2]))
    inertial, rotating = exact_run(field, frame, launch)
    settings = CheckSettings(True, 'rk4', 4, 1e-10, 1e-12)
    check = run_check(field, frame, launch, TIMES, settings)
    conserved = monitor(field, frame, launch, TIMES, inertial, rotating,
                        check)
    step = (TIMES[1] - TIMES[0]) / 4
    for drift in (conserved.energy_check, conserved.jacobi_check):
        assert drift is not None
        assert np.max(np.abs(drift)) < 0.05 * step ** 4 * len(TIMES) * 4
        assert np.max(np.abs(drift)) > 0.0


def test_a_tilted_axis_with_space_fixed_gravity_reports_energy_only():
    frame = Frame([1.0, 0.0, 1.0], 1.0)
    field = UniformGravitySpaceFixed([0.0, 0.0, -1.0], frame)
    launch = (np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.5, 0.0]))
    inertial, rotating = exact_run(field, frame, launch)
    conserved = monitor(field, frame, launch, TIMES, inertial, rotating,
                        None)
    assert conserved.jacobi_exact is None
    assert conserved.notes == (NOT_CONSERVED['J'],)
    assert np.max(np.abs(conserved.energy_exact)) < 1e-13


def test_the_scale_is_the_stated_sum():
    frame = Frame(Z_HAT, 2.0)
    field = UniformGravitySpaceFixed([0.0, 0.0, -3.0], frame)
    launch = (np.array([1.0, 0.0, 0.0]), np.array([0.0, 4.0, 0.0]))
    positions_rot = np.array([[1.0, 0.0, 0.0], [1.0, 0.0, -2.0],
                              [0.5, 0.0, 0.0]])
    # speed0^2 / 2 = 8; g * rho_max = 3 * 2 = 6; rate^2 r_perp^2 / 2 = 2.
    assert scale(frame, field, launch, positions_rot) == pytest.approx(
        16.0, rel=1e-12)
