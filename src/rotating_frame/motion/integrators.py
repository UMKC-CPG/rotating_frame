"""The time-stepping schemes (pseudocode 4.3; design 4.4).

Three schemes, selectable per run: forward Euler, to watch error
grow in a lecture; the classical fourth-order Runge-Kutta scheme
with a fixed step, the default, because its error is the lesson of
VISION P3 and halving the step must divide it by sixteen; and
Dormand-Prince 8(5,3) from SciPy, adaptive, as a tight reference.

A fixed-step scheme takes `substeps` equal steps between consecutive
sample times and records the state at every sample time exactly, so
that the check's samples and the transform's are at the same times
with nothing interpolated. Each integration also offers `evaluate`,
the state at an arbitrary time within the run, which the stopping
search needs: dense output for Dormand-Prince, and for a fixed-step
scheme a re-integration from the last sample before the time with the
same substep, accurate to the scheme's order.

No symplectic scheme is offered: the Coriolis term depends on the
velocity, which the simple ones cannot take without an implicit
step, and the check's job is to disclose error, not to hide it.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
schemes are the standard ones; see Hairer, Norsett, and Wanner,
*Solving Ordinary Differential Equations I*.
"""

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp

INTEGRATORS = ('euler', 'rk4', 'dop853')


@dataclass(frozen=True)
class Integration:
    """The states at the sample times, shape (N, 6), and a function
    giving the state at any time within the run."""

    states: np.ndarray
    evaluate: Callable


def euler_step(derivative, time, state, step):
    """One forward-Euler step: first order."""
    return state + step * derivative(time, state)


def rk4_step(derivative, time, state, step):
    """One classical Runge-Kutta step: fourth order."""
    slope_1 = derivative(time, state)
    slope_2 = derivative(time + step / 2.0, state + step / 2.0 * slope_1)
    slope_3 = derivative(time + step / 2.0, state + step / 2.0 * slope_2)
    slope_4 = derivative(time + step, state + step * slope_3)
    return state + step / 6.0 * (slope_1 + 2.0 * slope_2
                                 + 2.0 * slope_3 + slope_4)


STEP_FUNCTIONS = {'euler': euler_step, 'rk4': rk4_step}


def integrate(derivative, state0, times, method='rk4', substeps=4,
              rtol=1e-10, atol=1e-12):
    """Integrate `derivative` from `state0` at `times[0]`, recording
    the state at every entry of `times`."""
    if method not in INTEGRATORS:
        raise ValueError(f'integrator {method!r}: one of '
                         f'{", ".join(INTEGRATORS)}')
    if substeps < 1:
        raise ValueError('substeps must be at least one')
    times = np.asarray(times, dtype=float)
    state0 = np.asarray(state0, dtype=float)
    if method == 'dop853':
        solution = solve_ivp(derivative, (times[0], times[-1]), state0,
                             method='DOP853', t_eval=times,
                             dense_output=True, rtol=rtol, atol=atol)
        if not solution.success:
            raise RuntimeError(solution.message)
        return Integration(states=solution.y.T,
                           evaluate=lambda time: solution.sol(time))

    step_function = STEP_FUNCTIONS[method]
    states = np.empty((len(times), len(state0)))
    states[0] = state0
    for index in range(1, len(times)):
        state = states[index - 1]
        time = times[index - 1]
        step = (times[index] - times[index - 1]) / substeps
        for _ in range(substeps):
            state = step_function(derivative, time, state, step)
            time += step
        states[index] = state               # exactly at times[index]

    def evaluate(time):
        """Re-integrate from the last sample at or before `time` with
        the same substep, then a final short step to `time`."""
        index = int(np.searchsorted(times, time, side='right') - 1)
        index = min(max(index, 0), len(times) - 1)
        if index == len(times) - 1 or time <= times[index]:
            if np.isclose(time, times[index], rtol=0.0, atol=1e-15):
                return states[index].copy()
            index = max(index - 1, 0)
        step = (times[index + 1] - times[index]) / substeps
        state = states[index].copy()
        current = times[index]
        while current + step <= time + 1e-15 * max(1.0, abs(time)):
            state = step_function(derivative, current, state, step)
            current += step
        if time > current:
            state = step_function(derivative, current, state,
                                  time - current)
        return state

    return Integration(states=states, evaluate=evaluate)
