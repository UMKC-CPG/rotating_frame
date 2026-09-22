# Design — Index

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. For goals and principles see `VISION.md`; for
> the structural ideas, the module map, and the boundaries see
> `ARCHITECTURE.md`. Principles are cited as `P<n>`, goals as `G<n>`,
> architecture sections as `A<n>`.

---

**This file is an index, not the design.** Each numbered section
lives in its own file under `dev/design/`. Read this table to find
the section you need, then read only that file.

## Sections

Each entry: number, file, topic, status. The order is the order the
sections cite one another: every later section uses the conventions
of Section 1.

1. [`design/01-frame-and-transform.md`](design/01-frame-and-transform.md)
   — the `Frame` object, `R(t)`, the transforms of position and
   velocity, the sign conventions (A2.3, A6.6). *reviewed*
2. [`design/02-natural-units-and-presets.md`](
   design/02-natural-units-and-presets.md) — the scaling by `Ω` and
   `L`, mass per unit, the named presets (turntable, merry-go-round,
   Earth at a latitude), the exaggeration factor (P11, P12). *reviewed*
3. [`design/03-force-fields.md`](design/03-force-fields.md) — the
   interface, no force, and the two kinds of uniform gravity; the
   bare attraction and the plumb line; where the uniform
   approximation holds and its error (A3.2, A4.2). *reviewed*
4. [`design/04-motion-and-stopping.md`](design/04-motion-and-stopping.md)
   — the closed forms (line, parabola, rotating parabola) and their
   small-angle evaluation, the sampling, the integrators for the
   check and for future fields, the stopping rules and the exact
   event, the drop oracle with its derived tolerance (A3.4, A6.2).
   *reviewed*
5. [`design/05-pseudo-forces.md`](design/05-pseudo-forces.md) — the
   three terms from the rotating-frame state, evaluated once for the
   check and the store; what each view draws; the sign checks and
   the closure test (A3.5). *reviewed*
6. [`design/06-check-and-error-budget.md`](
   design/06-check-and-error-budget.md) — the rotating-frame
   integration, the comparison against the transform and the ghost
   path that scales it, energy and the Jacobi integral, the three
   columns never combined, the first-order deflections (P3, A3.6).
   *reviewed*
7. [`design/07-launches-and-the-ring.md`](
   design/07-launches-and-the-ring.md) — the launch point and local
   axes each preset supplies, a launch in either frame as offsets
   and a velocity, the ring, what is refused (A3.3). *reviewed*
8. [`design/08-run-file.md`](design/08-run-file.md) — the TOML
   tables and keys, the schema and its refusals, precedence, the
   resolution to natural units and the write-back, the results store
   and its interface, the driver (A3.7, A6.4, A7). *reviewed*
9. [`design/09-scene-and-geometry.md`](design/09-scene-and-geometry.md)
   — the two views and their cameras, the scene description, the
   triads, the stage, the trails, the arrows and their two stated
   scales, palettes and the redundancy rule, the panels, the
   readouts (A3.8, A3.9). *reviewed*
10. [`design/10-scrubber-and-session.md`](
    design/10-scrubber-and-session.md) — viewing versus run controls
    and the one rule, the session state, the loop, the time slider,
    every key chord, scripted controls, the invariants (A3.9). *reviewed*

Status is one of: planned, draft, reviewed, implemented, superseded.
All ten sections were reviewed together and ratified on 2026-09-22
(`v0.3-design`); a section becomes *implemented* when its code and
tests exist.
A superseded section keeps its number and file; its header names the
replacement. Numbers are never reused.

## Conventions

**Numbering is stable.** Sections are cited by number from
PSEUDOCODE, from TODO, and from source comments. Append rather than
renumber.

**One topic per file.** A section file passing roughly 1,500 lines is
describing more than one thing; split it and add the row.

**Cite upward.** A design choice forced by a VISION principle names
it; one forced by an architectural boundary names the section.

**Record what was rejected.** The alternative that was considered and
dropped, with the reason, is what stops it being proposed again.

## Notation

Fixed here and used in every section and in PSEUDOCODE.

**Frames and the transform.** The inertial frame and the rotating
frame share the origin `O`, a point on the axis (A2.3, A4.2). A
vector's inertial components carry the subscript `in` and its
rotating components the subscript `rot`; a bare symbol is the
geometric vector. The rotating frame has turned by `R(t)` since
`t = 0`, so that

    r_in = R(t) r_rot,        v_rot = R(t)ᵀ (v_in − Ω × r_in),

with the second line the velocity a rotating observer measures. `R`
is a right-handed rotation about `n̂` by the angle `θ(t)`; in the
first version `θ = Ω t` (NG3).

