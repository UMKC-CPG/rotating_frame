# Pseudocode 9: The Scene and Its Two Views

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 9. Governs
> `src/rotating_frame/geometry/frame_axes.py`, `geometry/stage.py`,
> `geometry/trails.py`, `render/scene_description.py`,
> `render/palettes.py`, `render/vedo_renderer.py`, `render/panels.py`,
> and the tests `tests/unit/test_geometry.py`,
> `test_scene_description.py`, `test_palettes.py`, `test_panels.py`,
> and `tests/integration/test_renderer.py`.
> *Status: reviewed; ratified 2026-09-22.*

**Replaces the skeleton's placeholders** `render/palettes.py` and
`render/vedo_renderer.py` (index row 0). `render/offscreen.py` stays
inherited. `geometry/` imports `core/` only; `render/` imports
`core/`, `run/` (the store and the spec), `geometry/`, and
`analysis/error_budget` through the store's data; only
`vedo_renderer.py` imports vedo, and only `panels.py` imports
matplotlib. Scene coordinates are natural units.

---

## 9.1 The drawables (`render/scene_description.py`)

```
frozen records, each with `role` naming a palette entry (9.4):
    Polyline(points (n, 3), role, width, style: "solid" | "dashed" |
             "dotted", label: str | None, label_at: (3,) | None)
    Arrow(base (3,), tip (3,), role, label, label_at: (3,) | None)
        # label_at: where the word sits, set by spread_labels below;
        #   the tip or the last point when None
    Glyph(center (3,), radius, role, label: str | None)
    Triad(origin (3,), axes (3, 3) as columns, role, labels (3 strings))
    Surface(points (n, 3) AT REST, faces (m, 3 or 4), role,
            rotation (3, 3): what turns the rest points into the
            view's, applied by the renderer as the actor's matrix so
            that a turning stage is one kept actor; markings: list of
            Polyline)
    Text(lines: list of str, corner: "top_left" | "top_right" |
         "bottom_left" | "bottom_right", role)
    Image(rgb (h, w, 3) uint8, rect: (x, y, w, h) in window fractions)

frozen record SceneInfo:
    extent          E: the scene's size, natural units
    scale_true      s_true, scale_pseudo  s_pseudo, scale_velocity
    arrow_ratio     s_pseudo / s_true, or None when equal
    camera_follows  bool
    camera_target   (3,) in the view's coordinates

frozen record ViewScene:
    view      "inertial" | "rotating"
    static    list of drawables built once per run
    dynamic   list of drawables rebuilt per sample
    info      SceneInfo

frozen record Strip:                  # what the panel strip shows
    images    list of (rgb (h, w, 3), cursor_fraction: float | None)
    lines     tuple of str            # the budget, as text (9.6)
```

## 9.2 `geometry/`

```
# frame_axes.py
function moving_triad(frame, time, view) -> (3, 3):
    return frame.rotating_triad_in_inertial(time) if view == "inertial"
           else frame.inertial_triad_in_rotating(time)   # Pseudocode 1.5

function triads(spec, view, time, extent) -> list of Triad:
    length = 0.25 * extent
    origin = launch point in this view (R(t) r̃_P or r̃_P)
    if spec.preset.name == "earth":
        local  = column_stack(spec.axes.east, north, up)
        fixed  = local          # this view's own triad, in both views
        moving = R(t) @ local if view == "inertial" else R(t)ᵀ @ local
                 # the rider's triad turning, as the room sees it; or
                 #   the room's copy turning back, as the rider sees it
        also an Arrow at the origin along n̂ (the axis), length,
            role "rotating_axes", label "Ω"
    else:
        fixed = I (this view's own axes), moving = moving_triad(...)
    return [Triad(origin, length * fixed, own role, own labels),
            Triad(origin, length * moving, other role, primed labels)]

# stage.py
function stage_surface(spec, view, time, extent) -> Surface:
    disc(radius = 1, spokes = 8, rim):     turntable; platform, plus a
        floor grid of side 4 E beyond the rim for merry_go_round
    ground(side = 4 E, grid, compass rose E/N, meridian line):  earth
    A part that belongs to the rotating frame (disc, platform, ground)
        is rotated by R(t) in the inertial view; a part that belongs to
        the room (the floor) is rotated by R(t)ᵀ in the rotating view;
        every point is placed relative to the launch point in that view.

# trails.py
function trail(store, i, k, view) -> Polyline:
    points = positions_in[i, :k+1] (inertial) or positions_rot (rotating),
             masked to valid samples; role f"trail_{i % 12}", solid,
             label = the particle's label when i is tracked
function extra_trails(store, spec, i, shown) -> list of Polyline:
    # rotating view; each path WHOLE over the particle's valid samples
    #   (design 9.3), so that it is built once and kept
function ghost_now(store, spec, i, k) -> (3,):   # the ghost's own point
    launch_point + ghost[i, min(k, valid − 1)]   #   at sample k
    check:   positions_rot^check[i, :k+1], role "check", dashed, "check"
    ghost:   launch_point + ghost[i, :k+1], role "ghost", dotted, "ghost"
    overlay: launch_point + ghost + overlay[i, :k+1], role "overlay",
             solid thin, "first order"
    each only when the store holds it and the session shows it
```

