# Design 9: The Scene and Its Two Views

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.8 (`geometry/`) and
> 3.9 (`render/`), and the renderer boundary 6.5; serves G1 (two
> frames at once), G3 (every term drawn), P5 (transparency), P6
> (encodings), P9, and P12 (labeled distortions). Uses Designs 1, 2,
> 5, 6, and 8. *Status: reviewed; ratified 2026-09-22.*

The display reads the results store and draws it twice: once as the
room sees it and once as the rider sees it. This section fixes the
two views and their cameras, the renderer-agnostic scene description,
the geometry each view is built from (triads, stage, trails,
glyphs, arrows), the two arrow scales and the rule that states them,
the palettes and the redundancy rule, the panels, and the readouts.

---

## 9.1 Two views, one clock

One window, two sub-renderers side by side: **inertial** on the left,
**rotating** on the right, each with its own camera, both showing the
sample `k` the session holds (Design 10). A keystroke that changes
`k` changes both. The run file's `views` key, and a key in the
session, select `both`, `inertial`, or `rotating`; a single view
fills the window.

**Cameras.** Each view's camera is described in that view's axes by
the run file's `[view].camera` (azimuth, elevation, distance, in
units of `L`), so the two views start from the same vantage relative
to their own axes. The rotating view's camera rides the frame: it
looks at the launch point `P`, which is fixed there, and the stage
and the local axes never move. The inertial view's camera keeps its
orientation fixed in space, and its target is a choice the run file
and the session make:

- **follow** (default): the target is the launch point's inertial
  position `R(t̃_k) r̃_P`, so the camera translates with `P` and turns
  not at all. On the Earth this is the only usable choice: the launch
  point moves at `Ω R_E cos λ`, over three hundred metres a second,
  so a fixed camera at the scale of a throw would lose the scene in
  a fraction of a second. The screen says `camera follows P` (P12).
- **fixed**: the target is `r̃_P` at `t̃ = 0`. On the turntable, where
  `P` is on the axis, the two are the same; on the merry-go-round
  the platform sweeps past a fixed camera, which is its own lesson.

A following camera is a translating, non-rotating vantage, not a
rotating one: the inertial triad stays put on screen while the
rotating triad turns, and nothing is transformed but the camera's
target. The mouse orbits, pans, and zooms each view independently,
as vedo provides; `Ctrl+0` in the session restores the run file's
cameras (Design 10).

**Rejected: two windows.** Harder to keep in step, and the side-by-
side is the picture of G1. **Rejected: one view with both triads
drawn.** Two triads in one scene ask the student to do the transform
in their head, which is the thing the tool is for.

## 9.2 The scene description

`render/scene_description.py` builds, for a sample `k` and a view,
a plain list of drawables from the store and `geometry/`, and knows
nothing about vedo (A6.5). A drawable is a kind and its data:

```
  polyline   points (n, 3), role, width, style ("solid" | "dashed" |
             "dotted"), label (optional, at the last point)
  arrow      base (3,), tip (3,), role, label at the tip
  glyph      center (3,), radius, role, label (optional)
  triad      origin (3,), three axes (3, 3), role, three labels
  surface    a disc or a rectangle: points and faces, role, and its
             markings (spokes, a grid, a compass rose) as polylines
  text       a block of lines, a screen corner, role
  image      an RGB array and a screen rectangle (the panels, 9.6)
```

`role` names a palette entry (9.5), never a color. The renderer
realizes each kind and holds the actors between frames, replacing
only what changed: the static drawables of a view (the stage and the
fixed triad in the rotating view; the fixed triad in the inertial
one) are built once, and the per-sample drawables are rebuilt at
each change of `k`. The tests of 9.8 read the description without a
renderer.

## 9.3 Geometry

`geometry/` computes points in each view's scene coordinates, which
are the natural units of the run (`L = 1`), from the store, and
draws nothing.

**The triads** (`frame_axes.py`, Design 1.6). Each view draws its
own axes fixed and the other frame's axes moving: in the inertial
view, the inertial triad at `O` and the rotating triad, the columns
of `R(t̃_k)`, turning; in the rotating view, the rotating triad and
the inertial triad, the columns of `R(t̃_k)ᵀ`, turning the other way.
The moving triad is labeled with primes. On the Earth the triads at
`O` are `R̃_E` away from the scene; the view draws the *local* triad
`(ê_E, ê_N, ê_U)` at `P` instead, fixed in the rotating view and
turning in the inertial one, and shows `n̂` as a short arrow at `P`
tilted by the colatitude, so that the axis the frame turns about is
visible from where the student stands. Triad length: `0.25` of the
scene's extent.

