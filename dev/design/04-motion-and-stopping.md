# Design 4: Motion and Stopping

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.4 (`motion/`) and 6.2
> (the motion-provider boundary); serves P1, P2, P10, G2, G5, and G7.
> Uses Designs 1 to 3. *Status: reviewed; ratified 2026-09-22.*

The motion provider turns a launch, a force field, a frame, and a
duration into inertial samples. This section fixes its contract, the
three closed forms and how the two small-angle functions in one of
them are evaluated, the sampling, the integrators that serve the
check and any future field, and the stopping rules with the exact
event they find.

---

## 4.1 The contract

```
  provide(launch, field, frame, t̃_end, stopping_rule, N, method)
      -> samples: t̃_k, r̃_in,k, ṽ_in,k for k = 0 … N−1,
         and the stop event, if any (4.5)                          (4.1)
```

`launch` is the inertial state at `t̃ = 0` (Design 1.5 has already
converted it). `method` is `"auto"`, `"closed_form"`, or
`"numerical"`: `"auto"` takes the field's declared closed form
(Design 3.1) when there is one and integrates otherwise;
`"closed_form"` refuses a field without one; `"numerical"` integrates
regardless, which is how a student sees an integrator's error against
an exact answer. Every consumer sees only the samples (P10). In the
first version every field has a closed form, so `"auto"` never
integrates the inertial motion; the integrators of 4.4 are used by
the check (Design 6).

## 4.2 The closed forms

In natural units per unit mass (Design 2), with `r̃₀`, `ṽ₀` the launch
and `g̃` the field's vector:

**Line** (no force):

```
  r̃(t̃) = r̃₀ + ṽ₀ t̃,            ṽ(t̃) = ṽ₀.                          (4.2)
```

**Parabola** (space-fixed uniform gravity):

```
  r̃(t̃) = r̃₀ + ṽ₀ t̃ + ½ g̃ t̃²,   ṽ(t̃) = ṽ₀ + g̃ t̃.                   (4.3)
```

**Rotating parabola** (frame-fixed uniform gravity). The field is
`f̃_in(t̃) = R(θ) g̃₀_rot` with `θ = Ω̃ t̃` (Design 3.4). Split `g̃₀_rot`
into its part along the axis, which the rotation leaves alone, and
its part across it, which turns:

```
  g̃_∥ = (g̃₀_rot · n̂) n̂,     g̃_⊥ = g̃₀_rot − g̃_∥,
  R(θ) g̃₀_rot = g̃_∥ + cos θ g̃_⊥ + sin θ (n̂ × g̃_⊥).
```

Integrating once and twice from `t̃ = 0`:

```
  ṽ(t̃) = ṽ₀ + g̃_∥ t̃ + (sin θ / Ω̃) g̃_⊥ + ((1 − cos θ) / Ω̃) n̂ × g̃_⊥
  r̃(t̃) = r̃₀ + ṽ₀ t̃ + ½ g̃_∥ t̃²
              + ((1 − cos θ) / Ω̃²) g̃_⊥ + ((θ − sin θ) / Ω̃²) n̂ × g̃_⊥   (4.4)
```

with `Ω̃ = 1` in the run's natural units, kept as a symbol so that the
form is right whatever the frame reports. For small `θ` the last two
coefficients are `½ t̃²` and `t̃³/6`: the first restores the parabola,
the second is the leading effect of the turning field, and it is
where the eastward deflection of a drop comes from (4.6). When
`g̃₀_rot ∥ n̂`, `g̃_⊥ = 0` and (4.4) is (4.3), which is the statement
of Design 3.3 that the two kinds coincide on a vertical axis.

**The two small-angle functions are evaluated without cancellation.**
On the Earth a five-second drop has `θ ≈ 3.6 × 10⁻⁴`, and
`θ − sin θ ≈ θ³/6 ≈ 8 × 10⁻¹²` computed as a difference of two
numbers near `3.6 × 10⁻⁴` keeps only about seven of its sixteen
digits. So `1 − cos θ` is evaluated as `2 sin²(θ/2)`, which is exact,
and `θ − sin θ` by its Taylor series through `θ⁹/9!` for `|θ| < 0.1`
(the next term is below `10⁻¹⁶` relative there) and directly above
that. This is a rule of the design and a test of 4.6, because the
quantity it protects is the deflection the tool exists to show.

## 4.3 Sampling

Samples are uniform in time: `t̃_k = k Δt̃`, `k = 0 … N−1`, with `N`
from the run file's fidelity table and `Δt̃ = t̃_end / (N − 1)`. A
closed form is evaluated at every `t̃_k` directly; there is no
stepping and no accumulated error, and a sample depends on nothing
but its own time (Design 1.3). Uniform samples are what make the
scrubber an index (G5) and what let the trail be drawn by slicing.

**Rejected: samples adaptive to the motion.** A closed form can be
sampled anywhere, so adaptivity buys nothing here, and it would make
the sample index mean different times in different runs.

## 4.4 The integrators

An integrator advances a state under an acceleration function. Two
callers use one: the check of Design 6, which integrates the
rotating-frame equation (2.1); and the provider in `"numerical"`
mode or for a field without a closed form, which integrates the
inertial equation `ã_in = f̃_in(t̃, r̃_in, ṽ_in)`. Both callers hand
the integrator an acceleration function and get samples back; the
integrator does not know which frame it is in.

Three schemes, selectable in the run file's fidelity table:

