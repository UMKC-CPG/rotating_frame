# Pseudocode 8: The Run File and the Results Store

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 8. Governs
> `src/rotating_frame/run/schema.py`, `run/rc.py`, `run/run_spec.py`,
> `run/serialization.py`, `run/results_store.py`, `run/driver.py`,
> and the tests `tests/unit/test_schema.py`, `test_rc.py`,
> `test_serialization.py`, `test_results_store.py`,
> `test_architecture.py`, and `tests/integration/test_run_files.py`,
> `test_determinism.py`, `test_ring_symmetry.py`. *Status: draft.*

**Replaces the skeleton's placeholder** `run/run_file.py` (index row
0): its `SCHEMA` table idea and `load_run_file` survive in shape,
generalized to typed, dimensioned keys. `run/` imports everything
below it (A5) and is imported only by `cli/` and `ui/`. The core
works in natural units with `Ω̃ = 1`, so the `Frame` built here has
`rate = 1.0`; the presets' SI arithmetic (Pseudocode 2.4) happens
before scaling.

---

## 8.1 `run/schema.py`

```
SCHEMA_VERSION = 1

frozen record Key:
    table, name
    kind        "number" | "int" | "bool" | "string" | "choice" |
                "quantity" | "vector" | "table" | "string_list"
    dimension   for quantity/vector: a KINDS entry of Pseudocode 2.1
    default     a value, REQUIRED, PRESET (filled from the preset), or
                OPTIONAL (absent is allowed and means None)
    bare        bool: a bare number is accepted for a quantity, in
                natural units (Design 8.1)
    choices     for "choice": the allowed strings

SCHEMA = [  # every key of Design 8.1, one Key each; the tables:
  frame:  preset (choice: turntable | merry_go_round | earth, REQUIRED),
          rate (quantity rate, PRESET, bare), latitude (quantity angle,
          OPTIONAL, bare), length_scale (quantity length, PRESET, bare),
          exaggeration (number, 1.0)
  force:  kind (choice none | uniform, PRESET), fixed_in (choice
          space | frame, PRESET), magnitude (quantity acceleration,
          PRESET, bare)
  launch: (an array of tables) position (vector length, [0,0,0], bare),
          velocity (vector speed, OPTIONAL, bare), speed (quantity speed,
          OPTIONAL, bare), azimuth (quantity angle, 0, bare), elevation
          (quantity angle, 0, bare), frame (choice rotating | inertial,
          "rotating"), mass (quantity mass, OPTIONAL, bare),
          label (string, "")
  ring:   count (int, REQUIRED within the table), radius (quantity
          length, REQUIRED, bare), target (vector length, [0,0,0], bare),
          speed (quantity speed, REQUIRED, bare), sense (choice inward |
          outward, "inward"), phase (quantity angle, 0, bare),
          height (quantity length, 0, bare)
  run:    duration (quantity time, REQUIRED, bare), stop (choice
          duration | lands | leaves, PRESET), samples (int, 1000),
          method (choice auto | closed_form | numerical, "auto")
  check:  enabled (bool, true), integrator (choice euler | rk4 | dop853,
          "rk4"), substeps (int, 4), rtol (number, 1e-10), atol (number,
          1e-12)
  view:   palette (choice light | dark | colorblind, "light"), views
          (choice both | inertial | rotating, "both"), arrows
          (string_list of the six names, all), ghost (bool, true),
          check_path (bool, false), overlay (choice auto | on | off,
          "auto"), triads (bool, true), stage (bool, true), panels
          (bool, true), legend (bool, true), arrow_scale (choice auto |
          same, "auto"), tracked (int, 0), camera (table: azimuth_deg,
          elevation_deg, distance numbers; follow bool true)
]

class RunFileError(Exception):   # one line a student can act on

function validate_raw(data) -> None:
    # data: the parsed TOML after overrides. Raises RunFileError for:
    #   schema != SCHEMA_VERSION; an unknown table or key; a value of
    #   the wrong kind (a string where a bool was expected, a bare
    #   number where bare is false, a vector not of length 3); a
    #   choice outside its list; [launch] not an array of tables;
    #   both velocity and speed in one launch; elevation without
    #   speed; samples < 2, substeps < 1, exaggeration <= 0, count < 1,
    #   tracked < 0; latitude present for a platform preset or absent
    #   for the Earth; |latitude| >= 89.9 deg (Pseudocode 2.4).
    # The message names the key as "table.key" (or "launch[i].key").

function apply_overrides(data, overrides) -> data:
    # "table.key=value" with the value parsed as TOML, as the
    #   skeleton's run_file.py did; a bad form or value raises
    #   RunFileError naming the override.
```

