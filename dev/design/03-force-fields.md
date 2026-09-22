# Design 3: The Force Fields

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.2 (`forces/`), 4.2
> (where gravity lives), and 6.3 (the force boundary); serves G4,
> NG5, and FD6. Uses Designs 1 and 2. *Status: draft.*

The first version has two force fields, none and uniform gravity,
and uniform gravity comes in two kinds. This section fixes the
interface every field satisfies, defines the three members, derives
the plumb line and the ground from the Earth's field, states the
condition under which the uniform approximation of the Earth's
gravity holds and how large its error is, and records what was
rejected.

---

## 3.1 The interface

A force field is an object that answers, in natural units and per
unit mass (Design 2.2), for a time and an inertial state:

```
  f_in(t̃, r̃_in, ṽ_in)  ->  acceleration, inertial components         (3.1)
```

and that declares three capabilities the rest of the tool asks for
by name, never by field type (P10, A6.3):

```
  closed_form     None, or a name the motion provider knows (Design 4):
                  "line", "parabola", "rotating_parabola"
  potential       None, or (frame, U) with frame in {"inertial",
                  "rotating"} and U(r̃) the potential energy per unit
                  mass in that frame's components (Design 6)
  approximation   None, or a note (text, and an error estimate as a
                  function of the run) that the screen shows (3.4)
```

A field that is defined through the frame (3.4) is constructed with
the `Frame` of Design 1 and keeps it; the interface (3.1) still
takes `t̃` and inertial components, so that the motion provider and
the check call every field the same way. The motion provider takes
the closed form when one is declared and integrates (3.1) otherwise;
Section 6 uses `potential` to know which of `E` and `J` should be
conserved; Section 9 prints the `approximation` note.

## 3.2 No force

```
  f_in = 0;   closed_form = "line";   potential = ("inertial", U = 0)
```

The turntable's puck: the disc's normal force cancels gravity and
the puck moves in the plane `z = 0`, in which it stays because
nothing pushes it out. Both `E` and `J` are conserved, since `U = 0`
is a function of either frame's components.

## 3.3 Uniform gravity, space-fixed

```
  f_in = g̃,  a constant vector in inertial components;
  closed_form = "parabola";   potential = ("inertial", U = −g̃ · r̃_in)
```

The room's gravity on a merry-go-round: `g̃ = g/(Ω² L)` along `−ẑ`.
`E` is conserved. When `n̂` is parallel to `g̃`, as it is for every
platform with a vertical axis, `R(t)ᵀ g̃ = g̃`, the field is constant
in rotating components too, `U` is a function of `r̃_rot` alone, and
`J` is conserved as well; the two kinds of uniform gravity coincide
(A4.2), and Section 6's monitor may report both.

## 3.4 Uniform gravity, frame-fixed

```
  g̃₀_rot   a constant vector in rotating components;
  f_in(t̃) = R(t̃) g̃₀_rot,  a rotating vector in inertial components;
  closed_form = "rotating_parabola";
  potential = ("rotating", U = −g̃₀_rot · r̃_rot);
  approximation = the note of 3.4.2
```

The uniform approximation of the Earth's central field, made at the
launch point `P` (A4.2): `g̃₀_rot = −g̃₀ r̂_P`, pointing from `P`
toward `O`, with `g̃₀ = g₀/(Ω² L)` and `g₀ = GM/R_E²` the bare
attraction (Design 2.4). In the inertial frame the vector turns at
`Ω`; the motion is still a closed form (Design 4). `J` is conserved,
because `U` is a function of `r̃_rot`; `E` is not, because the force
in the inertial frame depends on time.

### 3.4.1 The plumb line and the ground

At the launch point the centrifugal term of Design 1.4, per unit
mass, is `−Ω × (Ω × r_P)`, directed away from the axis with magnitude
`Ω² R_E cos λ`. Its sum with the attraction is what a plumb line
measures:

```
  g_eff = g₀_rot − Ω × (Ω × r_P),         ê_U = − g_eff / |g_eff|,
  |g_eff| = g₀ − Ω² R_E cos² λ  (to first order),
  tilt from r̂_P = Ω² R_E sin λ cos λ / g₀  (to first order).
```

The ground is the plane through `P` perpendicular to `ê_U`; the
local east and north are the index's `ê_E` along `n̂ × r_P` and
`ê_N = ê_U × ê_E`. A particle's height above the ground is
`h = ρ · ê_U` with `ρ = r_rot − r_P`, which is what the stopping rule
"lands" reads (Design 4). Away from `P` the centrifugal term differs
from its value at `P` by `−Ω × (Ω × ρ)`, of order `Ω² |ρ|`, which
Section 5 includes automatically since it evaluates the term at the
particle's position; nothing here special-cases it.

The tilt is `0.099°` at `λ = 45°` (Design 2.4). The tool draws `g₀`
and `F_cf` separately (G3), so a student sees that their sum, the
plumb line, is not quite radial; a ball dropped from rest in the
rotating frame falls along `ê_U`, not along `r̂_P`, before the
Coriolis term bends it east.

### 3.4.2 Where the approximation holds, and its error

