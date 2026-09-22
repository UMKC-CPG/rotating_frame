# Architecture

> **Document hierarchy:** VISION → **ARCHITECTURE** → DESIGN →
> PSEUDOCODE → Code. For goals and principles, see `VISION.md`.
> Principles are cited as `P<n>`, goals as `G<n>`, non-goals as
> `NG<n>`, future directions as `FD<n>`.

> **Ratified 2026-09-22.** Sections 1, 7, 8, and 9 were filled by the
> physdemo skeleton and are revised here where the tool's physics
> changes them.

---

## 1. Repository Layout

```
rotating_frame/
  dev/
    README.md         What lives in dev/, and what is not the chain
    VISION.md         Goals and principles
    ARCHITECTURE.md   This document
    DESIGN.md         Index of design sections
    design/           One file per design section
    PSEUDOCODE.md     Index of pseudocode sections
    pseudocode/       One file per pseudocode section
    TODO.md           Task list by level
    notes/            Dated working notes (not binding)
    figures/          Diagrams and their editable sources
    spikes/           Throwaway checks whose results the chain cites
  runs                Symbolic link to src/rotating_frame/examples/
  src/
    rotating_frame/   The importable library (Section 3), including
      cli/            the entry point's body (Section 6),
      defaults/       the shipped rc file (Section 7), and
      examples/       the example run files (TOML)
    scripts/          Thin executable front for cli/ (Section 6)
  tests/
    unit/             One module under test per file
    integration/      Several modules together, or an entry point
    regression/       Frozen reference outputs
  .claude/            Slash commands and reflow helpers
  .rotating_frame/    Machine-local rc overrides (never tracked)
  CLAUDE.md           AI assistant guidance
  README.md           User-facing description
  pyproject.toml      Packaging
```

Output (images, frames) is regenerable from a run file and is
excluded from version control; the run file that produced it is what
is tracked. There is no batch tier and no HDF5 (NG6).

**Everything the tool needs at run time lives under
`src/rotating_frame/`,** because that directory is all that an
installed copy contains (Section 9): the code, the shipped rc
defaults, and the example run files. `runs` at the top level is a
symbolic link so that `runs/turntable.toml` is a short path in a
clone; it is a convenience of a checkout and nothing may depend on it.

---

## 2. The Structural Ideas

Three ideas, each a VISION principle made structural; everything else
in the document hangs off them.

### 2.1 One motion, two descriptions, one source of truth (P2, G2)

The motion is computed once, in the inertial frame, from the true
forces. The rotating-frame description of it is a coordinate
transform: at each sample time `t`, the position and velocity are
carried into the rotating frame by the rotation `R(t)` that the frame
has undergone since `t = 0`, together with the velocity correction
`−Ω × r` that a rotating observer sees. The pseudo-forces are then
*evaluated* from the rotating-frame state, `−m Ω × (Ω × r_rot)`,
`−2m Ω × v_rot`, and `−m (dΩ/dt) × r_rot`, and drawn. Nothing in the
display is computed in the rotating frame; the display reads the
transform.

The rotating-frame *integration* of G2 exists beside this, not
underneath it. It integrates the equation of motion in rotating
coordinates, with the pseudo-forces as forces, from the same initial
conditions, and produces a second trajectory whose only consumer is
a comparison against the transform. The difference is what the
student sees as "numerical error", and the agreement is the proof
that the pseudo-force terms are complete and correctly signed. This
is enforced structurally (Section 6.1): the modules that draw may
not import the modules that integrate.

**Why the inertial frame is exact here.** With the first version's force
fields, none and uniform gravity (NG5), the inertial motion is a closed
form: a straight line, a parabola, or, for the uniform approximation of
the Earth's gravity (Section 4.2), the twice-integrated rotating vector,
which is still a closed form. The motion provider (Section 6.2) returns
the closed form where one exists and integrates only where none does,
and every consumer sees only samples.

### 2.2 Precompute, then view (G5)