## 8.2 `run/rc.py`

```
RC_FILENAME = "rfsimrc.py"
BUILTIN_RC = {"window_size": [1280, 800], "default_palette": "light",
              "arrow_scale": 1.0, "glyph_radius": 0.02, "trail_width": 2,
              "max_store_bytes": 500_000_000, "output_dir": "."}

frozen record RcSettings: one field per key above

function load_rc(search_path = None) -> RcSettings:
    values = support.load_rc_defaults(RC_FILENAME, BUILTIN_RC,
                                      search_path)      # inherited
    unknown = keys of values not in BUILTIN_RC
    if unknown: print one line on stderr naming them; drop them
    return RcSettings(**{**BUILTIN_RC, **values})
```

## 8.3 `run/run_spec.py`

```
frozen record ViewSettings:      # the [view] table, resolved
    palette, views, arrows (frozenset), ghost, check_path, overlay,
    triads, stage, panels, legend, arrow_scale, tracked,
    camera (azimuth_deg, elevation_deg, distance, follow)

frozen record RunSpec:
    preset          Preset                       (Pseudocode 2.3)
    frame           Frame(preset.axis, 1.0)      (Pseudocode 1)
    scales          Scales                       (Pseudocode 2.1)
    latitude        radians or None
    axes            LocalAxes, natural units     (Pseudocode 7.1)
    field           ForceField                   (Pseudocode 3)
    launches        list of ResolvedLaunch       (Pseudocode 7.1)
    ring            RingSpec or None
    duration        t̃_end
    stop            "duration" | "lands" | "leaves"
    samples         N
    method          "auto" | "closed_form" | "numerical"
    check           CheckSettings                (Pseudocode 6.1)
    view            ViewSettings
    exaggeration    α
    overlay_note    None, or the sentence saying why the overlay is
                    off when overlay = "on" was asked (Design 8.2)
    words           the run file's data after overrides and preset
                    fill, in the student's units, for write-back
    version         rotating_frame.__version__
```

## 8.4 `run/serialization.py`

```
function load_run_file(path, overrides = (), rc = None) -> RunSpec:
    text = read path                            # OSError -> RunFileError
    data = tomllib.loads(text)                  # TOMLDecodeError -> "
    data = apply_overrides(data, overrides)
    return resolve(data, rc)

function resolve(data, rc) -> RunSpec:
    # Everything below; separate so that a run control (Pseudocode
    #   10.4) can resolve edited words without a file.
    validate_raw(data)                                        # 8.1
    preset = presets.preset(data.frame.preset)
    fill every PRESET default from the preset (rate, length_scale,
        force.kind, force.fixed_in, force.magnitude, run.stop)
    # Units: every quantity key becomes an SI float through
    #   units.parse (strings) or is taken as natural (bare, later
    #   multiplied by the factor); Pseudocode 2.2.
    latitude_si  = parse or None
    rate_si      = parse(frame.rate);  length_si = parse(frame.length_scale)
    mass_si      = per launch, parse or None
    scales       = make_scales(rate_si, length_si, None, exaggeration)
    frame        = Frame(preset.axis, 1.0)
    axes_si      = presets.local_axes_si(preset, latitude, scales.rate)
    launch_point = presets.launch_point_si(preset, latitude) / scales.length
    axes         = LocalAxes(*axes_si, launch_point)
    # The field, in natural units:
    if force.kind == "none": field = make_field("none", ...)
    else:
        g_si     = force.magnitude (SI)
        g_vector = presets.gravity_vector_si(preset, latitude) scaled to
                   magnitude g_si, then / scales.acceleration
        approximation = None if fixed_in == "space" else Approximation(
            note = the text of Pseudocode 3.2,
            timescale = sqrt(preset.radius_si / g_si) / scales.time)
        field = make_field("uniform", fixed_in, g_vector, frame,
                           approximation)
    # Launches, in natural units, then resolved:
    specs = [LaunchSpec(position / L, velocity / (ΩL) or None,
                        speed / (ΩL) or None, azimuth, elevation, frame,
                        mass_si, label) for each [[launch]]]
    if data has [ring]: specs += expand_ring(RingSpec(... / L, / ΩL ...))
    if not specs: raise RunFileError("no launch and no ring")
    stage_rule = data.run.stop
    if stage_rule not in preset.stop_rules:
        raise RunFileError(f"run.stop: {stage_rule!r} is not a rule the "
                           f"{preset.name} stage has; one of "
                           f"{preset.stop_rules}")
    for spec in specs: check_launch(spec, ..., axes, stage_rule)     # 7.3
    launches = [resolve_launch(spec, axes, frame) for spec in specs]
    if view.tracked >= len(launches): raise RunFileError("view.tracked")
    duration = parse(run.duration) / scales.time
    overlay_note = (the sentence of Design 6.5 if view.overlay == "on"
                    and not overlay_applies(frame, duration) else None)
    return RunSpec(...)

function write_resolved(spec, path, view = None) -> None:
    # The resolved run file (Design 8.4): spec.words with every
    #   default filled, PRESET values written out in SI strings in the
    #   preset's display units, launches from the ResolvedLaunch specs
    #   (so a run control's change is written), the [view] table from
    #   `view` when given (the session's current ViewSettings), and a
    #   comment header: the tool's version, Ω, L, T, α, and m.
    # Written with tomli_w after the header comment; the header is
    #   prepended as text because TOML writers do not write comments.
    # An OSError is one line on stderr and returns (contract C16).
```

