# Design 2: Natural Units and the Presets

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.1 (`natural_units.py`,
> `units.py`, `presets.py`) and 6.6 (the units boundary); serves P11
> (a dimensionless core, real units at the boundary) and P12 (labeled
> distortions). Uses Design 1. *Status: reviewed; ratified 2026-09-22.*

The core works in units of the frame's rotation. This section fixes
the scaling, says what a run is characterized by, states where real
units enter and leave, defines the three presets with their numbers,
and says exactly what the exaggeration factor does.

---

## 2.1 The scaling

A run has one rate `Ω` and one length `L`. Every quantity in the core
is measured in units built from them and from a unit mass:

```
  T = 1/Ω            time         t̃ = t / T   = Ω t
  L                  length       r̃ = r / L
  Ω L                speed        ṽ = v / (Ω L)
  Ω² L               acceleration ã = a / (Ω² L)        g̃ = g / (Ω² L)
  m                  mass         the core works per unit mass (2.2)
```

In these units `Ω̃ = 1`, so the frame's angle is the elapsed time,
`θ = t̃` (Design 1.6), and the rotating-frame equation (1.4) per unit
mass reads

```
  ã_rot = f̃_rot  −  n̂ × (n̂ × r̃_rot)  −  2 n̂ × ṽ_rot,           (2.1)
```

with `f̃` the true force per unit mass in the same units and the
Euler term absent at constant rate. Every coefficient is one. That
is the point: a turntable and the Earth are the same computation,
and what distinguishes one run from another is a handful of
dimensionless numbers (2.3).

**Why `1/Ω` and not the flight time.** Scaling time by the run's
duration would make every run last one unit and hide the thing the
tool is about, how much the frame turns during the motion. With
`T = 1/Ω`, a dimensionless time of `0.1` means the frame turned a
tenth of a radian while the particle moved, and the Coriolis
deflection is of that order relative to the motion, which a student
can read straight off the clock on screen.

**Why `L` is the run's and not derived.** A rate fixes a time but no
length; the length that makes a run's picture order one is the
demonstration's own size, the disc's radius, the throw's range, the
drop's height. Each preset supplies a default `L` of that kind (2.4)
and the run file may override it (Section 8). Two runs with the
same `L` and the same dimensionless numbers are the same run, and
the tool can say so.

## 2.2 Mass

The first version's forces are per unit mass (none, and gravity),
and the pseudo-forces are proportional to `m`, so the motion does not
depend on the mass at all. The core therefore works per unit mass:
what Section 5 evaluates and the store holds are the three
pseudo-accelerations `F_cf/m`, `F_co/m`, `F_eu/m`. A run file may
give a mass; if it does, the boundary multiplies through for the
readouts (2.6) so that a force is shown in newtons, and if it does
not, the readouts say "per unit mass". Nothing in the core reads
`m`. When a future field depends on mass (it would be a strange
one), it enters through the force interface and not here.

## 2.3 What characterizes a run

After scaling, a first-version run is fixed by:

```
  ε      = v₀ / (Ω L)         the speed ratio of each launch
  g̃      = g₀ / (Ω² L)        the gravity, if any (0 for the turntable)
  r̃_P    = r_P / L            the launch point from the axis
  λ, R̃_E                      for the Earth: latitude and R_E / L
  t̃_end  = Ω t_end            the duration, and the stopping rule
  the launch direction, and the kind of gravity (Design 3)
```

`ε` is the number a student should learn to read: for `ε ≫ 1` the
particle crosses the scene before the frame has turned and the
deflection is a small correction; for `ε ~ 1` the spiral is the
whole picture. On a turntable at `33⅓ rpm` with `L = 0.3 m`, a puck
pushed at `0.5 m/s` has `ε ≈ 0.48`; on the Earth with `L = 100 m`, a
`10 m/s` throw has `ε ≈ 1.4 × 10³`, which is why the Earth's
deflections are small and why P12 exists.

## 2.4 The presets

A preset is a named set of real-unit values that a run file may
select and partly override. The boundary (2.5) turns the result into
the dimensionless numbers of 2.3. The three first-version presets:

**`turntable`.** A frictionless puck on a spinning disc: `n̂ = ẑ`;
`Ω = 33⅓ rpm = 3.4907 rad/s`; `L = 0.30 m`, the disc's radius; no
force (the disc's normal force cancels gravity and the puck stays in
the plane `z = 0`); the launch point `P` at the disc's center, a
launch's position being an offset from it (Design 7.1), the shipped
example starting at the rim; the stopping rule "leaves the disc" at
`|ρ| > L`, or the duration. The stage is the disc.

**`merry_go_round`.** A ball thrown across a playground roundabout:
`n̂ = ẑ`; `Ω = 0.50 rad/s` (about `4.8 rpm`); `L = 2.0 m`, the
platform's radius; space-fixed gravity `g = 9.81 m/s²` along `−ẑ`;
the launch point `P` on the axis at the platform's height, the
shipped example launching from the rim at `1.0 m` above it (an offset,
Design 7.1); the stopping rule "lands" when the height above the
platform reaches zero, or the duration. The platform is flush with
the floor, as a playground roundabout is, so landing is height zero
everywhere, on the platform or off it. The stage is the platform and
the floor.

