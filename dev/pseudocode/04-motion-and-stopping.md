# Pseudocode 4: Motion and Stopping

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 4. Governs
> `src/rotating_frame/motion/closed_forms.py`,
> `motion/equations_of_motion.py`, `motion/integrators.py`,
> `motion/stopping.py`, `motion/motion_provider.py`, and the tests
> `tests/unit/test_closed_forms.py`, `test_integrators.py`,
> `test_stopping.py`, `test_motion_provider.py`, and
> `tests/integration/test_drop_oracle.py`.
> *Status: reviewed; ratified 2026-09-22.*

New code. `motion/` imports `core/`, `forces/`, and `pseudoforces/`
(Pseudocode 5, for the rotating-frame equation). The state handed to
an integrator is one array of six, position then velocity, in the
components of whichever frame the equation is written in.

**Seam with Pseudocode 3.** The closed forms need the field's vector,
which the interface does not expose generically: `closed_forms`
reads `field.gravity_in` for `"parabola"` and `field.gravity_rot` for
`"rotating_parabola"`, the attributes the two uniform classes hold,
and nothing for `"line"`. A new closed form adds a name there, a
reader here, and an attribute on its field.

---

## 4.1 `motion/closed_forms.py`

```
function one_minus_cos(theta):                               # exact
    return 2 * sin(theta / 2) ** 2

function theta_minus_sin(theta):                             # Design 4.2
    # Series through θ⁹/9! below 0.1 (next term < 1e-16 relative),
    #   the direct difference above; vectorized with `where`.
    small = |theta| < 0.1
    t2 = theta²
    series = theta³/6 * (1 - t2/20 * (1 - t2/42 * (1 - t2/72)))
    return where(small, series, theta - sin(theta))

function line(position0, velocity0, times) -> (positions, velocities):
    positions  = position0 + outer(times, velocity0)          # (4.2)
    velocities = broadcast(velocity0, (N, 3))

function parabola(position0, velocity0, gravity, times):
    positions  = position0 + outer(times, velocity0)
                 + 0.5 * outer(times², gravity)               # (4.3)
    velocities = velocity0 + outer(times, gravity)

function rotating_parabola(position0, velocity0, gravity_rot, frame,
                           times):                            # (4.4)
    axis = frame.axis; rate = frame.rate
    g_parallel = (gravity_rot · axis) * axis
    g_perp     = gravity_rot - g_parallel
    axis_cross = cross(axis, g_perp)
    theta      = frame.angle(times)                           # (N,)
    c1 = one_minus_cos(theta) / rate²                         # (N,)
    c2 = theta_minus_sin(theta) / rate²
    s1 = sin(theta) / rate
    positions  = position0 + outer(times, velocity0)
                 + 0.5 * outer(times², g_parallel)
                 + outer(c1, g_perp) + outer(c2, axis_cross)
    velocities = velocity0 + outer(times, g_parallel)
                 + outer(s1, g_perp) + outer(one_minus_cos(theta) / rate,
                                             axis_cross)

CLOSED_FORMS = {"line": ..., "parabola": ..., "rotating_parabola": ...}

function sample_closed_form(name, field, frame, position0, velocity0,
                            times) -> (positions, velocities):
    if name == "line":               return line(position0, velocity0, times)
    if name == "parabola":           return parabola(..., field.gravity_in,
                                                    times)
    if name == "rotating_parabola":  return rotating_parabola(...,
                                         field.gravity_rot, frame, times)
    raise KeyError(name)             # a programming error, not a run error
```

Every function is exact at each time and evaluates nothing
cumulatively (Design 4.3); `times` need not be uniform, which is
what lets the stopping search evaluate the form at an arbitrary
`t_stop`.

## 4.2 `motion/equations_of_motion.py`

```
function inertial_derivative(field) -> function(time, state) -> (6,):
    # ẋ = v, v̇ = f_in(t, x, v).
    def derivative(time, state):
        position, velocity = state[:3], state[3:]
        return concatenate(velocity,
                           field.acceleration(time, position, velocity))
    return derivative

function rotating_derivative(field, frame) -> function(time, state) -> (6,):
    # Equation (2.1) / (6.1): the true force in rotating components
    #   plus the three terms of Pseudocode 5, at the current state.
    def derivative(time, state_rot):
        position_rot, velocity_rot = state_rot[:3], state_rot[3:]
        true_force = field.acceleration_rotating(frame, time,
                                                 position_rot, velocity_rot)
        centrifugal, coriolis, euler = pseudoforces.terms(
            frame, time, position_rot, velocity_rot)
        return concatenate(velocity_rot,
                           true_force + centrifugal + coriolis + euler)
    return derivative
```

Both take a scalar time and a single six-state, which is what the
integrators call; vectorization over samples is the integrator's
loop.

## 4.3 `motion/integrators.py`