Every particle is an independent one-body problem in a given force
field (NG4), and every run is finite: a duration from the run file,
optionally cut short by a stopping rule (the projectile lands, the
puck leaves the disc). So the whole run, every particle at every
sample time, in both frames, with the pseudo-forces at each sample,
is computed *before* anything is drawn, and stored as arrays:

```
  inertial[particle_index, sample_index, component]      position, velocity
  rotating[particle_index, sample_index, component]      position, velocity
  pseudo[particle_index, sample_index, term, component]  three vectors
```

The interactive tier then never integrates during display. Play,
pause, reverse, step, and jump are changes to `sample_index`, and
reverse is exact because it reads the same samples backwards. Two
runs of one file are identical regardless of how they were scrubbed
(Section 8.6 tests this). A change to the run itself, the rotation
rate or a launch (P4), rebuilds the store, which for the first
version's closed forms is instantaneous.

### 2.3 The frame is an object (FD1, FD2)

Everything that depends on how the frame moves, the rotation `R(t)`,
the angular velocity `Ω(t)`, and its rate of change, is asked of one
`Frame` object and computed nowhere else. The first version's frame
rotates about a fixed axis through a fixed origin at a constant rate
(NG3), so `R(t)` is a rotation by `Ω t` and `dΩ/dt` is zero. A
varying rate (FD2) changes the object's answers and nothing that
asks. A translating origin (FD1) adds terms the object would supply
and the transform would consume. The pseudo-force terms and the
rotating-frame equation are written against the object, so the Euler
term is present from the start (G3) with a zero coefficient.

---

## 3. Module Map

The package is `src/rotating_frame/`. Subpackages are named for a
concern, and each module has one responsibility. The skeleton's
placeholders (`core/motion.py`, `run/run_file.py`, the trail
renderer) are replaced by the modules below under DESIGN and
PSEUDOCODE sections of their own.

### 3.1 `core/` — Foundations

| Module | Single responsibility |
| --- | --- |
| `units.py` | The units boundary: presets and SI at the edge (P11); |
| | the only module that imports pint |
| `natural_units.py` | The dimensionless scaling used inside the core |
| `frame.py` | The `Frame` object: axis, rate, `R(t)`, `Ω(t)`, |
| | `dΩ/dt`, and the transforms of `r` and `v` (Section 2.3) |
| `presets.py` | Named frames with real units: a turntable, a |
| | merry-go-round, the Earth at a latitude |

`natural_units.py` fixes the scaling: times in units of `1/Ω`,
lengths in units of a scale `L` the run file names, so that a
turntable and the Earth are the same computation and a run is
characterized by the launch speed compared with `Ω L` (P11).
`frame.py` holds the inertial-to-rotating transform and its inverse;
`presets.py` is where "Earth at 39° latitude" becomes an axis tilted
by the colatitude, a rate, and a length scale.

### 3.2 `forces/` — What acts on the particle

| Module | Single responsibility |
| --- | --- |
| `force_interface.py` | The contract every force field satisfies |
| `fields.py` | The two first-version fields: none, uniform gravity |

The interface requires the force at `(t, r, v)` in **inertial**
coordinates, and *optionally* declares that the resulting motion has
a closed form (Section 6.2). Uniform gravity comes in two kinds that
a run file must choose between, because they are different
approximations (Section 4.2): **space-fixed**, the room's gravity on
a merry-go-round, a constant vector in the inertial frame; and
**frame-fixed**, the uniform approximation of the Earth's central
field made at the launch point, a constant vector in the rotating
frame and therefore a rotating vector in the inertial one. The
frame-fixed field is constructed with the frame, because it is
defined through it. No consumer may branch on which field it holds
(P10). Central gravity, a central attraction, and a spring (FD6)
arrive as new entries in `fields.py` with no change downstream.

### 3.3 `launch/` — What is thrown