## 8.5 `run/results_store.py`

```
BYTES_PER_SAMPLE = 40 * 8                      # Design 8.5

function estimate_bytes(n_particles, samples) -> int:
    return n_particles * samples * BYTES_PER_SAMPLE

frozen record StopRecord: index, time, kind ("lands" | "leaves")

class ResultsStore:
    # Every array is created writeable, filled once by the driver,
    #   then flagged read-only (numpy `flags.writeable = False`), which
    #   is the mechanical half of the determinism guarantee.
    times            (N,)         the uniform grid
    positions_in, velocities_in, positions_rot, velocities_rot
                     (N_p, N, 3)  NaN past a particle's stop
    terms            (N_p, N, 3, 3)  TERM_NAMES order
    true_force       (N_p, N, 3)  f̃_rot
    ghost            (N_p, N, 3)
    check_positions, check_velocities   (N_p, N, 3) or None
    comparison       list of Comparison per particle, or None
    conserved        list of Conserved per particle
    overlay          (N_p, N, 3) or None
    stops            list of StopRecord or None per particle
    mask             (N_p, N) bool: sample valid
    spec             RunSpec

    # A particle that stopped has its event state at sample index
    #   stops[i].index and its own time there, stops[i].time; the grid
    #   time at that index is not the sample's time. time_at says so.

    method n_particles, n_samples
    method sample_times() -> times
    method time_at(i, k) -> times[k], or stops[i].time when k is the
                            event sample
    method state_at(i, k) -> (positions_in[i,k], velocities_in[i,k],
                              positions_rot[i,k], velocities_rot[i,k])
    method terms_at(i, k) -> (terms[i,k], true_force[i,k])
    method error_at(i, k) -> (comparison[i].delta[k], .eta[k]) or None
    method conserved_at(i, k) -> the drifts at k and the notes
    method stop_of(i) -> StopRecord or None
    method size_bytes() -> sum of nbytes
```

## 8.6 `run/driver.py`