The true field is central, `−g₀ (R_E/r)² r̂`, static in the inertial
frame. Replacing it by the constant `g̃₀_rot` neglects two things at
a displacement `ρ` from `P`: the change of direction, by an angle
`|ρ_h| / R_E` for a horizontal displacement, and the change of
magnitude, by `2 h / R_E` for a height `h`. The screen must say how
much that costs compared with the effect being shown.

The direction change produces an extra horizontal acceleration
`g₀ ρ_h / R_E` pointing back toward `P`: it is *along* the
displacement, so at first order it shortens a throw's range and does
not deflect it sideways. The Coriolis deflection is sideways. The
approximation's sideways effect comes only from the component of the
restoring acceleration along the deflection already made, `g₀ d /
R_E` with `d` the Coriolis deflection itself, so its size relative
to `d` is

```
  (g₀ d / R_E) t² / 2  ÷  d   ≈   g₀ t² / (2 R_E)   =   ½ (t / t_E)²,
                                   t_E = sqrt(R_E / g₀) ≈ 805 s.  (3.2)
```

The magnitude change over a drop of height `h = ½ g₀ t²` alters the
fall time, and hence every deflection, by the same relative amount,
`h / R_E ~ g₀ t² / (2 R_E)`. So the uniform approximation is good
while the flight is short compared with about thirteen minutes:
its relative error in the deflections is `½ (t / 805 s)²`, which is
`2 × 10⁻⁵` for a five-second drop and `3 × 10⁻³` for a minute in
the air. The field declares this as its `approximation`: a sentence
for the screen, and the estimate `½ (t̃_end / (Ω t_E))²` that the
tool evaluates and prints for the run in hand.

**Why this and not the central field now.** The central field turns
every Earth run into an arc of a Kepler ellipse, whose closed form
needs Kepler's equation and whose textbook oracles are then
approximations of the tool's own answer. The uniform field keeps the
closed forms of Design 4 and makes the textbook formulas exact
oracles, at a cost the tool states. Central gravity is FD6, and when
it arrives it is a fourth field behind (3.1), with `closed_form =
None` or a Kepler solver, and a run may be computed both ways to
show where (3.2) bites.

## 3.5 What the interface leaves room for (FD6, FD5)

- **Central gravity**: `f_in = −g̃₀ (R̃_E / r̃)² r̂`, static in the
  inertial frame, `potential = ("inertial", U = −g̃₀ R̃_E² / r̃)`;
  because `|r̃|` is the same in both frames, `U` is also a function of
  `r̃_rot` and both `E` and `J` are conserved.
- **A central attraction on the turntable** (the cyclone inflow) and
  **a spring**: potentials in whichever frame their center is fixed
  in; a center fixed on the turntable is a rotating-frame potential.
- **The pendulum's constraint** (FD5) is not a field: it is a
  reaction force that depends on the motion, and it would need the
  motion provider to grow a constraint step. That is why FD5 is a
  future direction and not a row in `fields.py`.

## 3.6 Rejected

- **The measured `g = 9.81 m/s²` as the uniform magnitude.** It
  already contains the centrifugal term; drawing `F_cf` separately
  would then count it twice, and the plumb line would come out
  tilted twice over (A4.2).
- **One kind of uniform gravity, chosen by the preset.** The run file
  states the kind, and the Earth preset accepts `space_fixed` too, so
  that a student can ask for the wrong physics on purpose and watch
  the eastward deflection come out wrong (Design 8 keeps the key;
  Design 6's oracles are for the right kind).
- **A height-dependent `g₀ (1 − 2h/R_E)`.** The same order as the
  direction change (3.2), so correcting one without the other buys
  nothing honest; both arrive together with the central field.

## 3.7 Verification

- The no-force field returns zero at every `(t̃, r̃, ṽ)`.
- The space-fixed field returns the same vector at every `t̃`, and,
  for `n̂ ∥ g̃`, the same rotating components at every `t̃`.
- The frame-fixed field returns `R(t̃) g̃₀_rot` at every `t̃`, to
  `1e-14`, and constant rotating components; for `n̂ ∥ g̃₀_rot` it
  agrees with the space-fixed field at every `t̃`, and for the Earth
  at `λ = 45°` the two differ at `t̃` by `2 g̃₀ sin(t̃/2)` in
  magnitude, the chord of the turned vector.
- `|g_eff|` at the equator is `g₀ − Ω² R_E` and the tilt at `45°` is
  `0.099°`, to four figures; `ê_U · ê_E = ê_U · ê_N = ê_E · ê_N = 0`
  and the triad is right-handed.
- Every declared `closed_form` name is one Design 4 offers, and a
  field declaring none is integrated (an integration test with a
  throwaway field).
- The `approximation` estimate for a run of duration `t_end` equals
  `½ (t_end / t_E)²` with `t_E = 805 s` to three figures.
- The potentials declared here make Section 6's monitor report the
  conserved quantity constant to the integrator's tolerance on every
  packaged run (integration test, Design 6).

## Sources

Taylor, *Classical Mechanics*, §9.8 (the plumb line and the
effective gravity, with the `0.1°` figure) and §9.9 (the free-fall
deflection); Goldstein, Poole, and Safko, *Classical Mechanics*, 3rd
ed., §4.10. The error estimate (3.2) is this section's own; the
Kepler alternative is standard two-body mechanics, Goldstein
chapter 3.
