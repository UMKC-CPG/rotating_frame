# Design 5: The Three Pseudo-Force Terms

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.5 (`pseudoforces/`);
> serves G3 (draw every term), G2 (the check integrates the same
> terms), P13 (one word), and P9. Uses Designs 1, 2, and 4.
> *Status: reviewed; ratified 2026-09-22.*

One small module evaluates the three terms, once, for two consumers
that must agree: the rotating-frame integration of Design 6 and the
results store that the display reads. This section fixes the
function, the properties every term has and the tests that hold
them, which vectors the two views draw, and the sign checks.

---

## 5.1 The one function

```
  terms(frame, t̃, r̃_rot, ṽ_rot)  ->  (f̃_cf, f̃_co, f̃_eu)              (5.1)

  f̃_cf = − Ω̃ × (Ω̃ × r̃_rot)          centrifugal
  f̃_co = − 2 Ω̃ × ṽ_rot               Coriolis
  f̃_eu = − (dΩ̃/dt̃) × r̃_rot          Euler
```

Per unit mass (Design 2.2), in natural units, in rotating components;
`Ω̃` and `dΩ̃/dt̃` are the frame's answers at `t̃` (Design 1.1), which
in the first version are `n̂` and `0`. The function is written once
over arrays: `r̃_rot` and `ṽ_rot` may carry leading axes for particles
and samples, and the three results have the same shape, so the store
evaluates a whole run in one call and the check evaluates one state
at one time with the same code.

**The inputs are the transform's, never the check's.** The store
calls (5.1) with the rotating state that Design 1.3 produced from the
exact inertial motion. The arrows a student sees are therefore the
terms at the true position and velocity, and a defect in the check
of Design 6 cannot move them. The check calls (5.1) with its own
current state, which is what an integrator must do; agreement
between the two trajectories then says the terms and the integration
are both right.

**Rejected: evaluating the terms in the renderer, or in the check
and copying them out.** The first puts physics inside the renderer
(P9); the second ties the arrows to the numerically weaker
description (P2).

## 5.2 What each term is

Write `r̃_⊥ = r̃_rot − (r̃_rot · n̂) n̂` for the part of the position
across the axis, and `ṽ_⊥` likewise for the velocity. Then, at
constant rate with `Ω̃ = Ω̃ n̂`:

```
  f̃_cf = Ω̃² r̃_⊥              away from the axis;  |f̃_cf| = Ω̃² |r̃_⊥|
  f̃_co = − 2 Ω̃ n̂ × ṽ_rot     ⟂ n̂ and ⟂ ṽ_rot;    |f̃_co| = 2 Ω̃ |ṽ_⊥|
  f̃_eu = 0                    until FD2
```

Three facts about them are what the tests of 5.5 hold and what the
screen's labels say:

- The centrifugal term depends on where the particle is and not on
  how it moves; it is the same for a particle at rest on the
  turntable and one flying over it. On the Earth it is
  `Ω² R_E cos λ` at the surface, `0.0339 m/s²` at the equator (Design
  2.4), and Design 3.4.1's plumb line is `g₀` plus this term at the
  launch point; (5.1) at the particle's actual position includes the
  small change away from `P` with no special case.
- The Coriolis term depends on how the particle moves and not on
  where it is; it does no work in the rotating frame, `f̃_co · ṽ_rot =
  0`, so it changes the direction of the rotating-frame velocity and
  never its magnitude. This is why a puck on a frictionless turntable
  keeps its rotating-frame speed while the centrifugal term alone
  changes it, and why the Jacobi integral of Design 6 has no Coriolis
  contribution.
- The Euler term is present in (5.1) with a zero coefficient so that
  the check, the store, and the display already carry a third arrow
  and FD2 turns it on without touching any of them.

## 5.3 What the two views draw (with Design 9)

The decomposition decided here is what Design 9 renders; the sizes
and colors are its business.

