# Pseudocode 2: Natural Units and the Presets

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 2. Governs
> `src/rotating_frame/core/natural_units.py`, `core/units.py`,
> `core/presets.py`, and their tests `tests/unit/test_natural_units.py`,
> `test_units.py`, `test_presets.py`. *Status: draft.*

New code. Three modules with one direction of dependence:
`units.py` (the pint boundary) is imported by `run/` only; `presets.py`
imports `natural_units.py` and `frame.py` (Pseudocode 1);
`natural_units.py` imports NumPy alone. Every quantity a preset
holds is SI; every quantity that leaves `natural_units.py` toward the
core is dimensionless.

---

## 2.1 `core/natural_units.py`: the scales

```
KINDS = ("time", "length", "speed", "acceleration", "angle", "mass",
         "rate")

frozen record Scales:
    rate          Ω in rad/s, AFTER the exaggeration (Design 2.6)
    length        L in m
    mass          m in kg, or None (Design 2.2)
    exaggeration  α, kept for the readouts
    # derived, computed once in the constructor:
    time          T = 1 / rate
    speed         rate * length
    acceleration  rate² * length

function make_scales(rate_si, length_si, mass_si, exaggeration)
        -> Scales:
    if rate_si == 0 or length_si <= 0 or exaggeration <= 0:
        raise ValueError naming which
    return Scales(rate = exaggeration * rate_si, length = length_si,
                  mass = mass_si, exaggeration = exaggeration)

function factor(scales, kind) -> float:
    # The SI value of one natural unit of `kind`.
    time -> scales.time;  length -> scales.length;  speed -> scales.speed
    acceleration -> scales.acceleration;  rate -> scales.rate
    angle -> 1.0;  mass -> scales.mass (ValueError if None)

function to_natural(scales, value_si, kind) -> float or array:
    return value_si / factor(scales, kind)

function to_real(scales, value_natural, kind) -> float or array:
    return value_natural * factor(scales, kind)

function speed_ratio(scales, speed_si) -> float:            # ε, Design 2.3
    return speed_si / scales.speed
```

`to_natural` and `to_real` accept NumPy arrays and broadcast, so a
whole trajectory converts in one call. Nothing here knows what a
run is; `run/` (Pseudocode 8) calls these with the resolved values.

## 2.2 `core/units.py`: the boundary

The only module in the package that imports pint (A6.6; a test of
Pseudocode 8 enforces it).

```
import pint
REGISTRY = pint.UnitRegistry()          # built once, at import

# The SI unit every dimension is reduced to. "rpm" and "deg" parse
#   through pint's own definitions (a revolution is 2π radians).
SI_UNIT = {"length": "meter", "time": "second", "speed": "meter/second",
           "acceleration": "meter/second**2", "angle": "radian",
           "rate": "radian/second", "mass": "kilogram"}

class UnitsError(ValueError):
    key      the run-file key, for the message
    message  one line a student can act on

function parse(text, kind, key) -> float:
    # A dimensioned string from the run file to an SI number.
    try:
        quantity = REGISTRY.Quantity(text)
    except pint's errors as problem:
        raise UnitsError(key, f"{key}: cannot read {text!r} as a "
                              f"{kind} ({problem})")
    try:
        return float(quantity.to(SI_UNIT[kind]).magnitude)
    except pint.DimensionalityError:
        raise UnitsError(key, f"{key}: {text!r} is not a {kind}; "
                              f"expected units like {EXAMPLE[kind]}")
    # EXAMPLE = {"length": "1.2 m", "time": "10 s", "speed": "3 m/s",
    #            "acceleration": "9.8 m/s^2", "angle": "39 deg",
    #            "rate": "33.3 rpm", "mass": "0.2 kg"}

function parse_vector(texts, kind, key) -> array (3,):
    # Three strings, or a mix of strings and bare numbers is NOT
    #   accepted here: the schema (Pseudocode 8) decides bareness and
    #   calls parse on each string.
    return array([parse(t, kind, f"{key}[{i}]") for i, t in enumerate(texts)])

function format_real(value_si, kind, unit) -> str:
    # For the readouts (Design 9.7): an SI number shown in the
    #   preset's display unit, four significant figures, pint's
    #   compact unit symbol: format_real(0.0155, "length", "cm")
    #   -> "1.550 cm".
    quantity = REGISTRY.Quantity(value_si, SI_UNIT[kind]).to(unit)
    return f"{quantity.magnitude:.4g} {quantity.units:~}"
```

