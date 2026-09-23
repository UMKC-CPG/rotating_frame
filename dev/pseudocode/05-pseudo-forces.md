# Pseudocode 5: The Three Pseudo-Force Terms

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 5. Governs
> `src/rotating_frame/pseudoforces/terms.py` and
> `tests/unit/test_terms.py`. *Status: reviewed; ratified 2026-09-22.*

New code. `pseudoforces/` imports `core/` (the `Frame`) and nothing
else (A5). One module, one function of consequence, two callers that
must agree: the rotating derivative of Pseudocode 4.2 and the store
of Pseudocode 8. Per unit mass, natural units, rotating components.

---

## 5.1 `pseudoforces/terms.py`

```
TERM_NAMES = ("centrifugal", "coriolis", "euler")    # the order of the
                                                     #   store's term axis

function terms(frame, time, position_rot, velocity_rot)
        -> (centrifugal, coriolis, euler):                   # (5.1)
    # Each result has the shape of `position_rot`: (3,), (N, 3), or
    #   (N_p, N, 3). `time` is a scalar or matches the leading axes;
    #   it is passed to the frame, which in the first version ignores
    #   it (Pseudocode 1.3).
    omega     = frame.angular_velocity(time)              # (…, 3)
    omega_dot = frame.angular_acceleration(time)          # (…, 3)
    centrifugal = -cross(omega, cross(omega, position_rot))
    coriolis    = -2 * cross(omega, velocity_rot)
    euler       = -cross(omega_dot, position_rot)
    return centrifugal, coriolis, euler

function stacked(frame, time, position_rot, velocity_rot) -> (…, 3, 3):
    # The three terms on one axis, in TERM_NAMES order, for the store
    #   (Pseudocode 8.5): stack(terms(...), axis = -2).

function total(frame, time, position_rot, velocity_rot) -> (…, 3):
    # The sum, for the rotating derivative and for the "sum" arrow.
    return sum of terms(...)
```

`cross` is NumPy's, which broadcasts over leading axes; the frame's
`angular_velocity` broadcasts to the time's shape, and for a scalar
time NumPy's rules broadcast the `(3,)` vector against `(…, 3)`.
Nothing here special-cases the Earth: the centrifugal term at a
surface point comes out of the same cross product as on the
turntable (Design 5.2).

## 5.2 What calls it, and with what

- **The rotating derivative** (Pseudocode 4.2) calls `terms` at the
  check's own current state, one scalar time and one state at a time.
- **The store** (Pseudocode 8.5) calls `stacked` once over the whole
  run, on the rotating arrays that the transform produced from the
  exact inertial motion (Design 5.1), with `time` the sample-time
  array broadcast against the particle axis.
- **The scene** (Pseudocode 9) reads the store's terms; it never
  calls this module.

The second and third points are the ground-truth rule (A6.1): the
arrows come from the transform, and a defect in the check cannot
move them.

## 5.3 Verification (`tests/unit/test_terms.py`)

With `frame = Frame(ẑ, 1.0)` unless stated, random `position_rot`
and `velocity_rot`, and tolerance `1e-14`:

- `centrifugal · axis = 0`; `centrifugal · r_⊥ ≥ 0`;
  `|centrifugal| = rate² |r_⊥|`, with `r_⊥` the position less its
  axial part (Design 5.2); for `frame = Frame(ẑ, −1.0)` the same
  (the centrifugal term is even in the rate).
- `coriolis · axis = 0`; `coriolis · velocity_rot = 0`;
  `|coriolis| = 2 |rate| |v_⊥|`; reversing the rate reverses it.
- `euler` is identically zero (`angular_acceleration` is zero).
- **Sign check 1 (Design 1.8, 5.4):** `velocity_rot = (−sin λ, 0,
  cos λ)` gives `coriolis = (0, 2 sin λ, 0)` for `λ` in
  `{10°, 45°, 80°}`: east, for a northward motion.
- **Sign check 2 (Design 5.4):** at `position_rot = (r, 0, 0)` with
  `velocity_rot = (v, 0, 0)` (outward on the turntable), `coriolis =
  (0, −2v, 0)`, clockwise seen from `+ẑ`; at rest there,
  `coriolis = 0` and `centrifugal = (r, 0, 0)`.
- `stacked` has shape `(…, 3, 3)` with the terms in `TERM_NAMES`
  order, and `total` equals their sum.
- Shapes: on `(N_p, N, 3)` inputs with `time` of shape `(N,)`, every
  result is `(N_p, N, 3)` and equals, element by element, the
  function called on each `(i, k)` state alone.
- **Closure (Design 5.5), as an integration test in
  `tests/integration/test_closure.py`:** for every packaged run, the
  centered difference of the store's rotating velocities,
  `(v_rot[k+1] − v_rot[k−1]) / (2 Δt̃)`, agrees with
  `true_force[k] + total[k]` at interior samples to the bound of
  Design 5.5, `Δt̃² (rate² v_max + 2 rate a_max) / 6 + ε (v_max + rate
  r_max) / Δt̃` with `a_max = f_max + rate² r_max + 2 rate v_max` and
  `ε = 2.2e-16`, evaluated from the run's own maxima and written
  into the assertion message; the same test with `velocity_in` fed
  to `terms` in place of `velocity_rot` fails, which is asserted, so
  that the test is known to catch the mistake it exists for.