**The inertial view draws no pseudo-force.** It draws the true force
`f̃_in` and the velocity `ṽ_in` at the particle, and nothing else,
because an inertial observer needs nothing else: that absence is
half the lesson of the Purpose. The frame's triad is drawn turning,
so the student sees why the other observer will need more.

**The rotating view draws five arrows at the particle**: the true
force carried into rotating components, `f̃_rot = R(t̃)ᵀ f̃_in`; the
three terms of (5.1), each labeled with its word; and their sum,
`f̃_rot + f̃_cf + f̃_co + f̃_eu`, which is `ã_rot` and is what the
rotating observer calls the net force per unit mass. The velocity
`ṽ_rot` is drawn too. Any of the five can be hidden (Design 10). The
magnitudes are read out in real units with the scale note and the
exaggeration factor beside them (Design 2.6), and, when the run file
gives a mass, in newtons.

**Rejected: drawing the pseudo-forces in the inertial view as well,
dimmed.** It was considered because they are computable there (the
same vectors rotated by `R`). It was dropped because an arrow in the
inertial view says "a force acts here", and none does; a student who
sees pseudo-force arrows in both views has been told the opposite of
the point.

## 5.4 The sign checks

Two worked cases, both consequences of `Ω̃ > 0` counterclockwise
seen from `+n̂` (index, Design 1.8), are the first tests written:

1. **North at latitude `λ`** (Design 1.8): `f̃_co = + 2 Ω̃ ṽ sin λ ê_E`.
   East, to the right of the motion.
2. **Outward on the turntable**: a puck at radius `r̃` moving
   radially outward at speed `ṽ`, `ṽ_rot = ṽ r̂`, feels
   `f̃_co = − 2 Ω̃ ẑ × ṽ r̂ = − 2 Ω̃ ṽ φ̂`: clockwise, seen from above,
   for a counterclockwise turntable; to the right of its motion. At
   rest at the same radius it feels `f̃_co = 0` and
   `f̃_cf = Ω̃² r̃ r̂`, outward.

A tool that draws either arrow the other way has a sign wrong in
Design 1.2 to 1.4 or here, and nothing downstream would catch it,
because the check of Design 6 would agree with itself.

## 5.5 Verification

- For random states and axes: `f̃_cf · n̂ = 0`, `f̃_cf · r̃_⊥ ≥ 0`,
  `|f̃_cf| = Ω̃² |r̃_⊥|`; `f̃_co · n̂ = 0`, `f̃_co · ṽ_rot = 0`,
  `|f̃_co| = 2 Ω̃ |ṽ_⊥|`; `f̃_eu = 0`; all to `10⁻¹⁴`.
- The two sign checks of 5.4, numerically, at several latitudes and
  radii.
- **The terms close the equation of motion.** For every packaged run,
  differencing the store's transformed samples with a centered
  difference gives `ã_rot,k ≈ (ṽ_rot,k+1 − ṽ_rot,k−1) / (2 Δt̃)`, and
  `f̃_rot,k + f̃_cf,k + f̃_co,k + f̃_eu,k` agrees with it to the
  differencing error, `Δt̃² |d³r̃/dt̃³| / 6`, which for the closed forms
  is bounded by `Δt̃² Ω̃ (Ω̃² |r̃| + 2 Ω̃ |ṽ| + |g̃|) / 6` and is stated
  in the test. This is the test that would catch a term evaluated
  from the wrong velocity (`ṽ_in` in place of `ṽ_rot`), the commonest
  mistake in this subject.
- Shape: (5.1) on arrays of shape `(N_p, N, 3)` returns three arrays
  of that shape equal, element by element, to the function called
  on each state alone.
- The store's recorded terms equal (5.1) evaluated on the store's
  own rotating samples (they are the same call; the test guards a
  future refactor).

## Sources

Goldstein, Poole, and Safko, *Classical Mechanics*, 3rd ed., §4.10;
Taylor, *Classical Mechanics*, §9.5 to §9.7, whose figures 9.6 and
9.8 are the two sign checks of 5.4.