`parse` is deliberately strict about dimension: a speed where a
length was asked for is an error with the key named, never a silent
number (Design 2.5).

## 2.3 `core/presets.py`: the three presets

```
# Physical constants (Design 2.4, sources there).
EARTH_ROTATION_RATE = 7.2921150e-5      # rad/s, sidereal
EARTH_GM            = 3.986004e14       # m^3/s^2
EARTH_RADIUS        = 6.371e6           # m
EARTH_ATTRACTION    = EARTH_GM / EARTH_RADIUS**2      # g0 = 9.820 m/s^2
STANDARD_GRAVITY    = 9.81              # m/s^2, the room's

frozen record Preset:
    name              "turntable" | "merry_go_round" | "earth"
    axis              unit vector, rotating components
    rate_si           rad/s
    length_si         L in m
    force_kind        "none" | "uniform"
    force_fixed_in    "space" | "frame" | None
    gravity_si        magnitude, m/s^2, or None
    radius_si         R_E for the Earth, else None
    requires_latitude bool
    stop_rules        the rules the stage offers (Design 4.5):
                      ("duration", "leaves") | ("duration", "lands")
    stage             "disc" | "platform" | "ground"
    display_units     {"length": "m", "time": "s", "speed": "m/s",
                       "acceleration": "m/s^2", "angle": "deg"}
                      (the Earth shows lengths in "m" and, for the
                       readouts of deflections, "cm": Pseudocode 9)

PRESETS = {
  "turntable":      Preset(axis = ẑ, rate_si = 33⅓ rpm in rad/s
                           (= 3.4906585), length_si = 0.30,
                           force_kind = "none", force_fixed_in = None,
                           gravity_si = None, radius_si = None,
                           requires_latitude = False,
                           stop_rules = ("duration", "leaves"),
                           stage = "disc", display_units = ...),
  "merry_go_round": Preset(axis = ẑ, rate_si = 0.50, length_si = 2.0,
                           force_kind = "uniform", force_fixed_in =
                           "space", gravity_si = STANDARD_GRAVITY,
                           radius_si = None, requires_latitude = False,
                           stop_rules = ("duration", "lands"),
                           stage = "platform", ...),
  "earth":          Preset(axis = ẑ, rate_si = EARTH_ROTATION_RATE,
                           length_si = 100.0, force_kind = "uniform",
                           force_fixed_in = "frame",
                           gravity_si = EARTH_ATTRACTION,
                           radius_si = EARTH_RADIUS,
                           requires_latitude = True,
                           stop_rules = ("duration", "lands"),
                           stage = "ground", ...),
}

function preset(name) -> Preset:
    if name not in PRESETS: raise ValueError(
        f"frame.preset: no preset {name!r}; one of "
        f"{', '.join(PRESETS)}")
    return PRESETS[name]
```

## 2.4 The launch point and the local axes (Design 7.1, 3.4.1)

These belong to the preset because the preset owns the launch point;
the plumb-line formula is Design 3.4.1's and is applied here once.