```
INTEGRATORS = ("euler", "rk4", "dop853")

frozen record Integration:
    states     (N, 6) at the sample times
    evaluate   function(time) -> (6,): the state at an arbitrary time
               in [times[0], times[-1]], for the stopping search:
               dense output for dop853; for a fixed-step scheme, a
               re-integration from the last sample before `time`
               with the same substep, accurate to the scheme's order

function euler_step(derivative, time, state, step) -> state:
    return state + step * derivative(time, state)

function rk4_step(derivative, time, state, step) -> state:
    k1 = derivative(time, state)
    k2 = derivative(time + step/2, state + step/2 * k1)
    k3 = derivative(time + step/2, state + step/2 * k2)
    k4 = derivative(time + step, state + step * k3)
    return state + step/6 * (k1 + 2 k2 + 2 k3 + k4)

function integrate(derivative, state0, times, method, substeps = 4,
                   rtol = 1e-10, atol = 1e-12) -> Integration:
    if method not in INTEGRATORS: raise ValueError naming the three
    if method == "dop853":
        solution = scipy.integrate.solve_ivp(derivative,
            (times[0], times[-1]), state0, method = "DOP853",
            t_eval = times, dense_output = True, rtol = rtol, atol = atol)
        if not solution.success: raise RuntimeError(solution.message)
        return Integration(states = solution.y.T,
                           evaluate = lambda t: solution.sol(t))
    step_function = euler_step if method == "euler" else rk4_step
    states = empty((N, 6)); states[0] = state0
    for k in 1 … N-1:
        state = states[k-1]; time = times[k-1]
        step = (times[k] - times[k-1]) / substeps
        for s in 0 … substeps-1:
            state = step_function(derivative, time, state, step)
            time += step
        states[k] = state                     # exactly at times[k]
    def evaluate(t):
        k = the last index with times[k] <= t
        step = (times[k+1] - times[k]) / substeps    (or the last interval)
        state = states[k]; time = times[k]
        while time + step <= t + 1e-15:
            state = step_function(derivative, time, state, step); time += step
        if t > time: state = step_function(derivative, time, state, t - time)
        return state
    return Integration(states, evaluate)
```

The fixed-step loop lands on every sample time exactly because it
takes `substeps` equal steps per interval; no interpolation anywhere
(Design 4.4).

## 4.4 `motion/stopping.py`

```
abstract class StoppingRule:
    abstract method value(position_rot) -> float or (N,)
        # Positive before the event, zero at it, negative after; the
        #   rule fires at the first sample where value <= 0.

class DurationRule(StoppingRule):
    method value(position_rot): return +inf         # never fires

class LandsRule(StoppingRule):                       # Design 4.5, 3.4.1
    constructor (launch_point_rot, up): store
    method value(position_rot):
        return (position_rot - launch_point_rot) · up          # h

class LeavesRule(StoppingRule):
    constructor (launch_point_rot, axis, radius = 1.0): store
    method value(position_rot):
        rho = position_rot - launch_point_rot
        rho_h = rho - (rho · axis) * axis
        return radius - |rho_h|

function make_rule(name, launch_point_rot, up, axis) -> StoppingRule:
    "duration" -> DurationRule(); "lands" -> LandsRule(launch_point_rot,
    up); "leaves" -> LeavesRule(launch_point_rot, axis); else ValueError

frozen record StopEvent:
    index       the first sample index at or past which the rule held
    time        t̃_stop
    position_in, velocity_in    the state at t̃_stop, inertial components

function locate_event(rule, frame, times, positions_in, evaluate)
        -> StopEvent | None:
    # `evaluate(t)` returns the inertial six-state at t (a closed form
    #   or an Integration's evaluate).
    positions_rot, _ = frame.to_rotating(times, positions_in, zeros)
    values = rule.value(positions_rot)                       # (N,)
    if values[0] <= 0 and the launch is not upward (Design 7.4): the
        schema has refused this already; assert
    k = first index >= 1 with values[k] <= 0;  if none: return None
    def crossing(t):
        state = evaluate(t)
        position_rot, _ = frame.to_rotating(t, state[:3], state[3:])
        return rule.value(position_rot)
    t_stop = brentq(crossing, times[k-1], times[k], xtol = 1e-12)
    state = evaluate(t_stop)
    return StopEvent(k, t_stop, state[:3], state[3:])

function apply_event(times, positions, velocities, event)
        -> (times, positions, velocities, is_event_sample):
    # Keep samples 0 … k-1, append the event state as sample k, drop
    #   the rest; flag the appended sample (Design 4.5).
    keep = event.index
    times      = concatenate(times[:keep], [event.time])
    positions  = concatenate(positions[:keep], [event.position_in])
    velocities = concatenate(velocities[:keep], [event.velocity_in])
    flag       = zeros(keep + 1, bool); flag[-1] = True
    return times, positions, velocities, flag
```

## 4.5 `motion/motion_provider.py`

