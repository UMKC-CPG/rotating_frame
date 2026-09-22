"""Uniform circular motion, the skeleton's placeholder physics
(physdemo PSEUDOCODE 4.3).

A point moves on a circle of radius `radius` in the x-y plane at
constant angular speed `angular_speed`, so that at time `t` it is at

##    x = radius * cos(angular_speed * t)
##    y = radius * sin(angular_speed * t)
##    z = 0

This is here to be replaced. It was chosen because it has a closed
form to test against, needs one NumPy call, and draws as one glyph
and one trail, which is exactly enough to exercise the run file, the
scene, and the self-check.

Attribution: this module is part of the Rotating Frame teaching tool.
"""

import numpy as np


def circular_motion_samples(radius, angular_speed, n_steps, dt):
    """Return the positions of the point at `n_steps` times spaced
    `dt` apart, starting at t = 0, as an array of shape (n_steps, 3).

    Every argument that would make the motion meaningless is refused
    with a ValueError naming it, so that a bad run file fails at the
    physics boundary with a message rather than with a NaN later.
    """
    if radius <= 0:
        raise ValueError(f'radius must be positive, not {radius}')
    if n_steps < 1:
        raise ValueError(f'n_steps must be at least 1, not {n_steps}')
    if dt <= 0:
        raise ValueError(f'dt must be positive, not {dt}')
    times = np.arange(n_steps) * dt
    angle = angular_speed * times
    return np.column_stack((radius * np.cos(angle),
                            radius * np.sin(angle),
                            np.zeros(n_steps)))