```
function launch_point_si(preset, latitude_rad) -> vector, rotating comps:
    if preset.name == "earth":
        return EARTH_RADIUS * (cos λ, 0, sin λ)
    return zeros(3)                       # on the axis, at the origin

function gravity_vector_si(preset, latitude_rad) -> vector or None:
    # Rotating components at the launch point (Design 3.3, 3.4).
    if preset.force_kind == "none": return None
    if preset.name == "earth":
        return -preset.gravity_si * (cos λ, 0, sin λ)     # toward O
    return (0, 0, -preset.gravity_si)                     # down

function local_axes_si(preset, latitude_rad, rate_si)
        -> (east, north, up), each a unit vector:
    if preset.name != "earth":
        return x̂, ŷ, ẑ
    r_P     = launch_point_si(preset, λ)
    omega   = rate_si * preset.axis
    centrifugal = -cross(omega, cross(omega, r_P))
    g_eff   = gravity_vector_si(preset, λ) + centrifugal
    up      = -g_eff / |g_eff|
    east    = cross(preset.axis, r_P); east = east / |east|
    north   = cross(up, east)
    return east, north, up
    # `rate_si` is the run's rate, after the exaggeration, so that a
    #   faster Earth tilts the plumb line more (Design 2.6).

function plumb_line_tilt(preset, latitude_rad, rate_si) -> radians:
    east, north, up = local_axes_si(preset, λ, rate_si)
    r_hat = launch_point_si(preset, λ) / EARTH_RADIUS
    return arccos(clip(dot(up, r_hat), -1, 1))
```

`local_axes_si` is undefined at the poles (`east` has zero length);
the schema (Pseudocode 8) refuses `|λ| ≥ 89.9°` with a message, so
the function may assume `cos λ > 0`.

## 2.5 Verification

`test_natural_units.py`:

- `make_scales(7.2921150e-5, 100, None, 1)` has `time ≈ 13713 s`,
  `speed ≈ 7.29e-3 m/s`, `acceleration ≈ 5.32e-7 m/s²`, to `1e-12`
  relative; with `exaggeration = 2`, `rate` doubles and `time`
  halves; a zero rate, a non-positive length, or a non-positive
  exaggeration raises naming which.
- `to_real(scales, to_natural(scales, x, kind), kind) == x` to
  `1e-12` relative for every kind, scalars and arrays; `mass` with
  `mass = None` raises.
- `speed_ratio` for the two worked cases of Design 2.3: `0.477` for
  `0.5 m/s` on the turntable preset's scales and `1371` for `10 m/s`
  on the Earth's with `L = 100 m`, to three figures.

`test_units.py`:

- `parse("33.3 rpm", "rate", "frame.rate") ≈ 3.487`; `parse("39 deg",
  "angle", ...) ≈ 0.6807`; `parse("9.820 m/s^2", "acceleration", ...)`;
  `parse("1.2 m", "length", ...)`; `parse("0.2 kg", "mass", ...)`.
- `parse("3 m/s", "length", "launch.position[0]")` raises `UnitsError`
  whose message contains the key and `"is not a length"`;
  `parse("three", "length", ...)` raises with `"cannot read"`.
- `format_real(0.0155, "length", "cm") == "1.55 cm"`, and
  `format_real(1.0, "angle", "deg") == "57.3 deg"`.
- No module under `src/rotating_frame/` other than `core/units.py`
  imports pint (the AST test of Pseudocode 8; listed here because
  this is the rule it protects).

`test_presets.py`:

- `preset("earth").gravity_si == 9.820` to four figures; `preset("x")`
  raises naming the three; every preset has every field and a
  complete `display_units`.
- `launch_point_si("earth", 45°)` has magnitude `EARTH_RADIUS` and
  `z = R_E sin 45°`; the platforms give zero.
- `local_axes_si` is orthonormal and right-handed for every preset
  and for `λ` in `{10°, 45°, 80°}`; on the Earth `east · ŷ > 0` at
  `λ = 45°` (the launch point being in the `x`–`z` plane) and `up`
  is within `0.1°` of `r̂_P`.
- `plumb_line_tilt("earth", 45°, EARTH_ROTATION_RATE) = 0.099°` to
  three figures, and `Ω² R_E` at the equator (`|g_eff| − g₀` at
  `λ = 0`) is `0.0339 m/s²` (Design 2.4).
- With `rate_si` doubled, the tilt at `45°` is four times larger to
  first order (`0.397°`), which is Design 2.6's promise that the
  exaggeration tilts the plumb line.
