# Pseudocode 10: The Scrubber and the Session

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 10. Governs
> `src/rotating_frame/ui/session_state.py`, `ui/controls.py`,
> `ui/vedo_controls.py`, `ui/interactive_session.py`, `cli/rfsim.py`,
> and the tests `tests/unit/test_session_state.py`,
> `test_controls.py`, `tests/integration/test_session.py`, and
> `test_rfsim_cli.py`. *Status: reviewed; ratified 2026-09-22.*

`ui/` is new code. `cli/rfsim.py` is a **graft onto the skeleton's
extendable file** (index row 0), and `tests/integration/
test_rfsim_cli.py` replaces the placeholder of the same name; the
seam inventory is 10.6. `ui/` imports `render/`, `run/`, `core/`;
`cli/` imports `ui/`, `run/`, `render/`, and the inherited
`cli/support.py`.

**One addition to Pseudocode 8.4, made here because this section is
its consumer:** `load_run_file` is split into reading and resolving,
`resolve(data, rc) -> RunSpec` taking the parsed and overridden
data, so that a run control can edit the run's words and resolve
them again without a file.

---

## 10.1 `ui/session_state.py`

```
RATES = (1, 2, 4, 8, 16)
VIEWS = ("both", "inertial", "rotating")
ARROW_NAMES = ("true", "centrifugal", "coriolis", "euler", "sum",
               "velocity")
PATH_NAMES = ("check", "ghost", "overlay")
SCENERY_NAMES = ("triads", "stage")

frozen record SessionState:            # Design 10.2, every field
    k, playing, direction, rate, loop, view, arrows (frozenset),
    paths (frozenset), scenery (frozenset), panels, legend, palette,
    tracked, camera_mode, arrow_mode

function initial_state(spec) -> SessionState:
    from spec.view (Pseudocode 8.3): k = 0, playing = False,
    direction = +1, rate = 1, loop = False, view = spec.view.views,
    arrows = spec.view.arrows, paths = the set holding "ghost" when
    spec.view.ghost, "check" when spec.view.check_path, and "overlay"
    when spec.view.overlay != "off",
    scenery from triads and stage, panels, legend, palette, tracked,
    camera_mode = "follow" if camera.follow else "fixed",
    arrow_mode = spec.view.arrow_scale

VIEWING_COMMANDS = ("play_pause", "step_forward", "step_back", "faster",
    "slower", "normal", "reverse", "jump_start", "jump_end", "jump_event",
    "loop", "next_tracked", "toggle_all_arrows", "toggle_arrow_true",
    "toggle_arrow_centrifugal", "toggle_arrow_coriolis",
    "toggle_arrow_euler", "toggle_arrow_sum", "toggle_arrow_velocity",
    "toggle_ghost", "toggle_check", "toggle_overlay", "toggle_triads",
    "toggle_stage", "toggle_camera_mode", "toggle_arrow_mode",
    "toggle_panels", "toggle_legend", "cycle_view", "cycle_palette",
    "reset_camera", "set_sample")
RUN_COMMANDS = ("exaggeration_up", "exaggeration_down", "substeps_up",
    "substeps_down", "speed_up", "speed_down", "azimuth_right",
    "azimuth_left", "elevation_up", "elevation_down")
OTHER_COMMANDS = ("save", "quit")

function transition(state, command, store, argument = None)
        -> SessionState:                                     # pure
    n = store.n_samples
    play_pause:    playing = not playing
    step_forward:  k = min(k + 1, n − 1); playing = False
    step_back:     k = max(k − 1, 0);     playing = False
    faster/slower: rate = next/previous in RATES, saturating
    normal:        rate = 1
    reverse:       direction = −direction
    jump_start/end: k = 0 / n − 1
    jump_event:    k = store.stop_of(tracked).index if any else n − 1
    loop:          loop = not loop
    next_tracked:  tracked = (tracked + 1) mod store.n_particles
    toggle_*:      the named set gains or loses the name; toggle_all_arrows
                   empties the set if full, else fills it
    toggle_camera_mode / toggle_arrow_mode: flip between the two values
    cycle_view / cycle_palette: next in VIEWS / PALETTE_NAMES
    reset_camera:  no state change (the session tells the renderer)
    set_sample:    k = clip(argument, 0, n − 1); playing = False
    a run command, save, or quit: return state unchanged (the session
        handles them, 10.4)

function tick(state, store) -> SessionState:                 # pure
    if not playing: return state
    k = state.k + state.direction * state.rate
    if 0 <= k < n: return state with k
    if state.loop: return state with k = k mod n (wrapping)
    return state with k = clip(k, 0, n − 1), playing = False
```