| Module | Single responsibility |
| --- | --- |
| `launch_spec.py` | Initial position and velocity of each particle, |
| | given in either frame and converted to the inertial |
| | one at `t = 0` |
| `ring.py` | A ring of `N` particles launched toward a common |
| | point (G4), as `N` launch specs |

A launch is plain data. Giving it in the rotating frame is what a
student on the turntable means by "I threw it straight at the
center"; giving it in the inertial frame is what an observer in the
room means. The conversion is the frame's job and happens once.

### 3.4 `motion/` — How each particle moves

| Module | Single responsibility |
| --- | --- |
| `motion_provider.py` | The contract: launch, force, frame, duration |
| | → inertial samples |
| `closed_forms.py` | The line, the parabola, and the rotating-gravity |
| | parabola, sampled exactly |
| `equations_of_motion.py` | The inertial equation, and the rotating- |
| | frame equation with the pseudo-forces (for the |
| | check, and for future fields) |
| `integrators.py` | Time-stepping schemes, selectable per run |
| `stopping.py` | The stopping rules: duration, landing, leaving |
| | the disc |

`motion_provider.py` is the seam that lets an exact motion and an
integrated one be interchanged (P10, Section 6.2); the first version
takes the closed form whenever the field offers one, which is always.
`equations_of_motion.py` holds the rotating-frame equation because
that is the one thing that must be integrated numerically by design
(G2): its only purpose is to be compared with the transform.

### 3.5 `pseudoforces/` — The three terms

| Module | Single responsibility |
| --- | --- |
| `terms.py` | Centrifugal, Coriolis, and Euler vectors from `Ω`, |
| | `dΩ/dt`, `r_rot`, `v_rot`, each separately (G3) |

One small module, imported by two neighbors that must agree: the
rotating-frame equation (Section 3.4) adds the terms to the force, and
the results store (Section 3.7) records them for display. Writing
them once is what makes the drawn vectors and the integrated check
the same terms (P13, "one word": one code).

### 3.6 `analysis/` — Is it right?

| Module | Single responsibility |
| --- | --- |
| `conservation_monitor.py` | Energy in the inertial frame, the |
| | Jacobi integral in the rotating one (P3) |
| `comparison.py` | The rotating-frame integration against the |
| | transform: the disclosed error, per sample (G2) |
| `closed_form_deflections.py` | The textbook deflections, to the |
| | order they hold, for overlay and for the tests (G7) |

These are runtime components, not test helpers: the monitor's output
is on screen, and the comparison is the number the student reads as
"numerical error".

### 3.7 `run/` — The reproducible unit of work

| Module | Single responsibility |
| --- | --- |
| `run_spec.py` | Complete description of a run, as data (G6) |
| `schema.py` | The run-file keys, types, defaults, and validation |
| `serialization.py` | Load a run file; write the resolved copy back |
| `rc.py` | The rc settings and where they are looked for |
| `results_store.py` | The precomputed arrays and their access |
| | interface (Section 6.4) |
| `driver.py` | Run the whole thing from a spec: launches → motion |
| | → transform → pseudo-forces → check → store |

A run spec holds the frame, the force field, the launches, the
duration and stopping rule, the integrator and fidelity settings for
the check, the exaggeration factor on `Ω` (P12), and the viewpoint.
It is plain data with no behavior. `driver.py` is the one place that
knows the order of the stages.

### 3.8 `geometry/` — Derived display geometry

| Module | Single responsibility |
| --- | --- |
| `frame_axes.py` | The two triads: the rotating frame's axes as |
| | seen from the inertial view, and the inertial axes |
| | as seen from the rotating view |
| `stage.py` | The disc, the floor, or the patch of ground at a |
| | latitude that the particle moves over |
| `trails.py` | The trail through the samples up to the current |
| | one, in each frame |

This group computes *what* the constructions are, in scene
coordinates, and draws nothing. Keeping it out of `render/` is what
keeps the renderer replaceable (P9).

### 3.9 `render/` and `ui/` — Presentation

