# Design 6: The Check and the Error Budget

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.6 (`analysis/`) and
> the comparison half of 6.1; serves G2 (integrate in the rotating
> frame and show the difference), G7 (closed forms as oracles), P2,
> and P3 (numerical error disclosed and kept apart). Uses Designs 1
> to 5. *Status: draft.*

The rotating-frame integration exists to be compared with the
transform. This section fixes how it is run, what is compared and
against what, the ghost path that gives the comparison its scale,
the two conserved quantities and which field conserves which, the
three kinds of error the screen keeps in separate columns, and the
first-order deflection formulas that serve as overlays and oracles.

---

## 6.1 The check

The check integrates the rotating-frame equation (2.1), per unit
mass in natural units, in rotating components, from the same launch:

```
  r̃_rot(0) = r̃_in(0),   ṽ_rot(0) = ṽ_in(0) − Ω̃ × r̃_in(0)   (Design 1.5)
  ã_rot = f̃_rot + f̃_cf + f̃_co + f̃_eu,                              (6.1)
  f̃_rot(t̃, r̃_rot, ṽ_rot) = R(t̃)ᵀ f̃_in(t̃, R r̃_rot, R ṽ_rot + Ω̃ × R r̃_rot),
```

with the three terms from Design 5.1 at the check's own current
state, and the integrator, substeps, and tolerances from the run
file's `[check]` table (Design 8), defaulting to fixed-step `rk4`
with four substeps per sample. The integrator records the state at
every sample time exactly (Design 4.4), so the check's `k`-th sample
and the transform's are at the same `t̃_k`. The check runs by
default, because it is cheap (a few thousand evaluations of (6.1)
per particle) and because it is the lesson; a run file may switch it
off.

**The check reads only the launch, the field, and the frame.** It
does not see the transform's samples (A6.1); the store receives its
trajectory and the comparison below, and nothing that draws reads
the trajectory itself except to draw it as the check's path when
asked (Design 9).

## 6.2 The comparison, and the ghost path that scales it

At every sample:

```
  δ̃_k   = | r̃_rot^check,k − r̃_rot,k |          position error
  δ̃ṽ_k  = | ṽ_rot^check,k − ṽ_rot,k |          velocity error          (6.2)
```

These are in natural units, so `δ̃` is already the error as a
fraction of `L`. That is not the scale a student needs. On the
Earth the whole effect the tool shows, the deflection, is
`1.5 × 10⁻⁴ L` for a hundred-metre drop, and an error of `10⁻⁶ L`
is a hundredth of a deflection and not a millionth of the picture.
The comparison therefore also reports the error against the size of
the effect:

```
  Δ̃_k  = ρ̃_rot,k − ρ̃_ghost,k        the pseudo-force effect at k
  ε_k   = δ̃_k / max(|Δ̃_k|, δ̃_floor)   error as a fraction of the effect
```

where the **ghost path** `ρ̃_ghost` is what the rotating observer
would predict with no pseudo-forces at all: the motion under `f̃_rot`
alone, from the same rotating-frame launch. For the first version's
fields `f̃_rot` is constant in rotating components (Design 3.3, 3.4),
so the ghost is a line or a parabola in the rotating frame, a closed
form; for a future field it is integrated like the check. `δ̃_floor`
is a small number, `10⁻⁹`, that keeps the ratio finite at `t̃ = 0`,
where the effect is zero.

The ghost path is also drawn, dashed, in the rotating view (Design
9), because it is the picture of the mistake: "where I would have
expected the ball to go." The gap between the ghost and the true
path *is* the pseudo-forces, and the check's error is judged against
that gap. This is P3 made concrete: a student can always tell
whether what is on screen is physics or numerics, because the screen
says what fraction of the visible effect the numerics could account
for.

**What the check proves when it agrees.** The transform is exact
(Design 1.3) and the closed form is exact (Design 4.2); the check is
an independent computation of the same motion from (6.1). Agreement
to the integrator's tolerance says that the three terms of Design 5
are complete and correctly signed and that the launch conversion is
right. Disagreement beyond it says the rotating-frame code is wrong
(P2); the transform is never adjusted to meet the check.

## 6.3 The conserved quantities

Two are monitored, per unit mass, along both the exact trajectory
and the check's:

```
  E  = ½ |ṽ_in|²  + U_in(r̃_in)              energy, inertial frame
  J  = ½ |ṽ_rot|² + U_rot(r̃_rot) − ½ |Ω̃ × r̃|²  Jacobi integral       (6.3)
```

Which one is conserved is what the field declares (Design 3.1): a
field with an inertial potential conserves `E`; a field with a
rotating potential conserves `J`, whose last term is the centrifugal
potential and which has no Coriolis contribution because that term
does no work (Design 5.2). No force and space-fixed gravity on a
vertical axis declare both; frame-fixed gravity declares `J` only,
and its `E` is not conserved because the inertial-frame force
depends on time, which the monitor says in words rather than
reporting a drift as if it were an error.

The monitor reports, for each declared quantity, the drift `Q_k −
Q_0` relative to a scale `Q_scale = ½ |ṽ₀|² + |g̃| |ρ̃|_max + ½ Ω̃²
|r̃_⊥|²_max`, the size of the terms that go into it, so that a
large-radius Earth run does not make a tiny drift look tinier. Along
the exact trajectory the drift is rounding, `10⁻¹⁴` or so, and its
being that small is a test of the closed forms; along the check it
is the integrator's, and it is a second, independent measure of the
same numerical error `δ̃` reports.

## 6.4 Three kinds of error, never combined

The screen has an error panel (Design 9) with three columns, and
nothing is ever added across them (P3):