## 10.2 `ui/controls.py`: the chords

```
KEY_CHORDS = {                       # Design 10.5, both tables
    "Ctrl+space": "play_pause", "Ctrl+s": "step_forward",
    "Ctrl+S": "step_back", "Ctrl+plus": "faster", "Ctrl+equal": "faster",
    "Ctrl+minus": "slower", "Ctrl+underscore": "slower",
    "Ctrl+n": "normal", "Ctrl+r": "reverse", "Ctrl+Home": "jump_start",
    "Ctrl+End": "jump_end", "Ctrl+l": "loop", "Ctrl+Tab": "next_tracked",
    "Ctrl+a": "toggle_all_arrows", "Ctrl+c": "cycle_palette",
    "Ctrl+w": "save", "Ctrl+h": "toggle_legend", "Ctrl+q": "quit",
    "q": "quit",
    "Ctrl+v": "cycle_view", "Ctrl+1": "toggle_arrow_true",
    "Ctrl+2": "toggle_arrow_centrifugal", "Ctrl+3": "toggle_arrow_coriolis",
    "Ctrl+4": "toggle_arrow_euler", "Ctrl+5": "toggle_arrow_sum",
    "Ctrl+6": "toggle_arrow_velocity", "Ctrl+g": "toggle_ghost",
    "Ctrl+k": "toggle_check", "Ctrl+o": "toggle_overlay",
    "Ctrl+t": "toggle_triads", "Ctrl+d": "toggle_stage",
    "Ctrl+f": "toggle_camera_mode", "Ctrl+m": "toggle_arrow_mode",
    "Ctrl+p": "toggle_panels", "Ctrl+e": "jump_event",
    "Ctrl+0": "reset_camera",
    "Ctrl+bracketright": "exaggeration_up",
    "Ctrl+bracketleft": "exaggeration_down",
    "Ctrl+period": "substeps_up", "Ctrl+comma": "substeps_down",
    "Ctrl+Up": "speed_up", "Ctrl+Down": "speed_down",
    "Ctrl+Right": "azimuth_right", "Ctrl+Left": "azimuth_left",
    "Ctrl+Prior": "elevation_up", "Ctrl+Next": "elevation_down"}

LEGEND = [(chord, one-line help) for the chords that carry help, in
          the order of Design 10.5's two tables; aliases carry None]

function command_for(key) -> str | None:
    return KEY_CHORDS.get(key)      # matched case-sensitively, as given

function legend_lines() -> list of str:  "Ctrl+space  play / pause", …
```

Keys arrive from vedo already prefixed; nothing here strips or
lower-cases them (Design 10.5).

## 10.3 `ui/vedo_controls.py`: the two sources

```
abstract class ControlsSource:
    abstract method commands_at(tick) -> list of (command, argument)
    abstract method wants_to_stop() -> bool

class VedoControls(ControlsSource):
    constructor (renderer, n_samples):
        self.queue = []
        renderer.on_key(lambda key: self.queue.append(
            (command_for(key), None)) if command_for(key) else None)
        renderer.add_slider(lambda value: self.queue.append(
            ("set_sample", int(round(value)))), n_samples)
    method commands_at(tick): drain and return the queue
    method wants_to_stop(): a "quit" was queued (a flag, kept after
                            the queue is drained)

class ScriptedControls(ControlsSource):
    constructor (script: list of (tick, command, argument), frames):
    method commands_at(tick): the script's entries at this tick, and
                              remembers that this tick was served
    method wants_to_stop(): the next tick to serve >= frames

function parse_script(text) -> list of (tick, command, argument):
    # "5:play_pause,20:reverse,40:set_sample=7"; an unknown command
    #   or a bad tick is a ValueError naming the entry.
```