```
METHODS = ("auto", "closed_form", "numerical")

frozen record Trajectory:
    times            (M,)      M = N, or k + 1 after a stop
    positions_in     (M, 3)
    velocities_in    (M, 3)
    stop             StopEvent | None
    is_event_sample  (M,) bool

function provide(launch, field, frame, duration, samples, rule,
                 method = "auto", integrator = "rk4", substeps = 4,
                 rtol = 1e-10, atol = 1e-12) -> Trajectory:        # (4.1)
    # launch: (position_in, velocity_in) at t = 0, already converted
    #   (Pseudocode 7).
    if method not in METHODS: raise ValueError naming the three
    times = linspace(0, duration, samples)
    use_closed = (method == "closed_form") or
                 (method == "auto" and field.closed_form is not None)
    if method == "closed_form" and field.closed_form is None:
        raise ValueError("this field has no closed form; use "
                         "method = 'numerical' or 'auto'")
    if use_closed:
        positions, velocities = sample_closed_form(field.closed_form,
            field, frame, *launch, times)
        evaluate = lambda t: concatenate(sample_closed_form(
            field.closed_form, field, frame, *launch, array([t]))[...][0])
    else:
        integration = integrate(inertial_derivative(field),
            concatenate(launch), times, integrator, substeps, rtol, atol)
        positions, velocities = integration.states[:, :3], [:, 3:]
        evaluate = integration.evaluate
    event = locate_event(rule, frame, times, positions, evaluate)
    if event is None:
        return Trajectory(times, positions, velocities, None,
                          zeros(samples, bool))
    times, positions, velocities, flag = apply_event(times, positions,
                                                     velocities, event)
    return Trajectory(times = times, positions_in = positions,
                      velocities_in = velocities, stop = event,
                      is_event_sample = flag)
```

## 4.6 Verification

`test_closed_forms.py`:

- `one_minus_cos` and `theta_minus_sin` against the direct
  expressions for `θ` in `[0.1, 10]` to `1e-13` relative plus `1e-15`
  absolute: the relative part is the direct form's own rounding at
  `θ = 0.1` (`1e-16 / θ³ × θ`), and the absolute part is the direct
  form's cancellation near `θ = 2π`, where `1 − cos θ` itself is small
  (found when the test was first run);
  for `θ = 1e-4` the series equals `θ³/6 (1 − θ²/20)` to `1e-16` and
  the direct difference does not (its error is `3e-8` relative,
  checked against a forty-digit evaluation while this section was
  written).
- `rotating_parabola` with `gravity_rot ∥ axis` equals `parabola`
  with the same vector, exactly.
- Each closed form against `integrate(..., "dop853", rtol=1e-12)` on
  its own field over three turns, `1e-10` relative in position.

`test_integrators.py`:

- On `rotating_derivative` for the free particle with a known
  transform (Pseudocode 1): the `rk4` error at `t̃ = 2` falls by a
  factor in `[14, 18]` when `substeps` doubles from 4 to 8, and the
  `euler` error by a factor in `[1.8, 2.2]`.
- `dop853` reproduces the same case to `rtol`; an unknown method
  raises naming the three.
- `Integration.evaluate(times[k]) == states[k]` for fixed-step
  schemes, and `evaluate` between samples agrees with a run whose
  sample grid includes that time, to the scheme's order.

`test_stopping.py`:

- `LandsRule.value` is the height above the ground; `LeavesRule.value`
  is `1 − |ρ_h|`; `DurationRule` never fires.
- A parabola from height `1` at `g̃ = 1` lands at `t̃ = √2`: the event
  time is within `1e-12`, the event state has `value = 0` to `1e-12`,
  `apply_event` keeps `k` samples plus the event and flags only the
  last, and no kept sample is past the event.
- A line from the center of the unit disc at unit speed leaves at
  `t̃ = 1`, likewise.

`test_motion_provider.py`:

- `"auto"` on each first-version field uses the closed form (the
  trajectory equals `sample_closed_form` exactly); `"numerical"`
  differs from it by less than `C Δt̃⁴`; `"closed_form"` on a
  throwaway field with `closed_form = None` raises with the stated
  message.
- The returned `times` are uniform up to the event and the record's
  arrays share a length.

`tests/integration/test_drop_oracle.py` (Design 4.6, the spike made
a test):

- Earth preset, `λ` in `{10°, 30°, 45°, 60°, 80°}`, a drop from
  `100 m` at rest in the rotating frame, `"auto"`, `"lands"`: the
  landing offset along `ê_E` equals
  `(1/3) g₀ Ω t_stop³ cos λ × (1 − Ω² R_E / g₀)` to `1e-5` relative,
  and the offset along `ê_N` is below `(Ω t_stop)² × 100 m` in
  magnitude; `t_stop` is within `1e-6` relative of
  `sqrt(2 h / |g_eff|)`.
