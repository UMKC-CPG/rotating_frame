# Design 8: The Run File and the Results Store

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.7 (`run/`), 6.4 (the
> results-store boundary), and 7 (configuration); serves G6 (any
> run from a file), G5 (precompute, then view), and P11. Uses
> Designs 1 to 7. *Status: draft.*

A run file is the complete, self-contained description of one run,
in the student's words and units. This section fixes its tables and
keys, what the schema validates, how the rc file, the run file, and
the command line combine, how a run is resolved to natural units
and written back, what the results store holds and offers, and the
one place that knows the order of the stages.

---

## 8.1 The run file

TOML, beginning `schema = 1`, with these tables. Every dimensioned
key takes a string with units (`"33.3 rpm"`, `"39 deg"`, `"2 m/s"`)
or a bare number in the run's natural units where the schema allows
one (Design 2.5); a preset fills whatever is omitted.

```
[frame]
preset        = "earth"          # "turntable" | "merry_go_round" | "earth"
rate          = "7.2921150e-5 rad/s"   # default: the preset's
latitude      = "39 deg"         # earth only; required there
length_scale  = "100 m"          # L; default: the preset's
exaggeration  = 1.0              # alpha (Design 2.6)

[force]
kind          = "uniform"        # "none" | "uniform"; default: preset's
fixed_in      = "frame"          # "space" | "frame"; default: preset's
magnitude     = "9.820 m/s^2"    # default: the preset's g0 or g

[[launch]]                       # one table per particle, or a ring
position      = ["0 m", "0 m", "100 m"]   # local E, N, U (Design 7.2)
velocity      = ["0 m/s", "0 m/s", "0 m/s"]
# or:  speed = "20 m/s", azimuth = "90 deg", elevation = "30 deg"
frame         = "rotating"       # or "inertial"
label         = "stone"          # optional, for the readouts

[ring]                           # optional; expands to launches (7.3)
count = 12
radius = "0.25 m"
speed = "0.30 m/s"
sense = "inward"

[run]
duration      = "10 s"
stop          = "lands"          # "duration" | "lands" | "leaves"
samples       = 1000             # N
method        = "auto"           # "auto" | "closed_form" | "numerical"

[check]
enabled       = true
integrator    = "rk4"            # "euler" | "rk4" | "dop853"
substeps      = 4                # per sample, fixed-step schemes
rtol          = 1e-10            # dop853
atol          = 1e-12

[view]
palette       = "light"
views         = "both"           # "both" | "inertial" | "rotating"
arrows        = ["true", "centrifugal", "coriolis", "euler", "sum",
                 "velocity"]
ghost         = true             # the no-pseudo-force path (6.2)
overlay       = "auto"           # first-order deflection: "auto" |
                                 #   "on" | "off" (6.5)
tracked       = 0                # particle index for the readouts
camera        = { azimuth_deg = 35, elevation_deg = 25, distance = 3 }
```

**Which keys may be bare numbers.** `exaggeration`, `count`,
`samples`, `substeps`, `rtol`, `atol`, `tracked`, and the `[view]`
keys are dimensionless by nature. `rate`, `latitude`, `length_scale`,
`magnitude`, `position`, `velocity`, `speed`, `azimuth`, `elevation`,
`radius`, and `duration` are dimensioned; given bare, they are taken
in natural units (`L`, `1/Ω`, `Ω L`, radians), and the write-back
says so. A preset's own values are always in SI.

