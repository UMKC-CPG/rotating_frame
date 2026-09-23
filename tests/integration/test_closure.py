"""The closure test of pseudocode 5.5: differencing the store's
rotating velocities gives the rotating-frame acceleration, and the
true force plus the three terms must equal it to the differencing
error; and the same test, fed the inertial velocity by mistake,
fails."""

from pathlib import Path

import numpy as np
import pytest

from rotating_frame.pseudoforces import terms
from rotating_frame.run import build_store, load_rc, load_run_file

EXAMPLES = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame' \
    / 'examples'
RC = load_rc([Path(__file__).parent])
NAMES = ('turntable', 'merry_go_round', 'earth_drop', 'earth_throw',
         'earth_vertical')


def residual(store, spec, particle, velocities):
    """Max |difference - (true force + terms)| over interior valid
    samples, with the terms evaluated on `velocities`."""
    valid = store.valid_samples(particle)
    if store.stop_of(particle) is not None:
        valid -= 1                       # the event sample is off-grid
    times = store.sample_times()[:valid]
    step = times[1] - times[0]
    positions = store.positions_rot[particle, :valid]
    v_rot = store.velocities_rot[particle, :valid]
    centrifugal, coriolis, euler = terms(spec.frame, times, positions,
                                         velocities[:valid])
    predicted = (store.true_force[particle, :valid] + centrifugal
                 + coriolis + euler)
    differenced = (v_rot[2:] - v_rot[:-2]) / (2.0 * step)
    return np.max(np.abs(differenced - predicted[1:-1])), step


def bound(store, spec, particle, step):
    """Design 5.5: the centered difference's truncation error, from
    the derivative of the rotating-frame equation, plus its rounding,
    which matters on the Earth where a step is 1e-7 in natural time
    and the rotating velocity is the small difference of rim-sized
    numbers."""
    valid = store.valid_samples(particle)
    rate = abs(spec.frame.rate)
    r_max = np.max(np.linalg.norm(store.positions_rot[particle, :valid],
                                  axis=1))
    v_max = np.max(np.linalg.norm(store.velocities_rot[particle, :valid],
                                  axis=1))
    f_max = np.max(np.linalg.norm(store.true_force[particle, :valid],
                                  axis=1))
    a_max = f_max + rate ** 2 * r_max + 2 * rate * v_max
    truncation = step ** 2 * (rate ** 2 * v_max + 2 * rate * a_max) / 6.0
    rounding = np.finfo(float).eps * (v_max + rate * r_max) / step
    return truncation + rounding + 1e-12


@pytest.mark.parametrize('name', NAMES)
def test_the_terms_close_the_equation_of_motion(name):
    spec = load_run_file(EXAMPLES / f'{name}.toml', (), RC)
    store = build_store(spec, RC)
    for particle in range(store.n_particles):
        worst, step = residual(store, spec, particle,
                               store.velocities_rot[particle])
        limit = bound(store, spec, particle, step)
        assert worst <= limit, (f'{name} particle {particle}: residual '
                                f'{worst:.2e} exceeds the bound {limit:.2e}')


def test_the_inertial_velocity_would_be_caught():
    spec = load_run_file(EXAMPLES / 'turntable.toml', (), RC)
    store = build_store(spec, RC)
    worst, step = residual(store, spec, 0, store.velocities_in[0])
    assert worst > bound(store, spec, 0, step)