## 10.4 `ui/interactive_session.py`: the loop and the run controls

```
TICK_MILLISECONDS = 33                       # thirty ticks a second

class Session:
    constructor (spec, store, rc, controls, renderer):
        self.state = initial_state(spec); self.spec = spec
        self.store = store; self.rc = rc; self.controls = controls
        self.renderer = renderer; self.dirty = True
        # The slider, when there is one, was made by VedoControls and is
        #   kept by the renderer; the session moves it with set_slider.

    method handle(command, argument):
        if command in VIEWING_COMMANDS:
            self.state = transition(self.state, command, self.store,
                                    argument); self.dirty = True
            if command == "reset_camera": self.apply_cameras()
            # cycle_view and toggle_panels need no rebuild: the
            #   renderer lays its viewports out from what realize is
            #   given (9.5)
        elif command in RUN_COMMANDS: self.run_control(command)
        elif command == "save":       self.save()
        # "quit" is read by the loop through wants_to_stop

    method run_control(command):                         # Design 10.1
        words = deep copy of self.spec.words
        if the tracked particle came from a ring:
            expand the ring into explicit [[launch]] tables in `words`
            (the RingSpec's members as bare numbers, which a run file
            reads in natural units: a number sent through SI and back
            is not always the same number in floating point, and the
            untouched members must reproduce bit for bit) and drop
            [ring], so that one member can be edited and written back
        launch = words["launch"][self.state.tracked]
        if command starts with "speed", "azimuth", or "elevation":
            put `launch` in speed form: if it has a velocity, convert
            to speed, azimuth, elevation in the local axes and delete
            the velocity key
        exaggeration_up/down:  words.frame.exaggeration ×= 2 / ÷= 2
        substeps_up/down:      words.check.substeps ×= 2 / max(1, ÷ 2)
        speed_up/down:         launch.speed ×= 2 / ÷= 2
        azimuth_right/left:    launch.azimuth += 15° / −= 15°  (mod 360°)
        elevation_up/down:     launch.elevation ±= 15°, clipped to ±90°
        new_spec  = resolve(words, self.rc)                  # 8.4
        new_store = build_store(new_spec, self.rc)           # 8.6
        self.spec, self.store = new_spec, new_store
        self.state = self.state with k = min(k, n − 1)       # keep the view
        self.dirty = True

    method save():
        path = output_dir / (the run file's stem + "-resolved.toml")
        write_resolved(self.spec, path, view = ViewSettings from
                       self.state)                           # 8.4
        print one line naming the path (or the failure)

    method redraw():
        started = wall clock
        frame_note = "drawing R frames/s (M ms per frame: describe a,
            panels b, actors c, render d)" from the last thirty redraws'
            wall-clock stamps, once there are two; the four parts are
            the last frame's, the first two timed here and the last
            two read from renderer.last_seconds (9.5), so that a slow
            display says where its time goes
        scenes = describe(self.store, self.spec, self.state, self.rc,
                          legend lines when shown, frame_note)
        strip = None
        if state.panels:
            key = (id(self.store), tracked, palette)
            terms, conservation = self.panel_cache[key], rendered on the
                first miss with render_panel (9.6) and kept: matplotlib
                costs hundreds of milliseconds a panel and the images
                change only with the run, the tracked particle, or the
                palette; run_control clears the cache
            cursor = cursor_fraction(self.store, tracked, k)
            strip = Strip([(terms, cursor), (conservation, cursor)],
                          budget_lines(budget of Pseudocode 6.5 at k))
        self.renderer.realize(scenes, self.state.palette, strip)
        self.renderer.set_slider(self.state.k)      # no-op without one
        self.dirty = False; record the wall clock for the frame note

    method on_tick(tick):
        if self.redrawing: return      # a timer event that arrives while
                                       #   a frame is still drawing is
                                       #   dropped, never queued: the keys
                                       #   stay in the controls' queue
        for command, argument in self.controls.commands_at(tick):
            self.handle(command, argument)
        new_state = tick(self.state, self.store)
        if new_state != self.state: self.state = new_state; self.dirty = True
        if self.dirty: self.redraw()
        if self.controls.wants_to_stop(): self.renderer.stop()

    method save() writes next to the run: the constructor takes the
        run file's stem (`run_name`, default "run") for the file name.

function run_session(spec, store, rc, controls, renderer) -> SessionState:
    session = Session(...); session.redraw(); session.apply_cameras()
    if controls is a VedoControls:
        renderer.on_tick(session.on_tick, TICK_MILLISECONDS)
        renderer.interactive()               # returns on quit or close
    else:
        tick = 0
        while not controls.wants_to_stop():
            session.on_tick(tick); tick += 1
    return session.state
```

