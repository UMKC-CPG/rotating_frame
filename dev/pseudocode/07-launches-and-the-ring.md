# Pseudocode 7: Launches and the Ring

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 7. Governs
> `src/rotating_frame/launch/launch_spec.py`, `launch/ring.py`, and
> `tests/unit/test_launch.py`. *Status: draft.*

New code. `launch/` imports `core/` (the `Frame` and the presets'
local axes) and nothing else. Values arriving here are already in
natural units (Pseudocode 8 converts); this module turns the
student's description into the inertial state the motion provider
takes, and expands a ring into launches.

---

## 7.1 `launch/launch_spec.py`

```
frozen record LocalAxes:
    east, north, up     unit vectors, rotating components
    launch_point        r̃_P, rotating components
    # Built by run/ from presets.local_axes_si and launch_point_si
    #   (Pseudocode 2.4), scaled to natural units.

frozen record LaunchSpec:                          # the student's words
    position      (3,) offsets (E, N, U) from the launch point
    velocity      (3,) components (E, N, U), or None
    speed         float or None      # with azimuth and elevation
    azimuth       radians, from north, clockwise seen from above
    elevation     radians, from the horizontal
    frame         "rotating" | "inertial"
    mass          float or None
    label         str

frozen record ResolvedLaunch:
    position_in, velocity_in     the state at t̃ = 0, inertial comps
    position_rot, velocity_rot   the same in rotating components
    spec                         the LaunchSpec it came from

function local_velocity(spec) -> (3,) in (E, N, U) components:
    if spec.velocity is not None: return spec.velocity
    if spec.speed is None:        return zeros(3)
    return spec.speed * (cos(elevation) sin(azimuth),
                         cos(elevation) cos(azimuth),
                         sin(elevation))                        # (7.1)

function resolve_launch(spec, axes, frame) -> ResolvedLaunch:
    basis = column_stack(axes.east, axes.north, axes.up)        # (3, 3)
    position_rot = axes.launch_point + basis @ spec.position
    velocity_local = basis @ local_velocity(spec)
    if spec.frame == "rotating":
        position_in, velocity_in = frame.launch_to_inertial(
            position_rot, velocity_local)                  # Pseudocode 1.4
        velocity_rot = velocity_local
    else:                                          # "inertial"
        position_in, velocity_in = position_rot, velocity_local
        _, velocity_rot = frame.to_rotating(0.0, position_in, velocity_in)
    return ResolvedLaunch(position_in, velocity_in, position_rot,
                          velocity_rot, spec)
```

At `t̃ = 0` the rotating and inertial components of a position
coincide (`R(0) = I`), which is why `position_rot` serves as
`position_in` in both branches; only the velocity differs, by the
rim speed (Design 7.2).

## 7.2 `launch/ring.py`

```
frozen record RingSpec:
    count     N_p ≥ 1
    radius    ρ̃_ring > 0
    target    (3,) local offsets of the common point; default zeros
    speed     ṽ₀ ≥ 0
    sense     "inward" | "outward"
    phase     radians, azimuth of member 0
    height    ρ̃_U of every member

function expand_ring(ring) -> list of LaunchSpec:                # (7.2)
    launches = []
    for i in 0 … ring.count − 1:
        psi = ring.phase + 2π i / ring.count
        offset   = ring.radius * (sin psi, cos psi, 0)  # E, N; azimuth
                                                        #   from north
        position = ring.target + offset + (0, 0, ring.height)
        toward   = -offset / ring.radius                # unit, to target
        if ring.sense == "outward": toward = -toward
        velocity = ring.speed * toward
        launches.append(LaunchSpec(position, velocity, None, 0, 0,
                                   "rotating", None, f"ring {i}"))
    return launches
```

A ring's launches are ordinary `LaunchSpec`s in the rotating frame
with component velocities; after `expand_ring` nothing knows they
were a ring (Design 7.3). `psi` uses the same azimuth convention as
`local_velocity`, so member `0` at `phase = 0` sits north of the
target.

## 7.3 The physical refusals (Design 7.4)

These are checked by the schema layer of Pseudocode 8 with the
values it has just resolved, calling one function here so that the
rules live beside the records they constrain:

```
function check_launch(spec, resolved, axes, stage_rule) -> None:
    # Raises ValueError with the key named; the schema turns it into
    #   the run-file error of Pseudocode 8.
    if spec.velocity is not None and spec.speed is not None:
        raise ValueError("launch: give velocity or speed, not both")
    if spec.elevation is not None and spec.speed is None:
        raise ValueError("launch.elevation: needs launch.speed")
    if not -π/2 <= spec.elevation <= π/2: raise ValueError(...)
    if spec.speed is not None and spec.speed < 0: raise ValueError(...)
    if spec.frame not in ("rotating", "inertial"): raise ValueError(...)
    height = spec.position[2]                            # U offset
    if stage_rule == "lands":
        if height < 0: raise ValueError("launch.position[2]: below the "
                                        "ground")
        if height == 0 and local_velocity(spec)[2] <= 0:
            raise ValueError("launch.position[2]: on the ground with no "
                             "upward velocity")
    if stage_rule == "leaves":
        rho_h = |spec.position[:2]|  # E, N offsets; P is the center
        if rho_h >= 1.0: raise ValueError("launch.position: outside the "
                                          "disc")

function check_ring(ring, stage_rule) -> None:
    count < 1, radius <= 0, speed < 0, sense not in the two, height < 0
        under "lands", or any member outside the disc under "leaves":
        raise ValueError naming the key
```

## 7.4 Verification (`tests/unit/test_launch.py`)

With `frame = Frame(ẑ, 1.0)`, the platforms' axes (identity, launch
point zero) and the Earth's axes at `45°` from Pseudocode 2.4 scaled
by `L = 100 m`, tolerance `1e-14`:

- `local_velocity`: components pass through; `speed` with `azimuth =
  0` gives north, `90°` gives east, `elevation = 90°` gives up; `None`
  everywhere gives zero.
- `resolve_launch` of a rotating launch at rest at offset `ρ` has
  `velocity_in = Ω̃ × (r̃_P + ρ)`; of an inertial launch at rest,
  `velocity_in = 0` and `velocity_rot = −Ω̃ × r̃`; the resolved
  `position_in` equals `position_rot` in both; the `spec` is kept.
- On the Earth's axes, a launch `speed = 1, azimuth = 90°` has
  `velocity_rot · ê_E = 1`, and `position` offsets add along the
  local triad (a `U` offset of `1` puts the point at `r̃_P + ê_U`).
- `expand_ring` with `count = 12, radius = 0.25, speed = 0.3`: twelve
  launches, each `0.25` from the target, azimuths `30° i`, member
  `0` north of the target, every velocity of magnitude `0.3` pointing
  at the target (`inward`) or away (`outward`); with `target` moved,
  everything moves with it; every label is `"ring i"`.
- Expanding a ring and resolving its members gives, for the turntable
  with the target at the center, rotating-frame states that map onto
  one another under rotation by `2π/12` about `ẑ` (the symmetry of
  Design 7.5 at `t̃ = 0`; the whole-run symmetry is Pseudocode 8's
  integration test).
- `check_launch` raises with the key named for each case of 7.3 and
  passes the shipped examples; a launch on the ground with upward
  velocity passes under `"lands"`; `check_ring` raises for each of
  its cases.
