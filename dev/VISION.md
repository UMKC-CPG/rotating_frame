# Vision

> **Document hierarchy:** **VISION** → ARCHITECTURE → DESIGN →
> PSEUDOCODE → Code. This is the top of the chain; it cites nothing
> above it, and every level below must be consistent with it.

> **Status: DRAFT, 2026-09-22, not yet ratified.** Written as a
> starting point when the tool was generated from the `physdemo`
> skeleton; every paragraph is open. Ratify or rewrite it before
> ARCHITECTURE is begun, and remove this notice then.

---

## 1. Purpose

This project is an interactive, real-time teaching tool that builds
physical intuition for **motion seen from a rotating frame** in a
graduate theoretical-mechanics course. A student chooses a rotating
frame (a turntable, a merry-go-round, the Earth at a latitude), sets a
particle moving, and watches the same motion in the inertial frame
and in the rotating frame side by side, with the centrifugal,
Coriolis, and Euler terms drawn on the particle as labeled vectors.

The subject has one central image, and the tool exists to deliver
it. A particle that moves in a straight line at constant speed in the
inertial frame traces a curve on the turntable, and an observer
riding the turntable must invent forces to explain the curve. The
tool shows both pictures at once, so that the "pseudo-forces" are
seen for what they are: the bookkeeping of a frame that is itself
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

2. **Integrate in both frames and show they agree.** Compute the
   motion in the inertial frame from the true forces, and again in
   the rotating frame from the true forces plus the pseudo-forces;
   display the difference. Agreement to the integrator's tolerance is
   the tool's own proof that the pseudo-forces are complete and
   correctly signed.

3. **Draw every term.** The centrifugal, Coriolis, and (when the
   rotation rate varies) Euler contributions are drawn on the
   particle as separate labeled vectors, with their magnitudes read
   out, so that a student sees which term dominates and when.

4. **Ship the canonical demonstrations as run files.** A free
   particle on a turntable; a ball thrown across a merry-go-round; a
   projectile launched at a given latitude, deflected by the
   Coriolis term; the Foucault pendulum, whose plane precesses at
   `Ω sin(latitude)`; and a labeled cartoon of why cyclones turn the
   way they do.

5. **Scrub time in both directions.** Play, pause, step, reverse,
   and jump anywhere in the run, because the run is precomputed and
   the display is a view.

6. **Reproduce any run from a file.** A run is specified completely
   by a TOML run file: the frame, the rotation rate, the particle,
   the true forces, the fidelity, and the viewpoint.

7. **Validate against closed forms.** The free particle in a
   rotating frame, the Foucault precession rate, and the Coriolis
   deflection of a vertical drop have exact expressions; they are the
   standard of correctness and form the regression suite.

---

## 3. Non-Goals

1. **Fluid dynamics.** Cyclones, trade winds, and the bathtub are
   discussed with a point particle and a labeled cartoon, never
   simulated as a fluid.

2. **Relativistic rotation.** The frame rotates slowly enough that
   Galilean kinematics is exact.

3. **General non-inertial frames, in the first version.** The frame
   rotates about a fixed axis through a fixed origin. Translation of
   the origin, and a moving axis, are anticipated (Future Direction
   1) and must not be foreclosed, but are not built first.

4. **Many-body dynamics.** One particle, or a few independent ones,
   in given forces. Interactions between particles belong elsewhere.

---

## 4. Design Principles

1. **Physical fidelity.** The motion is produced by solving the true
   equations of motion, never by scripted or faked animation.

2. **The inertial frame is the ground truth.** The rotating-frame
   integration exists to be compared with it (G2); wherever the two
   disagree beyond the disclosed numerical error, the rotating-frame
   code is wrong.

3. **Numerical error is disclosed, never disguised.** Energy in the
   inertial frame, the Jacobi integral in the rotating frame, and the
   difference between the two integrations are monitored and shown.

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
   free particle; the Earth, the pendulum, and a varying rotation
   rate follow without a rewrite.

9. **Physics decoupled from presentation.** The two integrations and
   the pseudo-force terms are independent of the renderer.

10. **The computation method never dictates the simulation.** Where a
    closed form exists it may be drawn beside the integrated motion,
    and every consumer sees only the trajectory.

11. **Explicit physical units at the boundary.** A run file says
    `omega = "7.292e-5 rad/s"` or `latitude = "39 deg"`; the core may
    work in scaled units, and the display reports real ones.

12. **Deliberate distortions are labeled.** The Earth's rotation is
    too slow to see over a thrown ball's flight; exaggerating Ω to
    make the deflection visible is legitimate, and the factor is
    stated on screen.

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
   start (G3) but the first run files hold Ω fixed; a spun-up
   turntable is the natural next scenario.

3. **The plumb line and effective gravity.** Gravity plus the
   centrifugal term at a latitude defines the local vertical; showing
   the plumb line's tilt against the true radial direction connects
   to the Earth's oblateness.

4. **The Lagrangian view.** The same pseudo-forces from the
   rotating-frame Lagrangian, for a course that reaches it.
