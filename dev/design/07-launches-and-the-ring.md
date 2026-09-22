# Design 7: Launches and the Ring

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.3 (`launch/`); serves
> G4 (the demonstrations, including the ring), G6 (a run from a
> file), and NG4 (independent particles). Uses Designs 1 to 4.
> *Status: reviewed; ratified 2026-09-22.*

A launch is where a particle starts and how it is thrown, in the
words a student would use: an offset from the launch point in local
east, north, and up, and a velocity as either components or a speed
with a direction, in either frame. This section fixes the local
axes each preset supplies, the conversion to the inertial state the
motion provider takes, the ring, and what is refused.

---

## 7.1 The launch point and its local axes

Every preset (Design 2.4) supplies a launch point `P` and a
right-handed local triad `(ê_E, ê_N, ê_U)` at it, in rotating
components, so that a launch reads the same way on every stage:

| Preset | `P` | `ê_U` | `ê_E`, `ê_N` |
| --- | --- | --- | --- |
| turntable | the disc's center, | `n̂ = ẑ` | `x̂`, `ŷ` of the frame |
| | `r̃_P = 0` | | |
| merry-go-round | on the axis at the | `n̂ = ẑ` | `x̂`, `ŷ` of the frame |
| | platform's height | | |
| Earth | on the surface at | the plumb line, | `ê_E` along `n̂ × r_P`, |
| | latitude `λ` | Design 3.4.1 | `ê_N = ê_U × ê_E` |

On the two platforms the "local" axes are the frame's own, the disc
is the plane `ê_U · ρ̃ = 0`, and a position is an offset from the
axis. On the Earth the local axes are the ones Designs 3 and 6 use,
`P` is `R_E r̂_P` from `O`, and offsets are small numbers against a
large `r̃_P` that the store carries without difficulty (A4.2). A
run file may move `P` on the two platforms (a puck starting at the
rim) by giving the launch's position; on the Earth `P` is fixed by
the latitude and the launch's position is an offset from it, so
that the ground is always the plane through `P`.

## 7.2 One launch

```
  position   ρ̃ in local components (E, N, U), default (0, 0, 0)
  velocity   either components (E, N, U), or
             speed, azimuth (from north, clockwise seen from above),
             elevation (from the horizontal); default at rest
  frame      "rotating" (default) or "inertial"                    (7.1)
```

The conversion to the motion provider's inertial state at `t̃ = 0`:

```
  r̃_rot(0) = r̃_P + ρ̃_E ê_E + ρ̃_N ê_N + ρ̃_U ê_U
  ṽ_local  = ṽ_E ê_E + ṽ_N ê_N + ṽ_U ê_U,   or from (speed, ψ, χ):
             ṽ_local = speed (cos χ sin ψ ê_E + cos χ cos ψ ê_N
                              + sin χ ê_U)
  frame == "rotating":  r̃_in(0) = r̃_rot(0)
                        ṽ_in(0)  = ṽ_local + Ω̃ × r̃_rot(0)     (Design 1.5)
  frame == "inertial":  r̃_in(0) = r̃_rot(0),  ṽ_in(0) = ṽ_local
```

Since `R(0) = I`, the local triad is the same set of numbers in both
frames at the instant of launch, and the only difference between the
two kinds of launch is the rim velocity `Ω̃ × r̃`. "I pushed the puck
toward the center" is a rotating launch; "I rolled the ball onto the
turntable from the floor" is an inertial one, and the puck then
arrives already moving sideways in the platform's view.

**The launch is converted once, here, before the motion provider
runs**, and both the local description and the resolved inertial
state are kept in the run spec (Design 8), so that the run file
reads back in the student's words and the store starts from
exactly the numbers the physics used.

## 7.3 The ring

A ring is a shorthand for `N_p` launches at once (G4):

```
  ring.count      N_p ≥ 1
  ring.radius     ρ̃_ring > 0, from the target point
  ring.target     the common point, local components; default P
  ring.speed      ṽ₀ ≥ 0
  ring.sense      "inward" (default) or "outward"
  ring.phase      the azimuth of member 0, default 0
  ring.height     ρ̃_U of the members, default 0                    (7.2)
```

Member `i` sits at azimuth `ψ_i = phase + 2π i / N_p` on the circle
of radius `ρ̃_ring` about the target in the horizontal plane at
`ρ̃_U = height`, and is launched at speed `ṽ₀` toward the target
(inward) or away from it (outward), in the rotating frame. The ring
expands into `N_p` launch specs of 7.2 and is otherwise forgotten:
the motion provider, the store, and the display see particles, and
nothing downstream knows they came from a ring (NG4). The cyclone
cartoon of G4 is an inward ring on the turntable with the target at
the center; a student watching it sees every member veer the same
way and none reach the center.

**Rejected: a ring with random azimuths or speeds.** Nothing in the
first version is stochastic (A7); a symmetric ring is what shows the
symmetry of the deflection, and the picture's invariance under
rotation by `2π/N_p` is an oracle (A8.2).

## 7.4 What is refused

The schema (Design 8) validates types; this section fixes the
physical refusals, each with a message naming the key:

- A launch below the ground, `ρ̃_U < 0`, where a "lands" rule is in
  force; a launch on the ground, `ρ̃_U = 0`, only with `ṽ_U > 0`,
  and the landing event is then sought after the first sample
  (Design 4.5).
- A launch outside the disc, `|ρ̃_h| ≥ 1`, where a "leaves" rule is
  in force, and a ring whose members would be.
- An elevation outside `[−90°, 90°]`, a negative speed, a negative
  ring radius, a count below one.
- A frame other than `"rotating"` or `"inertial"`.

**Rejected: launches given as inertial-frame Cartesian components
from `O`.** They are what the physics uses, and a student never
means them: on the Earth they are seven-figure numbers whose small
differences are the whole experiment. The local axes are what a
student means, and the conversion is the tool's job.

## 7.5 Verification

- Each preset's local triad is orthonormal and right-handed to
  `10⁻¹⁴`, and on the Earth `ê_U` is the plumb line of Design 3.4.1
  and `ê_E` is eastward (`ê_E · (n̂ × r̂_P) > 0`).
- A rotating launch at rest has `ṽ_in(0) = Ω̃ × r̃_rot(0)`, and an
  inertial launch at rest has `ṽ_in(0) = 0`; the (speed, azimuth,
  elevation) form and the component form of the same velocity agree
  to `10⁻¹⁴`; azimuth `0` is north, `90°` is east.
- The run spec keeps both the local description and the resolved
  state, and the resolved state is what the store's sample `0`
  holds.
- A ring of `N_p` members has them equally spaced in azimuth, each
  at `ρ̃_ring` from the target, each with velocity of magnitude `ṽ₀`
  along `∓` the direction to the target; expanding a ring and
  launching its members one by one give identical stores.
- **The ring's symmetry** (A8.2): on the turntable with the target at
  the center, the rotating-frame samples of member `i` are those of
  member `0` rotated by `2π i / N_p` about `n̂`, to `10⁻¹²`, at every
  sample.
- Each refusal of 7.4 is a message naming the key and status 2 from
  the command, never a traceback.

## Sources

The azimuth convention (from north, clockwise seen from above) is
the navigational one, used by Taylor, *Classical Mechanics*, §9.9,
for the projectile examples.
