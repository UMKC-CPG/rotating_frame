"""Verifies physdemo PSEUDOCODE 4.3: the placeholder physics against
its closed form. PLACEHOLDER: the tool's own oracle tests replace
this file, and keep its two conventions. First, a test names the
chain section it verifies. Second, a tolerance is justified where it
is written."""

import numpy as np
import pytest

from rotating_frame.core.motion import circular_motion_samples


def test_every_sample_is_on_the_circle():
    """Oracle: |r| = radius. Tolerance 1e-12: one multiplication and
    one square root of order-one numbers, so a few ulps."""
    samples = circular_motion_samples(2.0, 0.7, 50, 0.1)
    assert samples.shape == (50, 3)
    assert np.allclose(np.linalg.norm(samples, axis=1), 2.0,
                       atol=1e-12, rtol=0)
    assert np.all(samples[:, 2] == 0.0)


def test_the_angle_advances_at_the_angular_speed():
    """Oracle: the polar angle of sample k is angular_speed * k * dt,
    modulo 2 pi. Tolerance 1e-12 as above; the arctangent adds no
    error worth counting at these magnitudes."""
    angular_speed, dt = 0.7, 0.1
    samples = circular_motion_samples(1.0, angular_speed, 50, dt)
    angles = np.arctan2(samples[:, 1], samples[:, 0])
    expected = (angular_speed * np.arange(50) * dt + np.pi) \
        % (2 * np.pi) - np.pi
    assert np.allclose(angles, expected, atol=1e-12, rtol=0)


@pytest.mark.parametrize('bad', [dict(radius=0.0), dict(n_steps=0),
                                 dict(dt=-1.0)])
def test_a_meaningless_argument_is_refused(bad):
    arguments = dict(radius=1.0, angular_speed=1.0, n_steps=10, dt=0.1)
    arguments.update(bad)
    with pytest.raises(ValueError):
        circular_motion_samples(**arguments)