Pacing is by ticks (Design 10.3): `tick` advances `rate` samples,
whatever the wall clock does.

## 10.5 `cli/rfsim.py`

```
COMMAND_NAME = "rfsim"; RC_FILENAME = "rfsimrc.py"
CHECKED_DISTRIBUTIONS = ("numpy", "scipy", "matplotlib", "vedo", "vtk",
                         "pint", "tomli_w")   # == pyproject deps minus
                                              #   the 3.10 backport

function parse_command_line(argv):
    runfile (optional); --set TABLE.KEY=VALUE (repeatable); --offscreen;
    --frames N; --script "tick:command,..."; --screenshot PATH;
    --palette {light, dark, colorblind}; --view {both, inertial,
    rotating}; --write-resolved PATH; --examples [DIR]; --write-rc;
    --check
    exactly one of {runfile, --examples, --write-rc, --check}
    --offscreen needs --frames or --script

function run_offscreen(run_file_path, frames) -> image:   # for --check
    rc = load_rc(); spec = load_run_file(run_file_path, (), rc)
    store = build_store(spec, rc)
    from render.vedo_renderer import TwoViewRenderer      # after
                                                          #   prepare_offscreen
    renderer = TwoViewRenderer((640, 480), offscreen = True, n_views = 2,
                               spec.view.palette, COMMAND_NAME)
    run_session(spec, store, rc, ScriptedControls([], frames), renderer)
    image = renderer.screenshot(as_array = True); renderer.close()
    return image

function main(argv = None) -> int:
    utilities as the skeleton has them (examples, write-rc, check)
    try:
        path = locate_run_file(args.runfile, COMMAND_NAME)
        rc = load_rc()
        overrides = args.set + view overrides from --palette / --view
        spec = load_run_file(path, overrides, rc)
        print the size estimate on stderr
        store = build_store(spec, rc, progress = a one-line bar for rings)
    except (RunFileError, UnitsError, FileNotFoundError, ValueError) as p:
        print f"{COMMAND_NAME}: {p}" on stderr; return 2
    if args.write_resolved:
        write_resolved(spec, args.write_resolved); return 0
    if args.offscreen: prepare_offscreen()
    from render.vedo_renderer import TwoViewRenderer
    renderer = TwoViewRenderer(rc.window_size, args.offscreen, n_views,
                               spec.view.palette, COMMAND_NAME)
    controls = ScriptedControls(parse_script(args.script), args.frames or
                                last tick + 2) if scripted else
               VedoControls(renderer, store.n_samples)
    run_session(spec, store, rc, controls, renderer)
    if args.screenshot: renderer.screenshot(path) guarded as C16 says
    renderer.close(); return 0
```

