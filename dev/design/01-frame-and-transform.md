# Design 1: The Frame and the Transform

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 2.3 (the frame is an
> object) and 6.6 in part; serves P2 and G2 (the inertial frame
> drives, the rotating frame is a transform), NG3 (a fixed axis
> through a fixed origin), and leaves FD1 and FD2 open. Notation is
> the index's. *Status: draft.*

Every other section uses this one. It fixes what the `Frame` object
holds, how the rotation `R(t)` is built, how a position and a
velocity are carried between the two descriptions, where the three
pseudo-force terms come from, and the one worked sign check that
every later formula must agree with.

---

## 1.1 What the frame holds

A rotating frame in the first version is three things (NG3):

- the origin `O`, shared with the inertial frame and on the axis;
- the unit axis `n̂`, fixed in both frames;
- the signed rate `Ω`, constant, with `Ω > 0` counterclockwise seen
  from `+n̂`.

From these the frame answers four questions, and nothing else in the
tool computes any of them (A2.3):

```
  θ(t)        the angle turned since t = 0             = Ω t
  Ω(t)        the angular velocity vector              = Ω n̂
  dΩ/dt (t)   its rate of change                       = 0
  R(t)        the rotation by θ(t) about n̂             (1.2)
```

The frame stores `Ω` as a number and does not assume the natural
units of Section 2, in which `Ω̃ = 1`; that assumption belongs to the
boundary, so that a varying rate (FD2) changes `θ(t)` and `dΩ/dt`
and nothing that asks for them.

**One axis, two frames.** Because `R(t)` rotates about `n̂`,
`R(t) n̂ = n̂`, and the angular velocity has the same components in
both frames: `Ω_in = Ω_rot = Ω n̂`, and likewise `dΩ/dt`. This is
why the pseudo-force formulas of the index carry `Ω` without a
subscript, and it is a property of a fixed axis that FD1 keeps and
a tumbling frame would not.

## 1.2 The rotation

`R(t)` is the right-handed rotation by `θ` about `n̂`, in Rodrigues'
form:

```
  R(θ) = cos θ I + sin θ [n̂]ₓ + (1 − cos θ) n̂ n̂ᵀ,

           ⎡  0   −n_z   n_y ⎤
  [n̂]ₓ =  ⎢  n_z   0   −n_x ⎥ ,     so that  [n̂]ₓ u = n̂ × u.
           ⎣ −n_y  n_x    0  ⎦
```

It is orthogonal with determinant `+1`, `R(θ) n̂ = n̂`, `R(0) = I`,
and rotations about one axis compose by adding angles, `R(θ₁)R(θ₂)
= R(θ₁ + θ₂)`. Its inverse is its transpose. The time derivative is
`Ṙ = Ω [n̂]ₓ R = [Ω]ₓ R`, which is the statement that a vector fixed
in the rotating frame moves with velocity `Ω × (·)` in the inertial
one; it is the source of every term in 1.4.

**Why a matrix and not a quaternion or vedo's transforms.** For a
single fixed axis a quaternion buys nothing, and the matrix is the
object a student meets in Goldstein §4.9: the columns of `R(t)` are
the rotating frame's axes as the inertial observer sees them, which
is exactly what the inertial view draws (1.6). vedo's own transform
objects are a rendering convenience and would put the physics inside
the renderer, against P9.

**Why the angle is never accumulated.** `θ(t_k) = Ω t_k` is computed
from the sample time at every sample, never by `θ += Ω Δt`. The
accumulated form drifts by rounding at every step and, worse, makes
the frame's position depend on the sample count; the direct form is
exact to one rounding, and reverse scrubbing (G5) reads the same
values. For the Earth over hours `θ` is thousands of radians and
double precision sine and cosine remain accurate to `1e-16` relative
at that size; no reduction modulo `2π` is needed or done.

## 1.3 Position and velocity between the frames

A particle at `r` (a geometric vector from `O`) has components
`r_in` in the inertial axes and `r_rot` in the rotating ones:

```
  r_in = R(t) r_rot,          r_rot = R(t)ᵀ r_in.                 (1.1)
```

Differentiating the first with respect to time, using `Ṙ = [Ω]ₓ R`
and writing `v_rot = d r_rot / dt` for the velocity the rotating
observer measures:

```
  v_in = Ω × r_in + R v_rot,
  v_rot = R(t)ᵀ (v_in − Ω × r_in).                                (1.2)
```

A particle at rest in the rotating frame (`v_rot = 0`) therefore has
`v_in = Ω × r_in`, the rim speed of the turntable at that radius,
which is the first check in 1.8.

Differentiating once more, with `a_rot = d v_rot / dt`:

```
  a_in = R [ a_rot + 2 Ω × v_rot + Ω × (Ω × r_rot)
                   + (dΩ/dt) × r_rot ],                            (1.3)
```

where every product on the right is taken in rotating components
(the same numbers, by 1.1, since `Ω` is along `n̂`). This is
Goldstein's equation (4.86) with the frame's origin at rest; the
term in `dΩ/dt` is present because the frame object promises it, and
is zero in the first version.

**The transform is applied per sample, exactly.** The motion
provider (Section 4) delivers `r_in` and `v_in` at the sample times
`t_k`. For each `k`, the store's rotating description is (1.1) and
(1.2) evaluated with `R(t_k)`:

```
  for k in 0 … N−1:
      Rₖ         = R(θ(t_k))
      r_rot,k    = Rₖᵀ r_in,k
      v_rot,k    = Rₖᵀ (v_in,k − Ω × r_in,k)
```

Nothing is integrated and nothing accumulates: the rotating
description at sample `k` depends only on the inertial state at
sample `k` and on `t_k`. That is the whole content of P2 at this
level, and it is what makes reverse scrubbing exact and the check of
Section 6 meaningful.

## 1.4 The rotating-frame equation of motion

Newton's law holds in the inertial frame, `m a_in = F`. Substituting
(1.3) and moving everything but `m a_rot` to the right, in rotating
components:

```
  m a_rot = F_rot  −  m Ω × (Ω × r_rot)  −  2 m Ω × v_rot
                   −  m (dΩ/dt) × r_rot,                            (1.4)
```

with `F_rot = R(t)ᵀ F_in` the true force carried into rotating
components. The three subtracted terms are the pseudo-forces of the
index:

```
  F_cf = − m Ω × (Ω × r_rot)        centrifugal, away from the axis
  F_co = − 2 m Ω × v_rot            Coriolis, perpendicular to v_rot
  F_eu = − m (dΩ/dt) × r_rot        Euler, zero at constant rate
```

Two facts about them are fixed here and used everywhere:

- **They are functions of the rotating state and the frame only:**
  `(Ω, dΩ/dt, r_rot, v_rot)`. Section 5 evaluates them, once, in a
  module both the display and the check import (A3.5). Nothing about
  the true force enters them.
- **They are what the check integrates.** Section 6 integrates (1.4)
  numerically from the same launch and compares `r_rot^check` with
  the transform (1.1). Agreement means the three terms are complete
  and correctly signed; nothing else in the tool would notice a
  wrong sign in `F_co`, because the display never uses (1.4).

**Rejected: integrating (1.4) and transforming back for the inertial
view.** It would make the numerically weaker description the source
of the picture and the exact one a derived quantity, which inverts
P2. The rotating-frame integration is a check, drawn beside the
transform and never in its place.

## 1.5 Launches

A launch (Section 7) is a position and a velocity at `t = 0`, given
in whichever frame the student means. Since `R(0) = I`, the two
descriptions coincide for positions at `t = 0`, and (1.2) gives the
velocity:

```
  given in the rotating frame:  r_in(0) = r_rot(0)
                                v_in(0) = v_rot(0) + Ω × r_rot(0)
  given in the inertial frame:  as given
```

"I threw it straight at the center" is a rotating-frame launch and
acquires the rim speed sideways in the inertial frame; "the ball was
already moving in the room" is an inertial one. The conversion is
done once, here, before the motion provider runs, and the run file
records which frame the launch was given in (Section 8).

## 1.6 What the frame gives the display

The geometry of Section 9 asks the frame for two triads and one
point, all at a sample time:

- the rotating frame's axes in the inertial view: the columns of
  `R(t_k)`;
- the inertial axes in the rotating view: the columns of `R(t_k)ᵀ`;
- the launch point `P`: `r_P` is fixed in rotating components, and
  is `R(t_k) r_P` in the inertial view.