**Two shipped examples**, both complete after the preset fills
in: `turntable.toml`, a puck pushed from the rim toward the center
with a twelve-member inward ring; and `earth_drop.toml`, the stone
above, at `39°` (the group's latitude), which lands `1.5 cm` east.
The others of G4 (`merry_go_round.toml`, `earth_throw.toml`,
`earth_vertical.toml`) follow the same shape.

## 8.2 The schema and what it refuses

`run/schema.py` is one table: for every key, its table, its type
(dimensionless number, dimensioned string, choice, list, boolean),
the dimension it must have, its default or `REQUIRED` or `PRESET`
(filled from the preset), and whether a bare number is allowed. A
run file is refused, with a message naming the key, for:

- an unknown table or key, or `schema` other than `1`;
- a wrong type, or a dimensioned string of the wrong dimension;
- a choice outside the list;
- `latitude` missing on the Earth, `latitude` given on a platform;
- both `velocity` and `speed` on one launch, or an `elevation`
  without a `speed`;
- the physical refusals of Design 7.4 and, from Design 4.5, a
  `stop` the stage has no rule for (`"leaves"` on the Earth,
  `"lands"` on the turntable);
- `samples < 2`, `substeps < 1`, `duration ≤ 0`, `exaggeration ≤ 0`,
  `count < 1`;
- an `overlay = "on"` where `Ω̃ t̃_end ≥ 0.1` (Design 6.5) is not
  refused but is answered on screen with the reason it is off.

The message is the whole of the error, one line, and the command
exits with status 2 (the inherited `cli/support.py` idiom).

## 8.3 Precedence

```
  rc file defaults  <  run file  <  --set TABLE.KEY=VALUE
```

The rc file (`rfsimrc.py`, found as the suite's contract says) holds
only what is machine-local and never affects a computed result:

```
  window_size       [1280, 800]
  default_palette   "light"
  arrow_scale       1.0     the drawn length of a unit acceleration,
                            in scene units (Design 9)
  glyph_radius      0.02    as a fraction of L
  trail_width       2
  max_store_bytes   500_000_000
  output_dir        "."
```

Every key that can change a trajectory, an arrow, or the comparison
is in the run file (A7); `--set` overrides a run-file key for one
invocation and the resolved copy records the value used.

**Rejected: physics defaults in the rc file.** A run file that
depended on a machine's rc file would not reproduce elsewhere (G6).

## 8.4 Resolution and write-back

Loading is one pass: parse TOML; apply `--set` overrides; validate
against the schema; fill from the preset; resolve every dimensioned
value to natural units through the boundary (Design 2.5); expand the
ring (Design 7.3); convert each launch to its inertial state (Design
7.2). The result is a `RunSpec`: plain data, every schema key
present, every physical value a dimensionless number, plus the
scale factors `(Ω, L, T, m)` for the way back and the student's
original launch words for the write-back.

`Ctrl+w` in the session (Design 10) and `--write-resolved` on the
command line write the resolved run file: the same TOML with every
default filled in, the preset's values written out in SI, and a
comment block naming the scale factors, the exaggeration, and the
tool's version. Loading it again resolves to an identical `RunSpec`
(8.7), which is what "self-contained" means.

## 8.5 The results store

Built once by the driver, then read only (A6.4). Shapes use `N_p`
particles and `N` samples; the last sample of a particle may be its
stop event (Design 4.5), and samples past a particle's stop hold
`NaN` and a mask.

```
  times        t̃_k                                   (N,)
  inertial     r̃_in, ṽ_in                            (N_p, N, 3) each
  rotating     r̃_rot, ṽ_rot                          (N_p, N, 3) each
  terms        f̃_cf, f̃_co, f̃_eu                     (N_p, N, 3, 3)
  true_force   f̃_rot                                 (N_p, N, 3)
  ghost        ρ̃_ghost                               (N_p, N, 3)
  check        r̃_rot^check, ṽ_rot^check              (N_p, N, 3) each, if on
  comparison   δ̃, ε                                  (N_p, N) each, if on
  conserved    E, J with flags for which apply       (N_p, N, 2)
  overlay      Δ̃ of (6.4)                            (N_p, N, 3), if on
  stops        (index, t̃_stop, kind) per particle
  mask         sample valid                          (N_p, N)
  spec         the RunSpec, and the scale factors
```

The interface the scrubber and the panels use, and the only one:
`state_at(i, k)` returning both descriptions; `terms_at(i, k)`;
`error_at(i, k)`; `conserved_at(i, k)`; `sample_times`; `stop_of(i)`;
`n_particles`, `n_samples`; `size_bytes`. Nothing outside `run/`
touches the arrays directly, so that Design 9 cannot depend on the
layout and a future field cannot break the display.

**Size.** Per particle and sample the store holds about 40 numbers,
`320` bytes; a twelve-member ring at a thousand samples is `4 MB`,
and the rc cap of `500 MB` allows a hundred particles at ten thousand
samples. The estimate is printed before the build and the build is
refused above the cap, as the scattering tool does.

**Rejected: holding the inertial arrays only and transforming on
demand.** The transform is cheap, but the store is the boundary the
display reads (A2.2), and "the display reads arrays and computes
nothing" is a rule worth the doubled memory.

**Rejected: saving the store to disk.** It is regenerable from the
run file in well under a second for every first-version run; nothing
is written but images and the resolved run file (NG6).

## 8.6 The driver

`run/driver.py` is the one place that knows the order of the
stages, and each stage is a call into the module that owns it:

```
  spec      = load_and_resolve(path, overrides, rc)             (8.4)
  launches  = expand_ring(spec) + spec.launches                 (7.3)
  inertial  = provide(launch, field, frame, ...) per particle   (4.1)
  rotating  = transform(frame, times, inertial)                 (1.3)
  terms     = pseudoforces.terms(frame, times, rotating)        (5.1)
  ghost     = ghost_path(spec, frame, field)                    (6.2)
  check     = integrate_rotating(spec, ...) if enabled          (6.1)
  compare   = comparison(rotating, check, ghost)                (6.2)
  conserved = monitor(field, inertial, rotating, check)         (6.3)
  overlay   = first_order(spec) if applicable                   (6.5)
  return ResultsStore(...)                                      (8.5)
```

Progress is reported per particle on standard error for a ring; for
a single launch the whole build is far below a second.

## 8.7 Verification

- Every packaged example loads, resolves, builds, and writes back;
  the written copy loads to a `RunSpec` equal to the original,
  field by field.
- Each refusal of 8.2, one run file per case, is a one-line message
  naming the key and status 2.
- `--set frame.exaggeration=10` doubles nothing but `Ω`, and the
  resolved copy records `10`; `--set` with a bad value is refused
  naming the key.
- The rc precedence, with the inherited rc tests (the suite's).
- The store's arrays have the shapes of 8.5, the mask is false past
  each stop and true before, and sample `0` of every particle is
  the launch's resolved state.
- **Determinism (A8.6(4))**: two builds of one run file are equal
  bit for bit, and reading the store in any order through its
  interface leaves every array unchanged (a checksum before and
  after a scripted session).
- The size estimate is within `10 %` of the built store's
  `nbytes`, and a run above the cap is refused before any array is
  allocated.

## Sources

The run-file discipline (physics in the run file, machine settings
in the rc file, self-contained write-back) follows the scattering
tool's design section 10 and the rigid-body tool's section 12; the
store follows scattering's section 6.
