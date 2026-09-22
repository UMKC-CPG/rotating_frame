# Pseudocode 6: The Check and the Error Budget

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 6. Governs
> `src/rotating_frame/analysis/comparison.py`,
> `analysis/ghost_path.py`, `analysis/conservation_monitor.py`,
> `analysis/closed_form_deflections.py`, `analysis/error_budget.py`,
> and the tests `tests/unit/test_comparison.py`, `test_ghost_path.py`,
> `test_conservation.py`, `test_deflections.py`,
> `test_error_budget.py`. *Status: draft.*

New code. `analysis/` imports `core/`, `forces/`, `motion/`
(Pseudocode 4's integrators and derivatives), and `pseudoforces/`;
nothing in `render/` or `ui/` imports `analysis/` directly, they
read what the store holds (Pseudocode 8). Natural units, per unit
mass.

---

## 6.1 `analysis/comparison.py`: the check and the comparison

```
frozen record CheckSettings:
    enabled     bool
    integrator  "euler" | "rk4" | "dop853"
    substeps    int
    rtol, atol  floats

function run_check(field, frame, launch_in, times, settings)
        -> (positions_rot, velocities_rot):                   # (6.1)
    # The rotating-frame integration from the same launch. It reads
    #   the launch, the field, and the frame, never the transform's
    #   samples (A6.1).
    position_rot0, velocity_rot0 = frame.to_rotating(0.0, *launch_in)
    state0 = concatenate(position_rot0, velocity_rot0)
    integration = integrate(rotating_derivative(field, frame), state0,
                            times, settings.integrator, settings.substeps,
                            settings.rtol, settings.atol)  # Pseudocode 4.3
    return integration.states[:, :3], integration.states[:, 3:]

DELTA_FLOOR = 1e-9

frozen record Comparison:
    delta        (N,)  |r_rot^check − r_rot|                  # (6.2)
    delta_v      (N,)  |v_rot^check − v_rot|
    effect       (N,)  |ρ_rot − ρ_ghost|                     # |Δ̃|
    eta          (N,)  delta / max(effect, DELTA_FLOOR)      # η
    max_delta, max_eta   scalars over the run

function compare(positions_rot, velocities_rot, check_positions,
                 check_velocities, ghost_positions, launch_point_rot)
        -> Comparison:
    delta    = norm(check_positions - positions_rot, axis = -1)
    delta_v  = norm(check_velocities - velocities_rot, axis = -1)
    effect   = norm((positions_rot - launch_point_rot)
                    - ghost_positions, axis = -1)
    eta      = delta / maximum(effect, DELTA_FLOOR)
    return Comparison(delta, delta_v, effect, eta, max(delta), max(eta))
```

`ghost_positions` are displacements from the launch point (6.2), so
the effect subtracts the launch point from the transform's positions
before comparing.

## 6.2 `analysis/ghost_path.py`

```
function rotating_force_is_constant(field, frame) -> bool:
    # True when f_rot is a constant vector in rotating components:
    #   NoForce; UniformGravityFrameFixed; UniformGravitySpaceFixed
    #   with "rotating" among its potential's frames (axis parallel).
    return field.closed_form == "line"
        or field.closed_form == "rotating_parabola"
        or (field.potential is not None and "rotating" in
            field.potential.frames)

function ghost_derivative(field, frame) -> function(time, state_rot):
    # The rotating derivative with the pseudo-forces omitted: what the
    #   rider expects with no extra forces (Design 6.2).
    def derivative(time, state_rot):
        position_rot, velocity_rot = state_rot[:3], state_rot[3:]
        return concatenate(velocity_rot,
            field.acceleration_rotating(frame, time, position_rot,
                                        velocity_rot))
    return derivative

function ghost_path(field, frame, launch_in, launch_point_rot, times,
                    settings) -> (M, 3):
    # Displacements from the launch point, rotating components.
    position_rot0, velocity_rot0 = frame.to_rotating(0.0, *launch_in)
    if rotating_force_is_constant(field, frame):
        f_rot = field.acceleration_rotating(frame, 0.0, position_rot0,
                                            velocity_rot0)
        positions, _ = parabola(position_rot0, velocity_rot0, f_rot,
                                times)                # Pseudocode 4.1;
                                                      #   a line when f = 0
    else:
        integration = integrate(ghost_derivative(field, frame),
            concatenate(position_rot0, velocity_rot0), times,
            settings.integrator, settings.substeps, settings.rtol,
            settings.atol)
        positions = integration.states[:, :3]
    return positions - launch_point_rot
```

The ghost is evaluated at the store's sample times, including the
event sample, so that it lines up with the true path sample by
sample.

## 6.3 `analysis/conservation_monitor.py`

```
NOT_CONSERVED = {
    "E": "E is not conserved here: the force in the inertial frame "
         "depends on time (frame-fixed gravity).",
    "J": "J is not conserved here: the potential is not fixed in the "
         "rotating frame (space-fixed gravity on a tilted axis)."}

function energy(field, positions_in, velocities_in) -> (N,) | None:
    if field.potential is None or "inertial" not in field.potential.frames:
        return None
    return 0.5 * sum(velocities_in², axis = -1)
           + field.potential.energy(positions_in)                 # E

function jacobi(field, frame, positions_rot, velocities_rot)
        -> (N,) | None:                                           # (6.3)
    if field.potential is None or "rotating" not in field.potential.frames:
        return None
    omega = frame.angular_velocity(0.0)
    return 0.5 * sum(velocities_rot², axis = -1)
           + field.potential.energy(positions_rot)
           - 0.5 * sum(cross(omega, positions_rot)², axis = -1)

function scale(frame, field, launch_in, positions_rot) -> float:
    # Q_scale of Design 6.3: the size of the terms that go into E or J.
    speed0   = |launch velocity_in|
    g        = |field.acceleration(0, *launch_in)|
    rho_max  = max |positions_rot − positions_rot[0]|
    r_perp   = max |positions_rot less its axial part|
    return 0.5 * speed0² + g * rho_max + 0.5 * frame.rate² * r_perp²
           + 1e-30                                       # never zero

frozen record Conserved:
    energy_exact, energy_check       (N,) drift, or None
    jacobi_exact, jacobi_check       (N,) drift, or None
    scale                            float
    notes                            list of the NOT_CONSERVED sentences
                                     that apply

function monitor(field, frame, launch_in, inertial, rotating, check)
        -> Conserved:
    # inertial = (positions_in, velocities_in); rotating likewise;
    #   check = (positions_rot, velocities_rot) or None.
    q = scale(frame, field, launch_in, rotating.positions)
    def drift(values): return None if values is None
                              else (values - values[0]) / q
    energy_exact = drift(energy(field, *inertial))
    jacobi_exact = drift(jacobi(field, frame, *rotating))
    if check is None: energy_check = jacobi_check = None
    else:
        check_in = frame.to_inertial(times, *check)
        energy_check = drift(energy(field, *check_in))
        jacobi_check = drift(jacobi(field, frame, *check))
    notes = [NOT_CONSERVED["E"] if energy_exact is None else nothing,
             NOT_CONSERVED["J"] if jacobi_exact is None else nothing]
    return Conserved(...)
```

## 6.4 `analysis/closed_form_deflections.py`

```
OVERLAY_LIMIT = 0.1                    # rate × duration below which the
                                       #   first-order formula is offered

function overlay_applies(frame, duration) -> bool:
    return |frame.rate| * duration < OVERLAY_LIMIT

function first_order_deflection(frame, velocity_rot0, gravity_rot, times)
        -> (N, 3):                                                # (6.4)
    # Displacement from the ghost path, rotating components, to first
    #   order in the rate. gravity_rot is the rotating-component
    #   force per unit mass (zero for NoForce).
    omega = frame.angular_velocity(0.0)
    return -cross(omega, outer(times², velocity_rot0)
                         + outer(times³ / 3, gravity_rot))

function first_order_tolerance(frame, duration, earth_ratio) -> float:
    # The relative tolerance a test uses against (6.4), Design 6.5:
    #   2 (Ω² R_E / g₀) + (Ω t)². `earth_ratio` is Ω² R_E / g₀ for the
    #   Earth preset and 0 on a platform.
    return 2 * earth_ratio + (frame.rate * duration) ** 2
```

The classroom cases (the drop, the vertical launch, the horizontal
launch) are tests of this function, not functions of their own; the
overlay in the scene is `first_order_deflection` added to the ghost
path (Pseudocode 9).

## 6.5 `analysis/error_budget.py`: three columns

```
frozen record ErrorBudget:
    numerical      {"delta": float, "eta": float, "drift": float | None,
                    "max_delta", "max_eta", "max_drift"}
    approximation  {"estimate": float, "note": str} | None
    distortion     {"exaggeration": float, "arrow_ratio": float | None,
                    "camera_follows": bool}

function budget_at(comparison, conserved, field, spec, k, scene_info)
        -> ErrorBudget:
    numerical = {delta: comparison.delta[k], eta: comparison.eta[k],
                 drift: the check's J or E drift at k (whichever the
                        field conserves; None with the check off),
                 max_…: the run's maxima}
    approximation = None if field.approximation is None else
                    {estimate: field.approximation.estimate(spec.duration),
                     note: field.approximation.note formatted with it}
    distortion = {exaggeration: spec.exaggeration,
                  arrow_ratio: scene_info.arrow_ratio (Pseudocode 9.4),
                  camera_follows: scene_info.camera_follows}
    return ErrorBudget(numerical, approximation, distortion)
```

No function anywhere combines two columns: `tests/unit/
test_error_budget.py` parses every module under `analysis/` and
`render/` and asserts that no binary arithmetic node has, on both
sides, attribute accesses whose names are two different column names
(`numerical`, `approximation`, `distortion`), the scattering tool's
AST test adapted.

## 6.6 Verification

`test_comparison.py`:

- `run_check` with `rk4` on the free particle from the unit rim
  agrees with `frame.to_rotating` of the line to `C Δt̃⁴` with `C`
  stated; doubling `substeps` divides the maximum `delta` by a
  factor in `[14, 18]`; `euler` by `[1.8, 2.2]`; the check's sample
  `0` equals the transform's to `1e-15`.
- `compare` on identical arrays gives `delta = 0`, `eta = 0`; on a
  check offset by a constant `c` gives `delta = c` everywhere and
  `eta = c / effect` where `effect > DELTA_FLOOR`.

`test_ghost_path.py`:

- `rotating_force_is_constant` is true for `NoForce`, the frame-fixed
  field, and the space-fixed field on a vertical axis, and false for
  a space-fixed field on a tilted axis.
- The ghost of a frame-fixed drop is the plain parabola `−½ g̃ t̃² ê_U`
  (a straight fall in the rider's view), to `1e-14`; and `run_check`
  with a derivative whose terms are zeroed reproduces the ghost to
  the integrator's tolerance (the ghost is what the words say).

`test_conservation.py`:

- `energy` along an exact line and an exact space-fixed parabola is
  constant to `1e-13` of `scale`; `jacobi` along an exact frame-fixed
  run likewise; along an `rk4` check both drift by less than
  `C' Δt̃⁴`.
- A frame-fixed field yields `energy_exact = None` and the `E`
  sentence in `notes`; a space-fixed field on a vertical axis yields
  both drifts and no note.
- `scale` is positive for every packaged run and equals the stated
  sum for a hand-built case.

`test_deflections.py`:

- `overlay_applies` is true for a five-second Earth drop and false
  for a turntable run of one turn.
- The drop: `first_order_deflection` with `velocity_rot0 = 0` and the
  Earth's `gravity_rot` at `λ` gives `(1/3) g̃ Ω̃ t̃³ cos λ ê_E`, east,
  to `1e-14`, at three latitudes.
- The vertical launch: a `20 m/s` throw at `45°` returns west by
  `(4/3) v₀³ Ω cos λ / g²` at `t = 2 v₀/g`, `5.70 mm`, to `1e-12`
  (checked while Design 6 was written).
- The horizontal launch east at `45°`: the horizontal part of the
  deflection is to the right (south) with magnitude `Ω v₀ t² sin λ`
  and the vertical part is upward with magnitude `Ω v₀ t² cos λ`.
- Against the exact trajectories of Pseudocode 4 through the
  transform, the same three cases agree with `first_order_deflection`
  within `first_order_tolerance`, and the drop within the sharper
  factor of Pseudocode 4.6.

`test_error_budget.py`:

- `budget_at` fills the three columns from their three sources for a
  packaged Earth run and leaves `approximation` `None` for the
  turntable; the AST assertion of 6.5 passes on the tree and fails
  on a planted `numerical.delta + distortion.exaggeration`.