| Column | What it holds | Where it comes from |
| --- | --- | --- |
| **numerical** | `δ̃_k`, `ε_k`, and the drift of `E` or `J` | 6.2, 6.3 |
| | along the check | |
| **approximation** | the field's declared estimate, for the | Design 3.4.2 |
| | Earth `½ (t̃_end / (Ω t_E))²`, and its words | |
| **distortion** | the exaggeration factor `α` when it is not | Design 2.6, |
| | one, and the arrow scale factors | Design 9 |

They have different causes and different remedies: more substeps
for the first, a shorter flight or the central field (FD6) for the
second, and nothing for the third, which is deliberate and labeled
(P12). A run with `α = 1`, a five-second Earth drop, and `rk4` shows
a distortion column that is empty, an approximation column reading
`2 × 10⁻⁵`, and a numerical column that depends on the substeps,
which is how a student learns which knob does what.

**Rejected: one "error" number.** It would be the sum of things
with different units of meaning, and it would let a large labeled
exaggeration hide a small numerical failure, or the reverse.

**Rejected: judging the check against a finer check.** When an
exact motion exists it is the reference, full stop. For a future
field with no closed form, the reference becomes `dop853` at a tight
tolerance, and the numerical column then says "against a reference
integration", so the change of meaning is visible.

## 6.5 The first-order deflections

`analysis/closed_form_deflections.py` holds the textbook results,
for two uses: an overlay in the rotating view (the first-order
prediction drawn against the exact path, Design 9), and the oracles
of the tests. To first order in `Ω`, a particle launched with
rotating-frame velocity `ṽ₀` in uniform gravity `g̃` (either kind;
constant in rotating components) is displaced from its ghost path by

```
  Δ̃(t̃) = − Ω̃ × ( ṽ₀ t̃² + g̃ t̃³ / 3 ),                               (6.4)
```

obtained by integrating (6.1) with the Coriolis term evaluated on
the ghost velocity `ṽ₀ + g̃ t̃` and the centrifugal term's variation
neglected. Its special cases are the classroom formulas:

- **The drop** (`ṽ₀ = 0`): `Δ̃ = −(t̃³/3) Ω̃ × g̃`; on the Earth, with
  `g̃` along `−ê_U` and `Ω̃ = Ω̃ (sin λ ê_U + cos λ ê_N)`, this is
  `(1/3) g̃ Ω̃ t̃³ cos λ ê_E`, east, as in Design 1.8 and the spike.
- **A vertical launch upward** at `ṽ₀ = ṽ₀ ê_U`: the `ṽ₀ t̃²` term is
  west and the `g̃ t̃³/3` term east; a ball thrown straight up lands
  west of its launch point, by `(4/3) ṽ₀³ Ω̃ cos λ / g̃²` at the return
  time `2 ṽ₀ / g̃`, which is the classic result that surprises.
- **A horizontal launch** at speed `ṽ₀` toward azimuth `ψ` from
  north: the horizontal part of `−Ω̃ × ṽ₀ t̃²` is `Ω̃ ṽ₀ t̃² sin λ` to
  the right of the motion, and the vertical part is the Eötvös
  term, `Ω̃ ṽ₀ t̃² cos λ sin ψ` upward for an eastward launch.

**Their accuracy, for the tests.** (6.4) omits terms of relative
order `Ω̃ t̃` (the Coriolis term acting on the Coriolis velocity, and
the centrifugal term's change along the path) and, on the Earth,
the effective-gravity and plumb-line corrections of order
`Ω² R_E / g₀ = 3.45 × 10⁻³` (Design 4.6, where for the drop they
combine into exactly `1 − Ω² R_E / g₀`). A test compares the tool's
exact deflection with (6.4) at a relative tolerance of
`2 (Ω² R_E / g₀) + (Ω̃ t̃)²`, stated in the test with this derivation,
and the drop test uses the sharper factor of Design 4.6. On the
turntable, where `Ω̃ t̃` is of order one, (6.4) is not an oracle and
is not overlaid: the overlay is offered only where `Ω̃ t̃_end < 0.1`,
and the screen says so.

## 6.6 Verification

- The check with `rk4` on every packaged run agrees with the
  transform to `δ̃ < C Δt̃⁴` with `C` stated per run, and halving the
  substep divides `δ̃` by sixteen; with `euler`, by two.
- The check's initial state equals the transform's at `k = 0` to
  `10⁻¹⁵`, which tests the launch conversion in both directions.
- The ghost path: with the pseudo-force terms replaced by zero in
  (6.1), the check reproduces the ghost to the integrator's
  tolerance (tests that the ghost is what the words say it is).
- `E` along an exact no-force or space-fixed run, and `J` along an
  exact frame-fixed run, are constant to `10⁻¹³` relative to
  `Q_scale`; `J` along the check drifts by less than `C' Δt̃⁴`.
- A field declaring only `J` makes the monitor say why `E` is not
  reported, in the words of 6.3.
- (6.4) against the exact deflection: the drop at five latitudes
  within `1 − Ω² R_E / g₀` and `10⁻⁵` (the spike); the vertical
  launch and the horizontal launch within the tolerance of 6.5; and
  the sense of each deflection (east, west, right, up) as listed.
- The three columns of 6.4 are populated from their three sources
  and no code path sums them: a test walks the panel's data and
  asserts that no field combines two columns (the scattering tool's
  AST test, adapted).

## Sources

The Jacobi integral: Goldstein, Poole, and Safko, *Classical
Mechanics*, 3rd ed., §4.10 (the effective potential in a rotating
frame). The first-order deflections (6.4) and the vertical-launch
result: Taylor, *Classical Mechanics*, §9.9, and Marion and
Thornton, *Classical Dynamics*, §10.4. The error-budget discipline
follows the scattering tool's design section 9.