| Symbol | Meaning |
| --- | --- |
| `O` | The common origin, on the axis |
| `n̂` | Unit vector along the rotation axis |
| `Ω` | Angular velocity of the frame, `Ω = Ω n̂`; `Ω = |Ω|` |
| `dΩ/dt` | Its rate of change; zero in the first version (FD2) |
| `θ(t)` | The frame's angle since `t = 0`; `θ = Ω t` now |
| `R(t)` | The rotation by `θ(t)` about `n̂`, inertial ← rotating |
| `t` | Time, common to both frames |
| `r, v, a` | Position, velocity, acceleration of a particle, |
| | from `O`; subscripts `in` and `rot` for components |
| `m` | Particle mass |
| `F` | The true force on the particle, in inertial components |
| `F_cf` | Centrifugal term, `−m Ω × (Ω × r_rot)` |
| `F_co` | Coriolis term, `−2m Ω × v_rot` |
| `F_eu` | Euler term, `−m (dΩ/dt) × r_rot` |
| `g₀` | The bare gravitational attraction, a vector; `g₀ = |g₀|` |
| | is about `9.82 m/s²` at the Earth's surface (A4.2) |
| `g_eff` | Effective gravity at the launch point, `g₀ + F_cf/m` |
| | evaluated there; what a plumb line measures |
| `ẑ_up` | The local vertical: the plumb line's direction, `−ĝ_eff` |
| `P`, `r_P` | The launch point and its position from `O`, fixed in |
| | the rotating frame |
| `ρ` | Displacement from the launch point, `r_rot − r_P` |
| `ê_E, ê_N, ê_U` | The local east, north, and up axes at `P` (Section |
| | 7); `ê_U = ẑ_up`, `ê_E` along `n̂ × r_P`, `ê_N = ê_U × ê_E` |
| `λ` | Latitude of `P`, the angle between `r_P` and the |
| | equatorial plane |
| `R_E` | The Earth's radius, for the Earth presets |
| `L` | The length scale of a run (Section 2) |
| `T` | The time scale, `1/Ω` |
| `x̃` | Any quantity `x` in natural units: `t̃ = t/T`, `r̃ = r/L`, |
| | `ṽ = v/(Ω L)`, `ã = a/(Ω² L)`, `g̃ = g/(Ω² L)` |
| `ε` | The speed ratio of a launch, `v₀/(Ω L)`: how fast the |
| | particle is compared with the frame at the scale `L` |
| `α` | The exaggeration factor on `Ω` (P12); the run uses |
| | `α Ω` and the screen states `α` |
| `v₀` | Launch speed; `v₀_in`, `v₀_rot` its components |
| `t_end` | The run's duration; a stopping rule may end it sooner |
| `N`, `k`, `Δt` | Number of samples, sample index `0 … N−1`, and |
| | sample spacing; `t_k = k Δt` |
| `i`, `N_p` | Particle index and count; a ring has `N_p` members |
| `E` | Mechanical energy in the inertial frame |
| `J` | The Jacobi integral in the rotating frame, |
| | `½ m v_rot² + U − ½ m |Ω × r|²`, for a frame-fixed `U` |
| `δ` | The comparison error, `|r_rot^check − r_rot|` at a |
| | sample (Section 6) |
| `Δ` | The pseudo-force effect, `ρ_rot − ρ_ghost` (Section 6); to |
| | first order, `−Ω × (v₀ t² + g t³/3)` |
| `η` | The comparison error as a fraction of the effect, `δ/|Δ|` |
| `h` | Height above the ground, `ρ · ê_U` |
| `ψ, χ` | A launch's azimuth (from north, clockwise seen from |
| | above) and elevation (from the horizontal) |
| `t_E` | `sqrt(R_E / g₀) ≈ 805 s`, the timescale of the uniform |
| | approximation's error (Section 3) |

**Signs and handedness.** `n̂` is the rotating frame's `ẑ` for the
turntable and the merry-go-round, and the polar axis for the Earth,
pointing north; `Ω > 0` is counterclockwise seen from `+n̂`, which is
the Earth's sense seen from above the north pole. The Coriolis term
then deflects a horizontally moving particle to the right in the
northern hemisphere, which is the check on every sign in the tool.

**Two kinds of uniform gravity** (A4.2) are written `g₀` with a kind:
*space-fixed*, constant in inertial components, and *frame-fixed*,
constant in rotating components. The word on screen for `F_cf`,
`F_co`, and `F_eu` together is *pseudo-forces* (P13).

**The local axes** `ê_E, ê_N, ê_U` are what the Earth runs are
displayed and launched in; they are defined from the plumb line, not
from the radial direction, so that "vertical" on screen is what a
student would measure. For the turntable and the merry-go-round, `P`
is on the axis or on the disc and the local axes are the frame's own.