| Name | Scheme | Global error | Why it is offered |
| --- | --- | --- | --- |
| `euler` | forward Euler | `O(Δt̃)` | to see error grow, in |
| | | | a lecture |
| `rk4` | classical Runge–Kutta, fixed step | `O(Δt̃⁴)` | the |
| | | | default: deterministic, and its error is the lesson of P3 |
| `dop853` | Dormand–Prince 8(5,3), adaptive | set by `rtol`, | a |
| | (SciPy) | `atol` | tight reference |

A fixed-step scheme takes `n_substeps` steps between consecutive
samples and records the state at every sample time exactly, so that
the check's samples and the transform's samples are at the same
times with no interpolation. The adaptive scheme is asked for dense
output at the sample times. The step of a fixed scheme is therefore
`Δt̃ / n_substeps`, and halving it must reduce `rk4`'s error sixteen
times and `euler`'s twice (4.6).

**Why not a symplectic scheme.** The Coriolis term depends on
velocity, which is what the simple symplectic schemes (Störmer–Verlet
and kin) cannot take without an implicit step, and the check's job
is to disclose error, not to hide it. A structure-preserving scheme
is the rigid-body tool's FD4 problem, not this tool's.

## 4.5 Stopping rules

A run ends at `t̃_end`, or earlier when a stopping rule fires. The
first version has two rules besides the duration, one per stage:

```
  "lands"       h(t̃) = ρ̃(t̃) · ê_U  ≤ 0,   with h(0) > 0
  "leaves"      |ρ̃_h(t̃)| ≥ 1,             the disc's radius is L
```

`ρ̃` is the displacement from the launch point in rotating components
(Design 3.4.1) and `ρ̃_h` its part in the disc's plane. Each rule is a
scalar function of time built from the transform of the closed form.

**The event is found exactly, not at a sample.** The provider finds
the first sample `k` at which the rule holds, then locates the
crossing time `t̃_stop` in `(t̃_{k−1}, t̃_k]` by bracketed root finding
(Brent's method) on the rule's function, to a tolerance of `10⁻¹²`
in `t̃`; for a closed form the function is exact, and for an
integrated motion it is the dense output, accurate to the
integrator's order. The state at `t̃_stop` is evaluated from the same
source. The store (Design 8) then holds samples `0 … k−1` and, as
its last sample, the event state at `t̃_stop`; samples past the event
are not kept. The one non-uniform sample is flagged, and the trail
ends on the ground or at the rim. This is what makes the landing
offset of a drop an exact number the oracle of 4.6 can compare.

**A ring stops particle by particle.** Each member has its own event
and its own last sample; the store marks a member's samples past its
event as absent, and the display stops that trail while the others
continue.

**Rejected: the last sample before the crossing, or linear
interpolation between samples.** Both make the landing point depend
on `N`, and the deflection is a difference of two nearly equal
positions; an error of a fraction of a sample in the landing time
would swamp it.

## 4.6 Verification

- Each closed form agrees with `dop853` at `rtol = 10⁻¹²` on its
  own field to `10⁻¹⁰` relative, over a duration of several turns;
  (4.4) reduces to (4.3) when `g̃₀_rot ∥ n̂` exactly.
- The small-angle functions: `2 sin²(θ/2)` and the series for
  `θ − sin θ` agree with the direct expressions to `10⁻¹⁵` relative
  for `θ` in `[0.1, 10]`, and the series has all sixteen digits for
  `θ = 10⁻⁴` where the direct expression has seven (checked against
  an extended-precision evaluation).
- `rk4` on (2.1) against the transform: the error at fixed `t̃_end`
  falls sixteenfold when `n_substeps` doubles, and `euler`'s twofold.
- A stopping event: at `t̃_stop` the rule's function is zero to
  `10⁻¹²`, the last stored sample is that state, and no stored
  sample lies past it.
- **The drop oracle, with its tolerance derived.** A particle dropped
  from rest in the rotating frame at height `h` at latitude `λ`
  lands east of the point below it by

  ```
    d = (1/3) g Ω t³ cos λ  ×  (1 − Ω² R_E / g₀)  ×  (1 + O((Ω t)²)),
  ```

  with `t` the landing time. The textbook formula is the first
  factor; the second is exact to first order in `Ω² R_E/g₀` and
  independent of latitude, because the effective gravity is weaker
  by `(1 − Ω² R_E cos² λ / g₀)` and the plumb line's tilt turns the
  Coriolis factor into `cos(λ + tilt)`, which costs
  `(1 − Ω² R_E sin² λ / g₀)`, and the two multiply to `1 − Ω² R_E/g₀
  = 0.99655`. The spike `dev/spikes/drop_deflection.py` confirms the
  ratio to six figures at five latitudes and two heights. The test
  therefore compares the tool's landing offset with the textbook
  formula times `0.99655` at a relative tolerance of `10⁻⁵`, which is
  the size of the neglected `(Ω t)²` and `h/R_E` terms for a
  hundred-metre drop, and it is a *check on the tool*, not a fit: a
  sign error, a missing `Ω × r` in the launch, or the wrong kind of
  gravity each move the answer by far more.
- The northward landing offset of the same drop is second order:
  the spike finds it within `(Ω t)² h` in magnitude (four
  micrometres for a hundred-metre drop, `2.6 × 10⁻⁴` of the eastward
  offset), so the test bounds it by `(Ω t)² h`, an absolute
  tolerance, and not by a fraction of the eastward one.

## Sources

The rotating-vector integrals of (4.4) are elementary. The
integrators are the standard ones: Hairer, Nørsett, and Wanner,
*Solving Ordinary Differential Equations I*, for Dormand–Prince 8(5,3)
as SciPy implements it. The first-order drop formula is Taylor,
*Classical Mechanics*, §9.9 and Goldstein §4.10; the correction
factor is this section's own, verified by the spike.