| Module | Single responsibility |
| --- | --- |
| `render/offscreen.py` | The window-class rule; imports no VTK |
| | (inherited) |
| `render/palettes.py` | Light, dark, color-blind-safe encodings (P6) |
| `render/scene_description.py` | Renderer-agnostic list of drawables |
| | for both views |
| `render/vedo_renderer.py` | Realizes the two views side by side in |
| | one window with vedo / VTK; the only module |
| | that imports vedo |
| `render/panels.py` | The 2D panels: pseudo-force magnitudes |
| | against time, the comparison error, the |
| | conservation readouts |
| `ui/session_state.py` | What is being viewed: sample index, |
| | playing or paused, direction, speed, which |
| | view, which vectors are shown |
| `ui/controls.py` | The key bindings and what each does |
| `ui/vedo_controls.py` | The live controls source, and a scripted |
| | one for tests and `--frames` |
| `ui/interactive_session.py` | The loop |

The two views are two sub-renderers of one vedo window with one
shared clock, so that a keystroke advances both; a single-view mode
shows either alone.

### 3.10 `cli/` and `scripts/` — Entry points

Section 6 of the skeleton's document, kept as it stands: the body of
the one command is `cli/rfsim.py`; `cli/support.py` and the front
`scripts/rfsim.py` are inherited from the suite (`PSEUDOCODE.md`
row 0).

---

## 4. Two Decisions the Map Depends On

### 4.1 Three dimensions, always

A puck on a turntable moves in a plane, and it would be tempting to
make the first version two-dimensional. It is not: the Earth
scenarios need the vertical, the merry-go-round throw needs it, and
the Coriolis term `−2m Ω × v` is a three-dimensional cross product
whose vertical component (the eastward deflection of a drop) is one
of the demonstrations. So every position and velocity is a
three-vector, and the puck is a particle launched in the plane
`z = 0` with no force, which stays there. The stage (Section 3.8)
draws the disc so the plane is visible.

### 4.2 Where gravity lives

The true gravity of a spherically symmetric Earth is central, toward
the center, and static in the inertial frame; rotating the Earth
changes nothing about it. The textbooks nevertheless derive the
Coriolis deflections with a *uniform* `g` that is constant in the
rotating frame, and the tool follows them, for a reason worth
stating exactly. Over a flight of seconds near a point `P` on the
surface, the central field is replaced by a uniform one pointing
from `P` toward the center. `P` is carried around the axis, so in the
inertial frame the direction of that uniform field turns at the rate
`Ω`; in the rotating frame `P` is at rest and the field is a constant
vector. Nothing physical turns. The approximation is tied to the
point where it is made, and that point rides the frame.

So "uniform gravity" is two different approximations, and the run
file must say which (Section 3.2):

- **Space-fixed**, for a merry-go-round: the room's gravity, a
  constant vector in the inertial frame. Because the axis is
  parallel to it, it is constant in the rotating frame too, and the
  two kinds coincide.
- **Frame-fixed**, for the Earth: the uniform approximation of the
  central field at the launch point, constant in the rotating frame.
  In the inertial frame it is a rotating vector, and the motion is
  still a closed form: the vector integrated twice. Computing the
  eastward deflection of a dropped stone, `d = (1/3) g Ω t³ cos λ`
  to first order, with a space-fixed `g` instead gives a different
  answer at the same order as the effect, which is why the choice is
  the run file's and not a default.

**The magnitude is the bare attraction.** Textbooks fold the
centrifugal term into an effective `g` and then show Coriolis alone.
This tool draws the centrifugal vector separately (G3), so the
uniform field it uses is the gravitational attraction itself, about
9.82 m/s² at the surface, and the centrifugal term at the launch
point supplies the rest: its sum with the attraction is the tilted,
slightly weaker effective gravity that a plumb line shows. Using the
measured `g` would count the centrifugal term twice. The oracles of
Section 8.2 are therefore written in terms of the effective gravity
and the plumb-line vertical, as the textbooks' `g` and "vertical"
are.