## 9.3 Building a view (`render/scene_description.py`)

```
function extent(store) -> float:
    return max(1.0, max over valid samples of |positions_rot − r̃_P|)

function arrow_scales(store, tracked, mode, rc, E, view)
        -> SceneInfo fields:
    true0   = |true_force[tracked, 0]|  (or 1e-30)
    pseudo0 = max over terms of |terms[tracked, 0]|  (or 1e-30)
    s_true   = (E / 4) / true0
    s_pseudo = (E / 4) / pseudo0
    if mode == "same" or 1/3 <= s_pseudo / s_true <= 3:
        s_pseudo = s_true; ratio = None
    else: ratio = s_pseudo / s_true
    # The velocity scale is the view's own and is set by the LARGEST
    #   speed over the run, never the launch speed: a drop is launched
    #   at rest in the rotating frame, and (E / 4) / 1e-30 drew every
    #   later arrow astronomically long (Design 9.4). The arrays are
    #   the store's velocities_in and velocities_rot (Pseudocode 8.5),
    #   filled by the driver and NaN past a particle's stop under a
    #   false mask, so the maximum runs over mask[tracked] only.
    velocities = velocities_in if view == "inertial" else velocities_rot
    speed_max  = max over k with mask[tracked, k] of
                 |velocities[tracked, k]|
    s_velocity = (E / 4) / max(speed_max, 1e-30)
        # the floor is reached only by a particle that never moves,
        #   which draws no velocity arrow at any sample
    return s_true * rc.arrow_scale, s_pseudo * rc.arrow_scale, ratio,
           s_velocity * rc.arrow_scale

function arrows(store, spec, i, k, view, info, shown) -> list of Arrow:
    p_in, v_in, p_rot, v_rot = store.state_at(i, k)
    terms, f_rot = store.terms_at(i, k)
    if view == "inertial":
        f_in = R(t) @ f_rot
        candidates = [("true", f_in, s_true, "true force"),
                      ("velocity", v_in, s_velocity, "v")]
        base = p_in
    else:
        candidates = [("true", f_rot, s_true, "true force"),
                      ("centrifugal", terms[0], s_pseudo, "centrifugal"),
                      ("coriolis", terms[1], s_pseudo, "Coriolis"),
                      ("euler", terms[2], s_pseudo, "Euler"),
                      ("sum", f_rot + sum(terms), s_true, "sum"),
                      ("velocity", v_rot, s_velocity, "v")]
        base = p_rot
    return [Arrow(base, base + scale * vector, role = name, label)
            for name, vector, scale, label in candidates if name in shown]

function readouts(store, spec, state, info, view, frame_note = None)
        -> Text:                                              # Design 9.7
    # frame_note: the session's drawing-rate line (10.4), appended
    #   last when given, so that a slow display is seen and not guessed
    lines: time (t̃_k, format_real(t_k, "time"), θ_k in degrees);
           for the tracked particle in the rotating view: the launch as
           given (Pseudocode 7.1 spec), position (E, N, U) and speed in
           real units, each drawn arrow's magnitude in m/s² (and N with
           a mass); the scale note (L, T, "Ω exaggerated × α" if α ≠ 1,
           "pseudo-force arrows × ratio" if ratio, "camera follows P"
           if it does); the approximation note with its estimate on the
           Earth.
    every number through units.format_real with the preset's display
    units; the Earth's deflection readouts in "cm" when below 1 m.

function describe_view(store, spec, state, rc, view) -> ViewScene:
    # state: the session state of Pseudocode 10.2 (k, tracked, arrows,
    #   paths, scenery, camera_mode, arrow_mode, legend).
    E    = extent(store); info = arrow_scales(...)
    # arrow_scales takes the view too: the velocity scale is the
    #   view's own largest speed over the run (on the Earth the
    #   inertial velocity is the ground's plus the throw; one scale
    #   would make one of the two arrows invisible or enormous).
    #   Nothing is compared across the views by the velocity arrow,
    #   so nothing is stated.
    time = store.time_at(state.tracked, state.k)   # the grid's clock:
        # a stopped particle sits at its stop while the stage and the
        #   other particles go on; only the particle's own state is
        #   read at min(k, its valid samples − 1)
    static  = [stage_surface(...) if state.scenery has "stage"]
              + [the fixed triad if "triads"]          # rotating view
              (in the inertial view the stage and the moving triad are
               dynamic, since they turn)
    dynamic = trails for every particle + extra_trails (rotating,
              whole, and a small Glyph in the ghost role at ghost_now
              when the ghost is shown) +
              tracked) + glyphs (tracked larger, labeled)
              + arrows(...) + moving triad + readouts
              + [Text(legend lines, "bottom_right")] if state.legend
                #   and this is the last view shown (the legend is
                #   drawn once, left-justified at a fixed offset on an
                #   opaque background)
        the dynamic list passes through spread_labels(dynamic, up,
            extent) before the readouts are appended: every labeled
            arrow gets label_at just past its tip (LABEL_BEYOND ×
            extent along the arrow), every labeled path its last
            point, and an anchor within LABEL_CLEARANCE × extent of an
            earlier one is moved along the view's up by LABEL_STEP ×
            extent until clear, so that at a landing, where the arrows
            are short and share a base, the words do not pile up
    info.camera_target = R(t) r̃_P if (view == "inertial" and
                          state.camera_mode == "follow") else r̃_P at 0
                          (inertial) or r̃_P (rotating)
    info.camera_basis  = the local (east, north, up) triad as this view
                          sees it at t (R(t) @ local when following in the
                          inertial view); the camera's azimuth, elevation,
                          and up are measured in it
    # Every point of every drawable is expressed RELATIVE TO the camera
    #   target (ARCHITECTURE 4.2: the display works relative to the
    #   launch point), so that VTK's single-precision vertices see
    #   numbers of order the scene and not R_E / L; the camera then
    #   looks at the origin of the scene.
    return ViewScene(view, static, dynamic, info)

function describe(store, spec, state, rc, legend_lines = (),
                  frame_note = None) -> list of ViewScene:
    views = ("inertial", "rotating") if state.view == "both" else
            (state.view,)
    return [describe_view(..., v, legend on the last view, frame_note)
            for v in views]
```