## 10.6 Seam inventory for `cli/rfsim.py`

What the skeleton's file holds, and what happens to it:

| In the skeleton's `cli/rfsim.py` | Now | Note |
| --- | --- | --- |
| docstring, the `--help` text | rewritten for this tool | |
| `COMMAND_NAME`, `RC_FILENAME` | unchanged | |
| `CHECKED_DISTRIBUTIONS` | this tool's seven | test keeps it |
| | | equal to pyproject |
| `BUILTIN_RC`, `load_rc_defaults(...)` | `run.rc.load_rc()` | 8.2 |
| `parse_command_line` | the flags of 10.5 | |
| `load_run_file(runfile, overrides)` | `serialization.load_run_file(` | 8.4 |
| | `path, overrides, rc)` | |
| `circular_motion_samples` | gone with `core/motion.py` | |
| `TrailRenderer(...).run(...)` | `TwoViewRenderer` and `run_session` | 9.5, |
| | | 10.4 |
| `run_offscreen` | as 10.5 | |
| `console_main`, `record_command` import | unchanged | inherited |

Consumed unchanged from the inherited `cli/support.py`:
`copy_examples`, `copy_rc_file`, `locate_run_file`, `record_command`,
`self_check`. The placeholder `core/motion.py` and `examples/
circle.toml` are deleted when this section is coded; the examples
of Design 8.1 replace the latter.

## 10.7 Verification

`test_session_state.py` (pure, no window):

- `initial_state` from each packaged spec matches its `[view]` table.
- Every transition of 10.1: play then pause leaves `k`; step forward
  then back returns it; reverse then step moves the other way; `tick`
  at the last sample with `loop` off stops and holds; with `loop` on
  wraps; `rate` saturates at 1 and 16; every toggle is its own
  inverse; `next_tracked` wraps; `jump_event` goes to the stop index
  or the last sample; `set_sample` clips.
- A run command, `save`, or `quit` leaves the state unchanged.

`test_controls.py`: every chord in `KEY_CHORDS` maps to a name in
one of the three command tuples; every non-alias chord appears in
`legend_lines`; no plain key but `q` is bound; `parse_script` parses
the example of 10.3 and refuses an unknown command naming it.

`tests/integration/test_session.py` (a scripted session, offscreen,
skipping without a context):

- A script issuing every viewing command in a scrambled order on
  every packaged run leaves the store's checksum unchanged (Design
  10.7, with Pseudocode 8's determinism test).
- `exaggeration_up` doubles `spec.exaggeration` and `scales.rate`,
  keeps `k` and every switch, and the budget's distortion column
  reads the new factor; `substeps_up` reduces `max_delta` by a factor
  in `[14, 18]` and leaves the exact arrays equal to the old store's;
  `speed_up` on the tracked particle doubles its `spec.speed` and
  leaves every other particle's samples equal; `azimuth_right` on a
  ring member expands the ring in `spec.words` and turns that member
  alone; `elevation_up` saturates at `90°`; after each, `save` writes
  a file that `load_run_file` resolves to the session's spec.
- `cycle_view` changes the number of `ViewScene`s the session
  describes; `toggle_camera_mode` changes the camera target as
  Pseudocode 9.3 says.
- `--script "5:play_pause,20:reverse,40:play_pause"` for 60 ticks
  ends at the `k` the pure `tick` function predicts.

`test_rfsim_cli.py` (replacing the placeholder, keeping its utility
cases from the skeleton):

- the inherited cases: examples, rc copy, read-only directory,
  utility invocations not logged, `--check` passes and writes
  nothing, usage errors;
- `main(["earth_drop", "--offscreen", "--frames", "3", "--screenshot",
  "f.png"])` returns 0 and writes a non-blank image;
  `--write-resolved` writes a file that reloads equal;
  `--set frame.exaggeration=10` shows in the resolved copy; a bad
  run file is status 2 with the key in the message and no traceback.