**Coordinates.** The frame's origin is on the axis, at the Earth's
center for the Earth presets, and positions are measured from it
(Section 2.3, NG3). The centrifugal term at a surface point is then
a constant vector plus a small position-dependent part, both
computed by the one module (Section 3.5) with no special case. The
display works relative to the launch point (Section 3.8), and double
precision holds six million metres and a millimetre deflection at
once, since its relative precision is `1e-16`.

**What this does not model** is that the Earth's gravity is central
and that the surface has settled perpendicular to the plumb line.
Central gravity is a future field (FD6) that would show where the
uniform approximation fails; the Earth's shape is FD3. Every Earth
run says on screen that it uses the uniform approximation, with the
condition under which it holds (the flight is short compared with
the Earth's radius).

---

## 5. Dependency Graph

Dependencies point downward only. No module may import from a group
listed above it, and this is tested (Section 8.6).

```
  scripts/  (front only; imports cli/ and nothing else)
  cli/
    +-- ui/
    |     +-- render/
    +-- run/          (driver, results_store, run_spec, schema, rc)
          +-- analysis/
          +-- geometry/
          +-- motion/
          |     +-- pseudoforces/
          +-- launch/
          +-- forces/
          +-- core/
```

Within the physics groups: `motion/` imports `forces/`, `launch/`,
`pseudoforces/`, and `core/`; `pseudoforces/` imports only `core/`;
`analysis/` imports `motion/` (to run the check) and `pseudoforces/`;
`geometry/` imports `core/` only, because it works from stored
samples. `render/`, `ui/`, and `geometry/` import nothing from
`motion/` (Section 6.1).

---

## 6. Key Boundaries

Six seams exist specifically to protect a VISION principle. Each is
an interface that must remain stable.

### 6.1 The ground-truth boundary (P2, G2)

The display draws the results store and nothing else. Nothing under
`render/`, `ui/`, or `geometry/` imports from `motion/`; the
rotating-frame integration's only exit is `analysis/comparison.py`,
whose only product is a per-sample difference that the store holds
beside the trajectory. A test asserts both. This is the structural
form of "the rotating frame is a coordinate transform of the inertial
one, never the source of the picture".

### 6.2 The motion-provider boundary (P10)

`motion_provider.py` defines one operation: given a launch, a force
field, a frame, and a duration with a stopping rule, return the
inertial samples. `closed_forms.py` implements it exactly for the
fields that declare a closed form; `integrators.py` implements it
numerically for any field. Every consumer sees only the samples.
The test that certifies this boundary is the numerical provider
reproducing the closed form on every first-version field to a stated
tolerance (Section 8.2).

### 6.3 The force boundary (NG5, FD6)

`force_interface.py` requires the force at `(t, r, v)` in inertial
coordinates and permits an optional closed-form declaration. The two
first-version fields supply both. Consumers ask for the closed form
by capability, never by field type. A central attraction and a spring
arrive as new fields with no change downstream, and the pendulum's
constraint (FD5) is the one addition that would need the interface
to grow, which is why it is a future direction and not a field.

### 6.4 The results-store boundary (G5)

`results_store.py` hides how the precomputed run is held. It offers:
the inertial and rotating state of a particle at a sample; the three
pseudo-force vectors there; the comparison error there; the
conservation readouts there; the sample times; and the store's size.
The scrubber and the panels speak only to this interface.

### 6.5 The renderer boundary (P9)

The driver does not know what happens to a completed store. Only
`vedo_renderer.py` imports vedo or VTK; a different backend is a new
module in `render/` and nothing else changes. `scene_description.py`
is the renderer-agnostic list of what to draw, built from the store
and `geometry/`.

### 6.6 The units boundary (P11)

The core works in the natural units of `natural_units.py`. Real
units enter at exactly one place, `core/units.py`, which is the only
module permitted to import pint, and they enter through named presets
in the run file (`frame = "earth"` with `latitude = "39 deg"`;
`frame = "turntable"` with `rate = "33.3 rpm"`) or through explicit
dimensioned values that the boundary converts. Display formats a
natural-unit value back into the preset's real units, with the scale
factor stated, and with the exaggeration factor on `Ω` stated beside
it whenever it is not one (P12). Below `run/`, no module imports
pint, accepts a pint object, or returns one; a test enforces this.

---

## 7. Configuration

Two mechanisms hold different kinds of thing, and the division is a
rule.

**The rc file** (`rfsimrc.py`) holds what is *machine-dependent and
rarely changed*: window size, preferred palette, glyph and vector
sizes, output directory. It is looked for in the working directory,
then in `$ROTATING_FRAME_RC`, and last in the package itself
(`rotating_frame/defaults/rfsimrc.py`), which is the documented set
of defaults and is always present, in a clone and in an installed
copy alike. `rfsim --write-rc` copies that file into the working
directory for a user who wants to change it.

**The run file** (TOML) holds the *physics*: the frame and its rate,
the exaggeration factor, the force field and its kind, the launches,
the duration and stopping rule, the fidelity of the check, and the
viewpoint.

```
  rc file defaults  <  run file  <  command-line arguments
```

> **Any value that can affect a computed trajectory, a drawn
> pseudo-force, or the comparison must live in the run file, never
> only in the rc file.** The rc file may supply its default, but the
> run file records the resolved value that was used.

A run file must be self-contained: handing it to another user on
another machine reproduces the same arrays. Nothing in the first
version is stochastic; if a ring ever gains random launch angles, the
seed becomes a required key, as in the scattering tool.

---

## 8. Testing Strategy

### 8.1 Layers

| Directory | Scope |
| --- | --- |
| `tests/unit/` | Pure functions: the transform, the three terms, the |
| | closed forms, the schema, unit round-trips |
| `tests/integration/` | Stages together: launch → motion → transform |
| | → check; a whole run from a file |
| `tests/regression/` | Whole runs against stored reference output |

### 8.2 Oracles

VISION G7 makes closed-form cases the standard of correctness. The
oracles are:

- The transform is a rotation: distances from the axis and speeds
  relative to the frame agree between the two descriptions at every
  sample, to floating-point precision.
- The free particle: its rotating-frame description is the closed
  spiral, and its rotating-frame integration reproduces it to the
  integrator's tolerance.
- The dropped stone at latitude `λ`: the eastward landing offset
  equals `(1/3) g Ω t³ cos λ` to the order that formula holds, with
  `g` the effective gravity and "vertical" the plumb line (Section
  4.2), the next order estimated, and the tolerance set from it.
- The projectile at latitude `λ`: the horizontal deflection to the
  same order, in the same terms.
- The plumb line: the attraction plus the centrifugal term at the
  launch point is tilted from the radial direction by the textbook
  angle, about `0.1°` at mid-latitudes, and shorter by `Ω² R cos² λ`.
- The ring: `N` particles launched toward a common point with the
  same speed veer in the same sense, and the picture is symmetric
  under rotation by `2π/N`.
- Space-fixed versus frame-fixed gravity: the two kinds give the same
  motion when `Ω` is parallel to the field and different motion when
  it is not, by the amount the closed forms predict.

### 8.3 Invariants

Asserted wherever the quantity is produced:

- Energy is conserved along every inertial trajectory for a
  space-fixed field; the Jacobi integral is conserved in the rotating
  frame for a frame-fixed one, to the tolerance the integrator
  implies.
- The three pseudo-force vectors, summed and added to the true force,
  equal `m` times the rotating-frame acceleration obtained by
  differencing the transformed samples, to the differencing error.
- The Euler term is identically zero while `dΩ/dt` is.
- A stopping rule never leaves a sample past the stop.

### 8.4 Tolerance policy

Every numerical tolerance is **derived and justified**, not tuned,
with the reasoning in a comment beside it: from the integrator's
order and step, from floating-point precision, or, for the textbook
deflections, from the size of the next-order term. Nothing here is
statistical.

### 8.5 Reference-output governance

A file in `tests/regression/reference_outputs/` is a claim about
correct behavior, and may be created only from a case checked
against an oracle or verified by hand. Regenerating one requires the
commit message to say what changed and why the new values are more
correct. References are stored as compact, diff-reviewable text.

### 8.6 Architectural tests

Mechanically checkable, so tested rather than left to discipline:

1. **The ground-truth rule of Section 6.1.** Nothing under `render/`,
   `ui/`, or `geometry/` imports from `motion/`.
2. **The import rule of Section 5.** No physics group imports from
   `render/`, `ui/`, or `run/`; `pseudoforces/` imports only `core/`.
3. **The units boundary of Section 6.6.** No module outside
   `core/units.py` imports pint.
4. **The determinism guarantee of Section 2.2.** The same run file
   produces an identical store on two runs, and scrubbing the store
   in any sequence leaves it unchanged.
5. **The installed-copy guarantee of Section 9.** The inherited
   `tests/unit/test_installed_copy.py`.

---

## 9. Build System: The Two Ways In

Python 3.10 or later, NumPy-based numerical core, vedo/VTK rendering,
pint at the units boundary, TOML run files. The tool reaches a user
in two ways that run the same code (Section 3.10).

**Route A: the `physdemo` suite, for a shared computer.** The tool
is one member of the suite (`github.com/UMKC-CPG/physdemo`): a set
of course demonstration tools that share one Python environment and
one `bin/` directory of commands. One person installs the suite;
everyone else only sources its `activate.sh`. The tool is *linked*,
never copied and never pip-installed into the suite, so a clone
stays live. The suite's contract (its `dev/ARCHITECTURE.md` section
4) says what this repository must do to be linked, and
`physdemo-check-tool .` verifies it.