## 9.4 `render/palettes.py`

```
ROLES = ("background", "text", "inertial_axes", "rotating_axes",
         "local_axes", "stage", "stage_marks", "floor", "trail_0", …,
         "trail_11", "check", "ghost", "overlay", "true", "centrifugal",
         "coriolis", "euler", "sum", "velocity", "glyph", "tracked_glyph")
PALETTES = {"light": {...}, "dark": {...}, "colorblind": {...}}
              # every palette maps every ROLE to a color name or hex;
              #   the colorblind palette's arrow colors come from a
              #   deficiency-safe set (the scattering tool's), and the
              #   trail cycle from a categorical set of twelve
PALETTE_NAMES = tuple(PALETTES)
function color(palette_name, role) -> str
```

## 9.5 `render/vedo_renderer.py`

The only module that imports vedo.

```
class TwoViewRenderer:
    constructor (window_size, offscreen, n_views, palette_name, title):
        self.plotter = vedo.Plotter(N = n_views, size = window_size,
            offscreen = offscreen, sharecam = False, title = title)
        set each renderer's background to color(palette, "background")
        self.static_actors  = {}      # (view index, id) -> actor
        self.dynamic_actors = {view index: list}
        self.shown = False
    method realize(scenes: list of ViewScene, palette_name,
                   strip: Strip | None):
        # Dynamic actors are KEPT between frames in a pool per view,
        #   keyed by what would need a rebuild (kind, role, label,
        #   width, style, radius, and an ordinal among equals), and
        #   only placed each frame: an arrow is a unit arrow under a
        #   matrix of rotation, scale, and translation; a glyph and a
        #   label are moved; a trail's points are reassigned into a
        #   line of fixed capacity, the tail collapsed onto the last
        #   point, and rebuilt only when it outgrows the capacity; a
        #   surface takes its rotation as its matrix; a text block
        #   takes new text. Keys no longer wanted are removed. This is
        #   what took a frame from ~90 ms of actors to a few.
        # the strip's images are placed side by side under the flat
        #   camera, a cursor line drawn over each at its fraction of
        #   PLOT_BOX (9.6), and the budget lines as 2D text between
        for index, scene in enumerate(scenes):
            if the static list changed (a new run, or a toggle):
                remove the old static actors of this view; build and
                add one actor per drawable (9.6)
            remove this view's dynamic actors; build and add the new
        if not self.shown: self.plotter.show(interactive = False,
                                            resetcam = True); shown
        self.plotter.render()
    method set_camera(view_index, camera, target):
        # azimuth, elevation, distance about `target`, in the view's
        #   axes; vedo's camera positioned from spherical coordinates
    method add_slider(callback, n_samples):  makes the widget, keeps it
    method set_slider(value):  moves the kept widget; no-op without one
    method on_key(handler):   plotter.add_callback("KeyPress", ...)
    method on_tick(handler, milliseconds):
        # vedo's timer delivers an event; the adapter counts ticks
        #   from zero and calls handler(tick).
        plotter.add_callback("timer", ...); plotter.timer_callback(...)
    method interactive():      plotter.interactive()      # blocks
    last_seconds: {"actors": s, "render": s} of the last realize, for
                               the session's frame note (10.4)
    method stop():             plotter.break_interaction()  # from a
                               #   tick, when the controls want to stop
    method screenshot(path = None, as_array = False)
    method close()
```