In natural units with `Ω̃ = 1`, `θ = t̃`, so the rotating triad in
the inertial view has turned by exactly the elapsed dimensionless
time, which is a useful thing to read off the screen.

## 1.7 What the frame promises for later

The `Frame` is an object with the four answers of 1.1 and the two
transforms of 1.3, each taking `t`. That is the whole interface, and
it is what leaves the doors open:

- **A varying rate (FD2)** replaces `θ(t) = Ω t` by `∫₀ᵗ Ω dt'`,
  makes `dΩ/dt` nonzero, and changes nothing in (1.1) to (1.4); the
  Euler term, present with a zero coefficient now, becomes visible.
- **A translating origin (FD1)** adds the origin's motion `r_O(t)`,
  `v_O(t)`, `a_O(t)` to the frame's answers; (1.1) and (1.2) subtract
  them, and (1.4) gains one more term, `−m a_O`, in the same list.
  The interface takes `t` everywhere for this reason.

**Rejected: putting the origin at the launch point.** For the Earth
runs a frame with its origin at `P` would keep the stored numbers
small. It would also make the origin accelerate, so that (1.4) would
gain the `−m a_O` term of FD1 now, and the centrifugal term would
split into a constant part hidden in `a_O` and a small residual in
`F_cf`. The one-term-per-vector picture of G3 would be lost, and the
plumb line would no longer be `g₀ + F_cf/m`. Positions are kept from
`O` on the axis (A4.2); double precision holds `R_E` and a
millimetre at once.

## 1.8 The sign check

Every formula above is right-handed with `Ω > 0` counterclockwise
seen from `+n̂`. The check that fixes every sign in the tool, worked
once here so that Section 5's tests and the classroom can point at
it:

Take the Earth frame, `n̂ = ẑ` pointing north, a launch point at
latitude `λ > 0` in the `x`–`z` plane, `r_P = R_E (cos λ, 0, sin λ)`,
and the local axes of the index: `ê_E` along `n̂ × r_P`, which is
`+ŷ`; `ê_N = (−sin λ, 0, cos λ)`; `ê_U` radial for this check,
`(cos λ, 0, sin λ)`. A particle moving north at speed `v`,
`v_rot = v ê_N`, feels

```
  F_co = − 2 m Ω ẑ × v (−sin λ, 0, cos λ)
       = − 2 m Ω v (−sin λ) (ẑ × x̂)
       = + 2 m Ω v sin λ  ŷ                    = + 2 m Ω v sin λ  ê_E.
```

Moving north in the northern hemisphere, it is pushed east: to the
right of its motion, as the trade winds, the rivers, and the
textbooks say. A tool that gets a west out of this has a sign wrong
somewhere in 1.2 to 1.4, and the test that encodes this line is the
first one written for Section 5. The same computation for a particle
moving east gives `F_co` with a southward horizontal part and an
upward vertical part, the Eötvös effect, which is why the vertical
Coriolis component matters and why the tool is three-dimensional
throughout (A4.1).

## 1.9 Verification

What a test of this section holds, before any physics is run:

- `R(θ)` is orthogonal with determinant `+1` for a set of axes and
  angles including `0`, `π/2`, `π`, and `10⁴`; `R(θ) n̂ = n̂`;
  `R(θ₁) R(θ₂) = R(θ₁ + θ₂)`; all to `1e-14`, the rounding of a
  handful of products.
- The round trip inertial → rotating → inertial of a position and a
  velocity is the identity to `1e-14`.
- A particle at rest in the rotating frame at distance `d` from the
  axis has inertial speed `Ω d`, directed along `n̂ × r`.
- `|r_rot| = |r_in|` at every sample of a run.
- The launch conversion of 1.5 for a rotating-frame launch toward
  the center yields an inertial velocity whose component along
  `n̂ × r` is the rim speed.
- The sign check of 1.8, numerically, for several latitudes.

## Sources

Goldstein, Poole, and Safko, *Classical Mechanics*, 3rd ed., §4.9
(the rate of change of a vector) and §4.10 (the Coriolis force),
whose equation (4.86) is (1.3) above. Taylor, *Classical Mechanics*,
chapter 9, for the same equation in the form (1.4) and for the
sign conventions of the Earth examples. Rodrigues' rotation formula
is standard and is stated, for example, in Goldstein §4.6.
