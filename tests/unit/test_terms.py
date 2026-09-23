"""Verifies pseudocode 5.3: the three terms' geometric properties,
the two sign checks, the stacked order, and broadcasting. The closure
test against a store is `tests/integration/test_closure.py`, written
with section 8."""

import numpy as np
import pytest

from rotating_frame.core.frame import Frame
from rotating_frame.pseudoforces import TERM_NAMES, stacked, terms, total

TOLERANCE = 1e-14
RANDOM = np.random.default_rng(5)
Z_HAT = np.array([0.0, 0.0, 1.0])


def perpendicular_part(vectors, axis):
    axial = (vectors @ axis)[..., np.newaxis] * axis
    return vectors - axial


@pytest.mark.parametrize('rate', [1.0, -1.0, 2.5])
def test_the_geometric_properties(rate):
    frame = Frame(Z_HAT, rate)
    positions, velocities = RANDOM.normal(size=(2, 20, 3))
    centrifugal, coriolis, euler = terms(frame, 0.0, positions, velocities)
    assert np.allclose(centrifugal @ Z_HAT, 0.0, atol=TOLERANCE)
    radial = perpendicular_part(positions, Z_HAT)
    assert np.all(np.einsum('ij,ij->i', centrifugal, radial) >= -TOLERANCE)
    assert np.allclose(np.linalg.norm(centrifugal, axis=1),
                       rate ** 2 * np.linalg.norm(radial, axis=1),
                       atol=TOLERANCE)
    assert np.allclose(coriolis @ Z_HAT, 0.0, atol=TOLERANCE)
    assert np.allclose(np.einsum('ij,ij->i', coriolis, velocities), 0.0,
                       atol=TOLERANCE)
    assert np.allclose(np.linalg.norm(coriolis, axis=1),
                       2.0 * abs(rate)
                       * np.linalg.norm(perpendicular_part(velocities,
                                                           Z_HAT), axis=1),
                       atol=TOLERANCE)
    assert np.all(euler == 0.0)


def test_reversing_the_rate_reverses_coriolis_and_not_centrifugal():
    positions, velocities = RANDOM.normal(size=(2, 5, 3))
    forward = terms(Frame(Z_HAT, 1.0), 0.0, positions, velocities)
    backward = terms(Frame(Z_HAT, -1.0), 0.0, positions, velocities)
    assert np.allclose(forward[0], backward[0], atol=TOLERANCE)
    assert np.allclose(forward[1], -backward[1], atol=TOLERANCE)


@pytest.mark.parametrize('latitude_deg', [10.0, 45.0, 80.0])
def test_sign_check_one_north_is_pushed_east(latitude_deg):
    frame = Frame(Z_HAT, 1.0)
    latitude = np.radians(latitude_deg)
    velocity_north = np.array([-np.sin(latitude), 0.0, np.cos(latitude)])
    _, coriolis, _ = terms(frame, 0.0, np.zeros(3), velocity_north)
    assert np.allclose(coriolis, [0.0, 2.0 * np.sin(latitude), 0.0],
                       atol=TOLERANCE)


def test_sign_check_two_outward_on_the_turntable_is_pushed_clockwise():
    frame = Frame(Z_HAT, 1.0)
    radius, speed = 0.7, 0.4
    position = np.array([radius, 0.0, 0.0])
    _, coriolis, _ = terms(frame, 0.0, position, np.array([speed, 0, 0]))
    assert np.allclose(coriolis, [0.0, -2.0 * speed, 0.0], atol=TOLERANCE)
    centrifugal, coriolis_at_rest, _ = terms(frame, 0.0, position,
                                             np.zeros(3))
    assert np.allclose(coriolis_at_rest, 0.0)
    assert np.allclose(centrifugal, [radius, 0.0, 0.0], atol=TOLERANCE)


def test_stacked_and_total():
    frame = Frame(Z_HAT, 1.3)
    positions, velocities = RANDOM.normal(size=(2, 4, 3))
    three = terms(frame, 0.0, positions, velocities)
    stack = stacked(frame, 0.0, positions, velocities)
    assert stack.shape == (4, 3, 3)
    for index, name in enumerate(TERM_NAMES):
        assert np.allclose(stack[:, index], three[index])
    assert np.allclose(total(frame, 0.0, positions, velocities),
                       sum(three), atol=TOLERANCE)


def test_broadcasting_over_particles_and_samples():
    frame = Frame([0.2, 0.3, 0.9], 0.8)
    times = np.linspace(0.0, 2.0, 6)
    positions, velocities = RANDOM.normal(size=(2, 3, 6, 3))
    stack = stacked(frame, times, positions, velocities)
    assert stack.shape == (3, 6, 3, 3)
    for particle in range(3):
        for sample in range(6):
            single = stacked(frame, times[sample], positions[particle,
                                                             sample],
                             velocities[particle, sample])
            assert np.allclose(stack[particle, sample], single,
                               atol=TOLERANCE)