**The stage** (`stage.py`). One surface per preset, with markings
so that its rotation can be seen:

- *turntable*: a disc of radius `1` at `ρ̃_U = 0`, eight spokes and a
  rim; it turns in the inertial view and is fixed in the rotating
  one. A puck that leaves it (Design 4.5) is not drawn falling: its
  trail ends at the rim, which is what the stopping event means.
- *merry-go-round*: the platform disc at height `0` with spokes,
  turning in the inertial view; and the floor, a grid at the same
  height beyond the platform's rim (the platform is flush with the
  floor, Design 2.4), fixed in the inertial view and turning the
  other way in the rotating one, since the floor belongs to the
  room. A ball lands at height zero whether over the platform or
  over the floor.
- *Earth*: a square ground patch through `P` perpendicular to `ê_U`,
  of side four times the scene's extent, with a grid and a compass
  rose marking east and north; the local meridian is drawn as a
  line toward north. In the inertial view the patch turns with the
  Earth, imperceptibly over a throw, which is itself honest: the
  triad at `P` and the following camera carry the motion the eye
  cannot see in the patch. The Earth's curvature is not drawn,
  consistently with the uniform approximation (Design 3.4.2); the
  screen's approximation note says so.

**The trails** (`trails.py`). For each particle, the polyline through
its stored samples `0 … k` in the view's frame, solid, in the
particle's role; past the particle's stop it ends at the event
sample. In the rotating view three more polylines may be drawn for
the tracked particle, each whole, over the particle's valid samples,
since each is a prediction the student compares the trail against:
the check's path (Design 6.1), dashed; the ghost path (Design 6.2),
dotted, which is the picture of where the rider expected the ball to
go, with a small marker at the ghost's own sample `k` so that the
expected ball and the real one can be compared as they move; and the
first-order overlay (Design 6.5), thin, where it applies. Each is
labeled at its end, so that the styles are redundant with words
(P6). A whole path is also built once and kept between frames, which
a growing dashed line could not be.

**The glyphs.** A sphere at each particle's sample `k`, radius from
the rc file as a fraction of `L`; the tracked particle's glyph is
larger and carries its label.

**The arrows** (Design 5.3). In the inertial view, at the tracked
particle: the true force `f̃_in` and the velocity `ṽ_in`. In the
rotating view: the true force `f̃_rot`, the three terms, their sum,
and `ṽ_rot`. Each arrow's base is the glyph and its tip is the base
plus the vector times a scale (9.4); each carries its word at the
tip. The velocity arrow has its own scale, `1 unit of ṽ` to a
quarter of the scene, since velocity and acceleration are not
commensurable.

## 9.4 Two arrow scales, both stated

Accelerations of very different sizes must be drawn in one picture.
On the Earth, in natural units with `L = 100 m`, gravity is
`1.85 × 10⁷`, the centrifugal term `4.5 × 10⁴`, and the Coriolis term
for a `10 m/s` throw `2.7 × 10³`: four orders of magnitude between
the arrow the picture needs and the arrows the tool exists to show.
On the turntable all three are of order one. So:

- The **true force** and the **sum** share one scale, `s_true`, and
  the **three pseudo-force terms** share another, `s_pseudo`. In
  `auto` mode each scale is chosen so that the largest arrow of its
  group at the launch is a quarter of the scene's extent, and the
  ratio `s_pseudo / s_true` is printed on screen as a labeled
  distortion, `pseudo-force arrows × 6800 relative to gravity`
  (P12). When the ratio would be within a factor of three of one, as
  on the turntable, the two scales are made equal and the note is
  omitted.
- `same` mode forces one scale for all arrows, which on the Earth
  makes the pseudo-force arrows invisible; it is offered because
  seeing them vanish is the honest picture of their size, and the
  screen then says which arrows are below a pixel.
- The rc file's `arrow_scale` multiplies both.

The scales are part of the distortion column of the error panel
(Design 6.4). **Rejected: a logarithmic arrow length.** It would make
the sum arrow no longer the sum of the others, and G3's picture is
that the arrows add.

## 9.5 Palettes and the redundancy rule

`render/palettes.py` holds three palettes, `light`, `dark`, and
`colorblind`, each a complete map from role to color, with the same
roles in each (a test checks):