```
function build_store(spec, rc, progress = None) -> ResultsStore:  # (8.6)
    n_p = len(spec.launches); N = spec.samples
    if estimate_bytes(n_p, N) > rc.max_store_bytes:
        raise RunFileError(f"this run needs about {estimate:.0f} MB of "
                           f"memory; the rc cap is {cap:.0f} MB")
    times = linspace(0, spec.duration, N)
    rule = make_rule(spec.stop, spec.axes.launch_point, spec.axes.up,
                     spec.frame.axis)                       # Pseudocode 4.4
    allocate every array, NaN-filled, mask False
    for i, launch in enumerate(spec.launches):
        trajectory = provide((launch.position_in, launch.velocity_in),
            spec.field, spec.frame, spec.duration, N, rule, spec.method,
            spec.check.integrator, spec.check.substeps, spec.check.rtol,
            spec.check.atol)                                # Pseudocode 4.5
        M = len(trajectory.times); mask[i, :M] = True
        positions_in[i, :M], velocities_in[i, :M] = trajectory arrays
        positions_rot[i, :M], velocities_rot[i, :M] = spec.frame.to_rotating(
            trajectory.times, ...)                          # Pseudocode 1.4
        terms[i, :M] = pseudoforces.stacked(spec.frame, trajectory.times,
            positions_rot[i, :M], velocities_rot[i, :M])    # Pseudocode 5.1
        true_force[i, :M] = spec.field.acceleration_rotating(spec.frame,
            trajectory.times, positions_rot[i, :M], velocities_rot[i, :M])
        ghost[i, :M] = ghost_path(spec.field, spec.frame, launch state,
            spec.axes.launch_point, trajectory.times, spec.check)   # 6.2
        if spec.check.enabled:
            check_positions[i, :M], check_velocities[i, :M] = run_check(
                spec.field, spec.frame, launch state, trajectory.times,
                spec.check)                                 # 6.1
            comparison[i] = compare(...)                    # 6.1
        conserved[i] = monitor(spec.field, spec.frame, launch state,
                               inertial, rotating, check or None)   # 6.3
        if overlay applies (view.overlay != "off" and
                overlay_applies(spec.frame, spec.duration)):
            overlay[i, :M] = first_order_deflection(spec.frame,
                launch.velocity_rot, f̃_rot at launch, trajectory.times) # 6.4
        stops[i] = StopRecord(...) from trajectory.stop, or None
        if progress: progress(i, n_p)
    flag every array read-only
    return ResultsStore(...)
```

`trajectory.times` carries the event time as its last entry when the
particle stopped, so every per-sample quantity above is evaluated
at the event exactly (Design 4.5), and `time_at` reports it.

## 8.7 Verification

`test_schema.py`: every refusal of 8.1, one minimal run file each,
raises `RunFileError` whose message names the key; the shipped
examples pass `validate_raw`; `apply_overrides` sets a nested key
and refuses a bad form.

`test_rc.py`: `load_rc` with no file gives `BUILTIN_RC`; the
inherited search order (working directory, `$ROTATING_FRAME_RC`, the
package) through `support.load_rc_defaults`; an unknown key is
dropped with a note.

`test_serialization.py`:

- A run written in SI and the same run written in natural units
  (bare numbers) resolve to `RunSpec`s whose numeric fields agree to
  `1e-12`; `write_resolved` then `load_run_file` gives an equal spec
  (field by field, arrays with `allclose`).
- The Earth example resolves to `frame.rate == 1.0`, `scales.rate ==
  α Ω_sidereal`, a frame-fixed field with `|g̃| == g₀ / (Ω² L)`, and an
  `Approximation` whose `timescale × scales.time == 805.5 s`.
- `run.stop = "leaves"` on the Earth is refused naming the key and
  the preset's rules; a run with neither launch nor ring is refused;
  `view.tracked` past the last particle is refused; `overlay = "on"`
  on the turntable gives an `overlay_note`, not an error.
- `write_resolved` into a read-only directory prints one line and
  raises nothing.

`test_results_store.py`: shapes of 8.5 for a two-particle run with
one stop; the mask false past the stop and true before; `time_at` at
the event sample returns the event time; every array is read-only
(assigning raises); `estimate_bytes` is within `10 %` of
`size_bytes` for the shipped examples; sample `0` of every particle
equals its `ResolvedLaunch` state.

`test_architecture.py` (A8.6(1), (2), (3)), by AST over
`src/rotating_frame/`: nothing under `render/`, `ui/`, or `geometry/`
imports `rotating_frame.motion`; nothing under `core/`, `forces/`,
`launch/`, `motion/`, `pseudoforces/`, `analysis/`, or `geometry/`
imports `render`, `ui`, or `run`; `pseudoforces/` imports only
`core`; only `core/units.py` imports pint.

`tests/integration/test_run_files.py`: every packaged example
loads, builds, writes back, and reloads to an equal spec; the build
of each takes under two seconds on the reference machine (noted, not
asserted).

`test_determinism.py` (A8.6(4)): two builds of one file give
stores whose every array is equal bit for bit (`array_equal` with
`equal_nan`); a checksum of all arrays before and after reading every
`*_at` accessor for every `(i, k)` in a scrambled order is unchanged.

`test_ring_symmetry.py` (Design 7.5, A8.2): the turntable example's
ring, target at the center: `positions_rot[i]` equals `rodrigues(ẑ,
2π i / N_p) @ positions_rot[0]` sample by sample to `1e-12`, and
every member's stop index and time agree to `1e-12`.
