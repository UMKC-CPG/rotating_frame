"""Verifies pseudocode 4.6 for `motion/closed_forms.py`: the two
cancellation-free functions against a forty-digit evaluation, the
reduction of the rotating parabola to the parabola, and each closed
form against a tight numerical integration."""

from decimal import Decimal, getcontext

import numpy as np
import pytest

from rotating_frame.core.frame import Frame
from rotating_frame.forces import (NoForce, UniformGravityFrameFixed,
                                   UniformGravitySpaceFixed)
from rotating_frame.motion.closed_forms import (one_minus_cos,
                                                parabola,
                                                rotating_parabola,
                                                sample_closed_form,
                                                theta_minus_sin)
from rotating_frame.motion.equations_of_motion import inertial_derivative
from rotating_frame.motion.integrators import integrate

Z_HAT = np.array([0.0, 0.0, 1.0])


def theta_minus_sin_exact(theta):
    """`theta - sin(theta)` to forty digits, by the sine series in
    Decimal arithmetic."""
    getcontext().prec = 40
    x = Decimal(repr(theta))
    total = Decimal(0)
    term = x
    power = 1
    for _ in range(40):
        total += term
        term = -term * x * x / ((power + 1) * (power + 2))
        power += 2
    return float(x - total)


def test_the_small_angle_functions_match_the_direct_forms_above_0_1():
    """The absolute floor covers the direct form's own cancellation
    near two pi, where 1 - cos(theta) is itself small; the relative
    part is its rounding at 0.1 (pseudocode 4.6)."""
    thetas = np.linspace(0.1, 10.0, 200)
    assert np.allclose(one_minus_cos(thetas), 1.0 - np.cos(thetas),
                       rtol=1e-13, atol=1e-15)
    assert np.allclose(theta_minus_sin(thetas), thetas - np.sin(thetas),
                       rtol=1e-13, atol=1e-15)


def test_the_series_keeps_all_digits_where_the_difference_does_not():
    theta = 1e-4
    exact = theta_minus_sin_exact(theta)
    assert float(theta_minus_sin(theta)) == pytest.approx(exact, rel=1e-15)
    direct = theta - np.sin(theta)
    assert abs(direct - exact) / exact > 1e-9
    assert float(one_minus_cos(theta)) == pytest.approx(
        2.0 * np.sin(theta / 2) ** 2, rel=1e-15)


def test_the_rotating_parabola_reduces_to_the_parabola_on_the_axis():
    frame = Frame(Z_HAT, 1.0)
    times = np.linspace(0.0, 5.0, 11)
    position0 = np.array([1.0, 0.5, 0.2])
    velocity0 = np.array([0.3, -0.1, 0.4])
    gravity = np.array([0.0, 0.0, -2.0])
    plain = parabola(position0, velocity0, gravity, times)
    turning = rotating_parabola(position0, velocity0, gravity, frame, times)
    assert np.array_equal(plain[0], turning[0])
    assert np.array_equal(plain[1], turning[1])


@pytest.mark.parametrize('case', ['line', 'parabola', 'rotating_parabola'])
def test_each_closed_form_against_a_tight_integration(case):
    frame = Frame([0.2, -0.3, 0.9], 1.0)
    if case == 'line':
        field = NoForce()
    elif case == 'parabola':
        field = UniformGravitySpaceFixed([0.1, -0.5, -1.0], frame)
    else:
        field = UniformGravityFrameFixed([0.4, 0.0, -0.9], frame, None)
    assert field.closed_form == case
    position0 = np.array([1.0, 0.0, 0.2])
    velocity0 = np.array([0.1, 0.6, 0.3])
    times = np.linspace(0.0, 3.0 * 2.0 * np.pi, 61)      # three turns
    positions, velocities = sample_closed_form(case, field, frame,
                                               position0, velocity0, times)
    reference = integrate(inertial_derivative(field),
                          np.concatenate((position0, velocity0)), times,
                          'dop853', rtol=1e-12, atol=1e-14)
    scale = np.max(np.linalg.norm(positions, axis=1))
    assert np.allclose(positions, reference.states[:, :3],
                       atol=1e-10 * scale, rtol=0.0)
    assert np.allclose(velocities, reference.states[:, 3:],
                       atol=1e-10 * scale, rtol=0.0)


def test_an_unknown_name_is_a_programming_error():
    with pytest.raises(KeyError):
        sample_closed_form('spiral', NoForce(), Frame(Z_HAT, 1.0),
                           np.zeros(3), np.zeros(3), np.zeros(2))
