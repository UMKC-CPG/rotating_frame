# Pseudocode 3: The Force Fields

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 3. Governs
> `src/rotating_frame/forces/force_interface.py`, `forces/fields.py`,
> and `tests/unit/test_fields.py`. *Status: reviewed; ratified 2026-09-22.*

New code. `forces/` imports `core/` (the `Frame` of Pseudocode 1)
and nothing else. Everything is in natural units per unit mass, and
`acceleration` always takes and returns inertial components; the
frame-fixed field holds a `Frame` to make that so.

---

## 3.1 `forces/force_interface.py`: the contract

```
frozen record Potential:
    frames    frozenset of "inertial" and/or "rotating": the frames in
              which `energy` is a function of position alone, so that
              E or J is conserved (Design 6.3)
    energy    function(position) -> float or (N,): the potential
              energy per unit mass; when both frames are declared the
              vector it dots with has the same components in both, so
              either frame's position may be passed

frozen record Approximation:
    note       one sentence for the screen (Design 3.4.2)
    timescale  t_E in natural units
    method estimate(duration_natural) -> float:
        return 0.5 * (duration_natural / timescale) ** 2      # (3.2)

abstract class ForceField:
    closed_form    None | "line" | "parabola" | "rotating_parabola"
    potential      Potential | None
    approximation  Approximation | None

    abstract method acceleration(time, position_in, velocity_in)
            -> (..., 3):                                       # (3.1)
        # Vectorized over leading axes of `time` (N,) and the states
        #   (N, 3), or a scalar time with a single state.

    method acceleration_rotating(frame, time, position_rot, velocity_rot)
            -> (..., 3):
        # The same force in rotating components, for the check
        #   (Design 6.1): carry the state out, ask, carry the answer
        #   back. Concrete here so that no field repeats it.
        position_in, velocity_in = frame.to_inertial(time, position_rot,
                                                     velocity_rot)
        R = frame.rotation(time)
        return Rᵀ @ self.acceleration(time, position_in, velocity_in)
```

`closed_form`'s names are the ones Pseudocode 4 dispatches on; a
name not in that set is a programming error caught by the test of
Design 3.7, not a run-file error.

## 3.2 `forces/fields.py`: the three members

```
class NoForce(ForceField):
    closed_form   = "line"
    potential     = Potential(frames = {"inertial", "rotating"},
                              energy = lambda position: zeros(leading
                                                              shape))
    approximation = None
    method acceleration(time, position_in, velocity_in):
        return zeros_like(position_in)

class UniformGravitySpaceFixed(ForceField):
    constructor (gravity_in, frame):
        # gravity_in: the constant vector g̃ in inertial components.
        self.gravity_in = gravity_in
        parallel = |cross(frame.axis, gravity_in)| < 1e-12 * |gravity_in|
        frames = {"inertial"} ∪ ({"rotating"} if parallel else ∅)
        self.potential = Potential(frames,
            energy = lambda position: -(position @ gravity_in))
        self.closed_form = "parabola"; self.approximation = None
    method acceleration(time, position_in, velocity_in):
        return broadcast(self.gravity_in, position_in.shape)

class UniformGravityFrameFixed(ForceField):
    constructor (gravity_rot, frame, approximation):
        # gravity_rot: the constant vector g̃₀_rot in rotating
        #   components (Design 3.4); approximation: the record of 3.1,
        #   built by run/ from the preset's radius and g0 (Pseudocode 8).
        self.gravity_rot = gravity_rot; self.frame = frame
        self.potential = Potential({"rotating"},
            energy = lambda position_rot: -(position_rot @ gravity_rot))
        self.closed_form = "rotating_parabola"
        self.approximation = approximation
    method acceleration(time, position_in, velocity_in):
        R = self.frame.rotation(time)                     # (N, 3, 3)
        return R @ self.gravity_rot                        # rotating vector

function make_field(kind, fixed_in, gravity_vector, frame,
                    approximation) -> ForceField:
    # Called by run/ (Pseudocode 8) with the resolved, natural-unit
    #   values. `gravity_vector` is in inertial components for
    #   "space" and rotating components for "frame"; at t = 0 the two
    #   coincide (R(0) = I), which is why one key can serve both.
    if kind == "none":        return NoForce()
    if fixed_in == "space":   return UniformGravitySpaceFixed(gravity_vector,
                                                              frame)
    if fixed_in == "frame":   return UniformGravityFrameFixed(gravity_vector,
                                                              frame,
                                                              approximation)
    raise ValueError(f"force: kind {kind!r} with fixed_in {fixed_in!r}")
```

The approximation note's text, fixed here so the screen and the
tests agree:

```
"Gravity is uniform here by approximation: the Earth's central field
 is replaced by its value at the launch point. Good while the flight
 is short compared with sqrt(R_E/g0) ≈ 805 s; the relative error in
 the deflections for this run is {estimate:.1e}."
```

## 3.3 Verification (`tests/unit/test_fields.py`)

With `frame = Frame(ẑ, 1.0)` unless stated, random states, and
tolerance `1e-14`:

- `NoForce().acceleration` returns zeros of the input's shape, for a
  single state and for `(N, 3)`; its potential declares both frames
  and its energy is zero.
- `UniformGravitySpaceFixed(g, frame)` returns `g` at every time, in
  both call shapes; with `g ∥ ẑ` its potential declares both frames,
  with `g` tilted it declares `{"inertial"}` only; `energy(r) =
  −g · r`.
- `UniformGravityFrameFixed(g_rot, frame, approx)`: `acceleration(t)`
  equals `frame.rotation(t) @ g_rot`; its rotating components,
  `acceleration_rotating(frame, t, r_rot, v_rot)`, equal `g_rot` at
  every `t` (the defining property); for `g_rot ∥ ẑ` it agrees with
  the space-fixed field at every `t`; for the Earth at `45°` the two
  differ at `t` by `2 |g_⊥| sin(t/2)` in magnitude.
- `acceleration_rotating` for every field equals `Rᵀ` applied to
  `acceleration` at the carried-out state (the interface method
  against the direct computation).
- `Approximation(note, timescale).estimate(d) == 0.5 (d/timescale)²`;
  with the Earth's `t_E = 805.5 s` converted to natural units at the
  sidereal rate, `estimate` of a five-second drop is `1.9e-5` to two
  figures.
- Every field's `closed_form` is in `{"line", "parabola",
  "rotating_parabola"}`, the set Pseudocode 4 dispatches on.
- `make_field` returns the right class for the three combinations
  and raises for `("uniform", None, ...)` and for an unknown kind.
- The plumb-line numbers of Design 3.7 (`|g_eff|` at the equator,
  the tilt at `45°`) are tested in `test_presets.py` (Pseudocode
  2.5), where the vector is built.