**Route B: `pip install`, for a personal computer.** The tool
installs like any Python package, with its dependencies, into an
environment the user makes:

```
python -m venv physdemo
source physdemo/bin/activate        (Windows: physdemo\Scripts\activate)
pip install https://github.com/UMKC-CPG/rotating_frame/archive/refs/heads/main.zip
rfsim --check
```

This is why everything the tool needs at run time is inside the
package (Section 1), and why `pyproject.toml` **declares the
dependencies**: on this route nobody else will supply them.

**Who owns the versions.** The suite's `requirements.in` is the
single statement of what the course tools need; `pyproject.toml`
repeats the subset this tool imports, with lower bounds no tighter
than the suite's. This tool adds `scipy` (integrators), `pint` (the
units boundary), and `matplotlib` (the panels) to the skeleton's
`numpy`, `vedo`, and `vtk`; all are already in the suite.

**Offscreen drawing** (`--offscreen --frames N`, `--check`, the
tests) chooses VTK's window class by the suite's rule: EGL on Linux
whenever offscreen drawing is asked for, nothing on macOS or Windows
(`render/offscreen.py`). There is no batch tier (NG6); headless use
is this capture.

**What has been tried.** Nothing yet on this tool; the skeleton it
came from was tested on Linux on both routes.

---

## 10. Development Checkpoints

Each level of the chain gets a tagged baseline when first considered
complete, so later drift is measured against a fixed point:

```
v0.1-vision          VISION.md complete                       (done)
v0.2-architecture    ARCHITECTURE.md complete
v0.3-design          Design sections for the first version complete
v0.4-pseudocode      Pseudocode sections for the first version
v0.5-motion          Closed forms, the transform, the three terms,
                     the check; validated (G2, G7)
v0.6-scene           Two views, scrubber, vectors, the turntable
                     and merry-go-round runs (G1, G3, G4, G5)
v0.7-earth           Latitude presets, the drop and the projectile,
                     the ring (G4, G7)
v1.0-classroom       Usable in a graduate mechanics course
```

Work proceeds on short-lived topic branches merged into `main`.
