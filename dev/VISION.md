# Vision

> **Document hierarchy:** **VISION** → ARCHITECTURE → DESIGN →
> PSEUDOCODE → Code. This is the top of the chain; it cites nothing
> above it, and every level below must be consistent with it.

> **Ratified 2026-09-22; Goal 4, Non-goal 5, and Future Directions
> 3 and 6 revised the same day** to state how the Earth's gravity is
> modeled (the uniform approximation of a central field, with the bare
> attraction as its magnitude), after the point was raised while
> writing ARCHITECTURE.

---

## 1. Purpose

This project is an interactive, real-time teaching tool that builds
physical intuition for **motion seen from a rotating frame** in a
graduate theoretical-mechanics course. A student chooses a rotating
frame (a turntable, a merry-go-round, the Earth at a latitude),
launches a particle, and watches the same motion in the inertial
frame and in the rotating frame side by side, with the centrifugal,
Coriolis, and Euler pseudo-forces drawn on the particle as labeled
vectors.

The subject has one central image, and the tool exists to deliver
it. A particle that moves in a straight line at constant speed in the
inertial frame traces a curve on the turntable, and an observer
riding the turntable must invent forces to explain the curve. The
tool shows both pictures at once, so that the pseudo-forces are seen
for what they are: the bookkeeping of a frame that is itself
accelerating, exactly as large as the frame's rotation demands and
not one bit more. Rendered as two views of one motion, the equation

    m a_rot = F − m Ω × (Ω × r) − 2 m Ω × v_rot − m (dΩ/dt) × r

stops being a formula to memorize and becomes something a student has
seen happen, term by term.

It is the companion of the rigid-body and scattering tools in this
group and shares their tooling, their environment, and their
conventions. Its closest kin is the rigid-body tool's body-frame
versus space-frame display: the same conceptual error, conflating two
frames, is at stake.

---

## 2. Goals

1. **Show one motion in two frames at once.** Render the inertial
   view and the rotating view side by side, or switchable, with each
   frame's axes drawn and labeled, so that a student can watch a
   straight line become a spiral and back.

2. **The inertial frame drives; the rotating frame is a transform.**
   The motion is computed in the inertial frame from the true forces
   and carried into the rotating frame by an exact rotation, so that
   the picture is as accurate as the inertial motion itself. The
   pseudo-forces are evaluated from that motion and drawn. Alongside,
   and optionally, the same motion is integrated a second time in the
   rotating frame from the true forces plus the pseudo-forces, and
   the difference between the two is displayed. Agreement to the
   integrator's tolerance is the tool's own proof that the
   pseudo-forces are complete and correctly signed, and the
   discrepancy is the disclosed numerical error of Principle 3. With
   the first version's forces the inertial motion is a closed form,
   so the comparison is against an exact answer.

3. **Draw every term.** The centrifugal, Coriolis, and (when the
   rotation rate varies) Euler contributions are drawn on the
   particle as separate labeled vectors, with their magnitudes read
   out, so that a student sees which term dominates and when.

4. **Ship the canonical demonstrations as run files.** All are freely
   launched projectiles: a particle sliding on a turntable; a ball
   thrown across a merry-go-round; a projectile launched at a given
   latitude and deflected by the Coriolis term; a vertical drop, which
   lands to the east; and a ring of independent particles launched
   toward a common point on the turntable, which all veer the same
   way, the cyclonic sense as a cartoon. The Earth runs model its
   gravity as the textbooks do: the central field is replaced by a
   uniform one at the launch point, whose magnitude is the bare
   attraction, so that the centrifugal term the tool draws is not
   counted twice and the tilted, slightly weaker effective gravity
   (the plumb line) emerges from the two together. The run says so on
   screen, with the condition under which it holds.

5. **Scrub time in both directions.** Play, pause, step, reverse,
   and jump anywhere in the run, because the run is precomputed and
   the display is a view.

6. **Reproduce any run from a file.** A run is specified completely
   by a TOML run file: the frame, the rotation rate, the particles
   and their launches, the force field, the fidelity, and the
   viewpoint.

7. **Validate against closed forms.** The free particle in a
   rotating frame is exact; the eastward deflection of a vertical
   drop and the deflection of a projectile at a latitude are known to
   the order their closed forms hold. They are the standard of
   correctness, to that order, and form the regression suite.

---

## 3. Non-Goals

1. **Fluid dynamics.** Cyclones, trade winds, and the bathtub are
   discussed with independent particles and a labeled cartoon (Goal
   4), never simulated as a fluid.

2. **Relativistic rotation.** The frame rotates slowly enough that
   Galilean kinematics is exact.

3. **General non-inertial frames, in the first version.** The frame
   rotates about a fixed axis through a fixed origin. Translation of
   the origin, and a moving axis, are anticipated (Future Direction
   1) and must not be foreclosed, but are not built first.

4. **Interacting particles.** A particle, or a ring of them, moves
   independently in the given force field. Interactions between
   particles belong elsewhere.