**`earth`.** A projectile at a latitude: `n̂ = ẑ`, the polar axis
pointing north; `Ω = 7.2921150 × 10⁻⁵ rad/s`, the sidereal rate;
`R_E = 6.371 × 10⁶ m`; frame-fixed gravity with `g₀ = GM/R_E² =
9.820 m/s²` (`GM = 3.986004 × 10¹⁴ m³/s²`) directed from `P` toward
`O` (Design 3); `λ` required, no default; the launch point `r_P =
R_E (cos λ, 0, sin λ)` in rotating components, the run file adding
a height above the ground; `L = 100 m` by default, the size of a
throw; the stopping rule "lands" when the height above the ground
patch reaches zero, or the duration. The stage is a patch of ground
through `P` perpendicular to the plumb line (Design 3, Design 9).

Two numbers the Earth preset implies, stated here because Section 3
and the tests use them: the centrifugal acceleration at the surface
is `Ω² R_E cos λ`, `0.0339 m/s²` at the equator; and the plumb line's
tilt from the radial direction is `Ω² R_E sin λ cos λ / g₀` to first
order, a maximum of `0.0017 rad = 0.099°` at `λ = 45°`.

**Rejected: a preset for a rotating space station or a centrifuge.**
Both are the turntable with a different `Ω` and `L`, which the run
file can already say; a preset earns its place only when it brings a
different force, a different stage, or a different stopping rule.

## 2.5 The boundary

`core/units.py` is the only module that imports pint (A6.6). It does
three things and nothing else:

1. **Parses dimensioned strings** from the run file, `"33.3 rpm"`,
   `"39 deg"`, `"10 m/s"`, `"1.2 m"`, `"0.5 kg"`, into SI, with the
   error message pint gives when a string is not a quantity of the
   expected dimension (a speed where a length was wanted). A bare
   number in the run file is taken as already dimensionless in the
   natural units of the run, and the schema (Section 8) says, key by
   key, which keys may be bare.
2. **Resolves a run to natural units.** Given the preset's values and
   the run file's overrides, it fixes `Ω` (after the exaggeration
   factor, 2.6), `L`, and `T = 1/Ω`, divides every dimensioned
   quantity by the right combination, and hands the core the
   dimensionless numbers of 2.3 plus the scale factors `(Ω, L, T, m)`
   for the way back.
3. **Formats a natural-unit value back into real units** for the
   readouts, `r̃ L`, `ṽ Ω L`, `ã Ω² L`, and `t̃ T`, in the preset's
   units, with the scale factors stated on screen (2.6).

Below `run/`, no module imports pint, accepts a pint object, or
returns one; the test of A8.6(3) enforces it. The reason is the one
the scattering tool gives: pint's cost and its verbosity stay at the
edge, and a student reading `motion/` sees numbers.

**Rejected: SI throughout, as the rigid-body tool does.** It suits a
tool whose scales are all of one kind. Here the Earth and the
turntable differ by five orders of magnitude in `Ω` and seven in
`L`, and the thing the tool teaches is that they are nonetheless the
same problem, which only the dimensionless form makes visible (P11).

## 2.6 The exaggeration factor

The Earth's rotation is too slow to see over a thrown ball's flight:
`ε ~ 10³`. A run file may set `α`, and the run then uses `α Ω` in
place of the preset's `Ω`, everywhere. That is the whole definition,
and it has consequences the screen must state (P12):

- The natural units are built from the run's `Ω`, so `T = 1/(α Ω)`.
  A dimensionless time of one is still one turn's worth, of the
  faster frame.
- Every pseudo-force term follows the run's `Ω`: the Coriolis term
  grows as `α`, the centrifugal term as `α²`. On the Earth, a large
  `α` therefore tilts the plumb line visibly and shortens `g_eff`,
  which is what a faster-spinning Earth would do. The tool shows it
  and says why; it does not hide it.
- The readouts convert with the run's scale factors and add, beside
  the scale note, the line `Ω exaggerated × α` whenever `α ≠ 1`.

**Rejected: exaggerating the Coriolis term alone.** It would make a
deflection visible without the rest of the physics that goes with a
faster frame, and the three terms would no longer come from one `Ω`,
which breaks the check of Section 6 and the lesson of G2. A distortion
is legitimate when it is a change of the parameters and labeled; a
distortion of one term is a different equation.

## 2.7 Verification

- The scaling round-trips: a run written in SI and the same run
  written in natural units resolve to identical dimensionless
  arrays, and formatting back reproduces the SI values to `1e-12`
  relative (the rounding of a few multiplications).
- Each preset resolves to the numbers stated in 2.4, and the derived
  numbers, `0.0339 m/s²` at the equator and `0.099°` at `45°`, come
  out to the four figures given.
- `ε` for the two worked cases of 2.3 comes out `0.48` and
  `1.4 × 10³`.
- With `α = 2` the resolved run's `Ω` is doubled, `T` is halved, the
  readout states `× 2`, and the dimensionless arrays of a run whose
  physical `Ω` is `2 Ω` with `α = 1` are identical to them.
- A dimensioned string of the wrong dimension is refused with a
  message naming the key; a bare number where the schema forbids one
  is refused likewise.
- No module outside `core/units.py` imports pint (A8.6(3)).

## Sources

The sidereal rotation rate `7.2921150 × 10⁻⁵ rad/s` is the IERS
value; `GM = 3.986004 × 10¹⁴ m³/s²` and `R_E = 6.371 × 10⁶ m` (the
mean radius) are the IAU 2015 nominal values, so that `g₀` here is
the attraction of a spherical Earth and not the measured `9.81`,
which already includes the centrifugal term (ARCHITECTURE 4.2). The
plumb-line tilt is Taylor, *Classical Mechanics*, §9.8; the
dimensionless treatment follows the scattering tool's design
section 1.