Three facts learned when this was coded, which the code follows:

- The window holds THREE sub-renderers from the start, two views and
  the panel strip, each a viewport that `realize` places and turns
  on or off from the number of scenes and whether panel images were
  given (`set_layout`). A change of view or of the panel switch is
  then a change of viewports, never a new window, and the kept
  static actors and cameras survive it.
- vedo binds `Ctrl+w` (this tool's save) and `Ctrl+q` to closing the
  window in its own key table, so the renderer turns vedo's default
  keyboard callbacks off before the window is made. Plain keys then
  do nothing but `q`, which is this tool's own quit; the mouse keeps
  vedo's camera interaction, which is the interactor style and not a
  callback.
- Offscreen there is no interactor: `add_slider`, `on_key`, and
  `on_tick` are no-ops, and the scripted loop of 10.4 drives the
  session instead.

```

function build_actor(drawable, palette_name) -> vedo object:
    Polyline -> vedo.Line (dashed/dotted: vedo.DashedLine, or a line
                of short segments) with .c(color) .lw(width); label ->
                vedo.Text3D or a caption at the last point
    Arrow    -> vedo.Arrow(base, tip) .c(color); label at the tip
    Glyph    -> vedo.Sphere(center, r) .c(color); label
    Triad    -> three vedo.Arrow from origin, labels at the tips
    Surface  -> vedo.Mesh([points, faces]) .c(color) .alpha(0.6) plus its
                markings as Lines
    Text     -> vedo.Text2D(joined lines, pos = corner) .c(color)
    Image    -> vedo.Image(rgb) placed at rect (as the scattering
                renderer places its panels); in practice the strip's
                images arrive through `Strip`, not as drawables
```

## 9.6 `render/panels.py`

```
PANEL_NAMES = ("terms", "budget", "conservation")
PLOT_BOX = (left, bottom, right, top) as figure fractions: where the
    axes sit in every plotted panel, so that the renderer can place a
    cursor over the image without matplotlib

function panel_terms(store, i, palette) -> Figure:
    |terms[i, :, j]| for j in TERM_NAMES and |true_force[i, :]| against
    times; log axis when max/min > 100; the x axis exactly the
    particle's valid times, no margin
function panel_budget(budget: ErrorBudget, palette) -> Figure:
    the lines of budget_lines(budget), as text
function panel_conservation(conserved, palette) -> Figure:
    the drifts against time, or the note sentence
function render_panel(name, store, i, palette, budget = None,
                      size = (400, 300)) -> rgb (h, w, 3):
    FigureCanvasAgg, colors from the palette, background from
    "background"; returns the buffer as uint8
function cursor_fraction(store, i, k) -> float | None:
    (time_at(i, k) − t_0) / (t_last − t_0) over the particle's OWN
    times (time_at over its valid samples: the grid, with the stop's
    event time last), clipped to [0, 1]; None with fewer than two;
    the plotted panels use the same times for their x axis, so that
    the axis ends where the data does
function budget_lines(budget) -> list of str:
    the three columns of Design 6.4 as text lines (the numerical
    column on two, the values at k then the maxima), an empty column
    reading "none" (the window font has no em dash)
```

The plotted images depend on the run, the tracked particle, and the
palette only, and matplotlib is slow (hundreds of milliseconds a
panel), so the session keeps them (10.4) and the cursor is a line
the renderer draws over the image at `cursor_fraction`; the budget,
which changes with every sample, is text the renderer draws in the
strip and never an image. `Strip` (9.3) carries the two.

## 9.7 Verification

`test_geometry.py`: the moving triad's columns equal `R(t)` or its
transpose; the Earth triads are the local axes; the stage's turning
parts move by `θ_k` in the view where they turn and not in the
other; the floor turns the other way in the rotating view; trails
stop at the mask; `extra_trails` are absent when the store lacks the
array.

`test_scene_description.py`, without a renderer, on every packaged
run at `k ∈ {0, N/2, last}`:

- the inertial view has exactly the `true` and `velocity` arrows at
  the tracked particle and no arrow with a pseudo-force role; the
  rotating view has six when all are shown, and the set follows the
  session's `arrows`;
- every `Arrow` has a label; every extra `Polyline` has a label and
  a non-solid style (the overlay thin solid);
- `tip − base` equals the stored vector times the stated scale; in
  `auto` mode the largest of each group at `k = 0` is `E/4`; the
  turntable example reports `arrow_ratio None`, the Earth example a
  ratio equal to what the store implies; `same` mode gives `None`
  everywhere; in each view, over every sample of every packaged run,
  no velocity arrow is longer than `E/4` and the longest is `E/4`
  (the drop's rotating arrow starts at nothing);
- `camera_target` is `R(t_k) r̃_P` with `follow` and the initial
  point with `fixed`; `describe` returns one `ViewScene` for a single
  view and two for `both`;
- the readouts contain the scale note, the exaggeration line when
  `α ≠ 1`, the approximation note on the Earth and not on the
  turntable, and the tracked launch's speed as given.

`test_palettes.py`: every palette has every role; the colorblind
palette's six arrow colors are pairwise distinguishable under the
two common deficiencies (a fixed table of simulated colors, checked
once, as the scattering tool does).

`test_panels.py`: each panel renders to an array of the requested
size for every packaged run at `k = 0` and the last sample, with no
exception, and a budget with an empty column renders.

`tests/integration/test_renderer.py` (skips without an offscreen
context, the inherited fixture): `TwoViewRenderer(offscreen = True,
n_views = 2)` realizes the turntable example at three samples and the
screenshot's pixels are non-blank and change between samples;
`n_views = 1` for each single view; `--frames 3 --screenshot` through
the command (Pseudocode 10) writes a non-blank file; `--check` passes.