5. **Forces other than none and uniform gravity, in the first
   version.** Every first-version demonstration is a freely launched
   projectile, and the Earth's gravity is uniform by approximation
   (Goal 4). Central gravity, a spring, and the constraint a pendulum
   needs are anticipated (Future Directions 5 and 6) and the force
   interface must admit them, but they are not built first.

6. **A batch tier.** The older tools have one because they need large
   ensembles for statistics. Nothing here does. Headless use is the
   offscreen capture every tool in the suite provides, and no more.

---

## 4. Design Principles

1. **Physical fidelity.** The motion is produced by solving the true
   equations of motion, never by scripted or faked animation. Where
   a closed-form motion exists it may be used directly, but it must
   be the exact solution.

2. **The inertial frame is the ground truth.** It drives the display;
   the rotating frame is a coordinate transform of it; a rotating-
   frame integration is a check (Goal 2), never the source of the
   picture. Wherever the two disagree beyond the disclosed numerical
   error, the rotating-frame code is wrong.

3. **Numerical error is disclosed, never disguised.** Energy in the
   inertial frame, the Jacobi integral in the rotating frame, and the
   difference between the exact motion and the rotating-frame
   integration are monitored and shown.

4. **Real-time interactivity.** Changing the rotation rate or the
   launch recomputes the run quickly enough to feel like manipulation.

5. **Pedagogical transparency.** Every vector, trace, and frame is
   labeled with the quantity it represents.

6. **Configurable visual encoding.** Light, dark, and color-blind-safe
   palettes at minimum; no distinction that carries meaning rests on
   color alone.

7. **Student-readable source.** The code is a teaching artifact
   (`CLAUDE.md`).

8. **Start simple, stay extensible.** First the turntable and the
   free particle; the Earth at a latitude follows in the same
   version; a varying rotation rate, other forces, and the pendulum
   follow without a rewrite.

9. **Physics decoupled from presentation.** The motion, the
   transform, and the pseudo-force terms are independent of the
   renderer.

10. **The computation method never dictates the simulation.** A
    motion may come from a closed form or from an integrator; every
    consumer sees only the trajectory.

11. **A dimensionless core, with real units at the boundary.** The
    core works in units of the frame's rotation: times in units of
    `1/Ω`, lengths in units of a chosen scale, so that a turntable and
    the Earth are the same computation and a run is characterized by
    the launch speed compared with the frame's speed at that radius.
    Real units enter only through named presets at the input boundary
    (a turntable, Earth at a latitude), which carry SI dimensions and
    are reported in them, with the scale factor stated. A student sees
    physical scale where it means something and is not asked to carry
    exponents where it does not.

12. **Deliberate distortions are labeled.** The Earth's rotation is
    too slow to see over a thrown ball's flight; exaggerating `Ω` to
    make the deflection visible is legitimate, and the factor is
    stated on screen.

13. **One word for the forces.** They are *pseudo-forces* everywhere:
    on screen, in the run file, in the source, and in these documents.

---

## 5. Audience and Use

Graduate students in a theoretical-mechanics course at the level of
Goldstein (chapter 4) and Taylor (chapter 9). The tool runs wherever
a student is given to run it: a laptop through `pip`, or a shared
teaching computer through the `physdemo` suite; it needs no GPU and
keeps working in a directory it cannot write.

---

## 6. Future Directions

1. **A translating and tilting frame.** The general non-inertial
   frame adds the origin's acceleration and a moving axis; the
   pseudo-force interface should take a frame object, not an axis
   and a rate.

2. **A varying rotation rate.** The Euler term is drawn from the
   start (Goal 3) but the first run files hold `Ω` fixed; a spun-up
   turntable is the natural next scenario.

3. **The Earth's shape.** The first version already shows the plumb
   line: the bare attraction plus the centrifugal term at a latitude
   is the local vertical, tilted against the radial direction (Goal
   4). What it does not show is that the Earth's surface has settled
   perpendicular to that plumb line, which is its oblateness; a
   later version can draw the ellipsoid and the level surface.

4. **The Lagrangian view.** The same pseudo-forces from the
   rotating-frame Lagrangian, for a course that reaches it.

5. **The Foucault pendulum.** The most famous demonstration, and not
   a free particle: either a bob constrained to a sphere, or the
   small-angle approximation, in which it is a two-dimensional
   oscillator with a Coriolis coupling whose plane precesses at
   `Ω sin(latitude)` in closed form. The small-angle version is the
   cheap one and the natural first step.

6. **Further force fields.** Central gravity, the field the Earth
   actually has, shows where the uniform approximation of Goal 4
   fails and turns a long projectile flight into an arc of a Kepler
   ellipse; a central attraction on the turntable turns the cyclone
   cartoon into an inflow that spirals in; a spring gives the
   oscillator of Direction 5. All are new force objects behind the
   interface of Non-goal 5 and change nothing downstream.