```
  background, text, inertial_axes, rotating_axes, local_axes,
  stage, stage_marks, floor, trail_0 … trail_11 (cycled by particle),
  check, ghost, overlay, true_force, centrifugal, coriolis, euler,
  sum, velocity, glyph, tracked_glyph
```

**No distinction that carries meaning rests on color alone** (P6):
every arrow carries its word; every extra path has a style and a
label; the tracked particle is larger and labeled; the two triads
differ by primes; the two views are titled. Colors are the second
channel, and the `colorblind` palette is built from a palette with
that property. A ring's members are told apart by color and, for the
tracked one, by label; the others are not individually meaningful,
which is why that is enough.

## 9.6 The panels

Two-dimensional panels are drawn with matplotlib into RGB images and
placed in the window as `image` drawables, as the scattering tool
does, in a strip along the bottom, each with a key to hide it
(Design 10):

1. **terms against time**: `|f̃_cf|`, `|f̃_co|`, `|f̃_eu|`, and `|f̃_rot|`
   for the tracked particle over the whole run, on a log axis when
   they span more than two decades, with a cursor at `t̃_k`;
2. **the error budget**: the three columns of Design 6.4, as text
   with the numbers at `t̃_k` and the run's maxima (drawn as text in
   the strip, not as an image, since it changes with every sample);
3. **conservation**: the drift of `E` and of `J` along the exact
   path and the check, or the sentence saying why one is not
   reported (Design 6.3).

The key legend is not a panel: it is a text block of its own
(9.7), with its own switch, so that it can be shown while the panel
strip is hidden.

A plotted panel is drawn once per run, tracked particle, and
palette, and kept; the cursor is a line drawn over the image. A
panel that is redrawn every sample costs more than the whole 3D
scene and would set the frame rate by itself.

## 9.7 The readouts

A text block in each view's corner, updated per sample:

- the time, `t̃_k` and `t_k` in the preset's units, and the frame's
  angle `θ_k` in degrees;
- for the tracked particle, in the rotating view: its launch as
  given (speed, azimuth, elevation, or components, and the frame),
  which the run controls of Design 10 change; its position as
  `(E, N, U)` from `P` and speed, in real units; the magnitude of
  each drawn arrow in `m/s²` (and in newtons when a mass is given);
- the scale note: `1 unit = L`, `1 time unit = T`, the exaggeration
  `× α` when not one, the arrow-scale ratio when not one, and
  `camera follows P` when it does;
- the approximation note of Design 3.4.2, with its number, on the
  Earth;
- the legend of key chords (Design 10.5), in the lower left, with
  its own switch;
- the drawing rate, frames per second over the last thirty frames,
  so that a slow display is seen and not guessed, and the site
  notes can record a measured number.

Every number is formatted back through the boundary (Design 2.5),
so the screen never shows a natural-unit value without saying so.

## 9.8 Verification

- The scene description for each packaged run at several `k`, built
  without a renderer: the inertial view has exactly two arrows at
  the tracked particle and none named for a pseudo-force; the
  rotating view has six; every arrow and every extra polyline has a
  label; the moving triad's axes are the columns of `R(t̃_k)` or its
  transpose to `10⁻¹⁴`; the stage's markings turn by `θ_k` in the
  view where they turn and not at all in the other.
- Arrow tips minus bases equal the stored vectors times the stated
  scales; in `auto` mode the largest of each group at `k = 0` is a
  quarter of the extent; on the turntable the two scales are equal
  and no ratio is reported; on the Earth the ratio is reported and
  is what the store implies.
- Every palette has every role; the `colorblind` palette's arrow
  colors are pairwise distinguishable under the two common
  deficiencies (a table of simulated colors, checked once, as the
  scattering tool does).
- The panels render to arrays of the requested size with no
  exception for every packaged run at `k = 0` and `k = N − 1`.
- Offscreen: `--frames 3 --screenshot` on every packaged run writes
  a non-blank image whose pixels change between frames (the
  inherited pixel rule); the `--check` self-test does the same.
- A run with `views = "inertial"` and one with `"rotating"` each
  draw one sub-renderer, and toggling in a scripted session (Design
  10) changes the count.

## Sources

The redundancy rule and the palette roles follow the scattering
tool's design section 11; the panel mechanism is its
`render/panels.py`. The camera choice for the Earth is this
section's own.
