"""Loading a run file into a `RunSpec`, and writing the resolved copy
back (pseudocode 8.4; design 8.4).

Loading is one pass: parse the TOML, apply the command-line
overrides, validate against the schema, fill what the preset
supplies, resolve every dimensioned value to the run's natural units
through the boundary, build the frame, the local axes, the field,
and the launches (expanding a ring first), and check what the stage
allows. The result is plain data. `resolve` is separate from the
file reading so that a run control in the session can edit the run's
words and resolve them again without a file.

The resolved copy is the same TOML with every default filled in, the
preset's values written out in SI strings, and a comment header
naming the scale factors, so that loading it again gives an equal
spec: that is what "self-contained" means.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import copy
import sys
from pathlib import Path

import numpy as np
import tomli_w

try:
    import tomllib
except ModuleNotFoundError:                      # Python 3.10
    import tomli as tomllib

import rotating_frame
from rotating_frame.analysis import CheckSettings, overlay_applies
from rotating_frame.core import presets as preset_table
from rotating_frame.core import units
from rotating_frame.core.frame import Frame
from rotating_frame.core.natural_units import factor, make_scales
from rotating_frame.forces import Approximation, make_field
from rotating_frame.forces.fields import UNIFORM_APPROXIMATION_NOTE
from rotating_frame.launch import (LaunchSpec, LocalAxes, RingSpec,
                                   check_launch, check_ring, expand_ring,
                                   resolve_launch)
from rotating_frame.run.rc import load_rc
from rotating_frame.run.run_spec import RunSpec, ViewSettings
from rotating_frame.run.schema import (KEYS, OPTIONAL, PRESET, REQUIRED,
                                       RunFileError, apply_overrides,
                                       check_latitude, validate_raw)

# The sentence shown when overlay = "on" is asked where the frame
# turns too much for the first-order formula (design 6.5, 8.2).
OVERLAY_OFF_NOTE = ('The first-order overlay is off: the frame turns '
                    'more than a tenth of a radian during this run, '
                    'so the formula is not an approximation of it.')


def _get(data, table, name):
    """The value of a key, its default, or None for one that is
    absent and optional; a missing required key is an error."""
    key = KEYS[(table, name)]
    if name in data.get(table, {}):
        return data[table][name]
    if key.default is REQUIRED:
        raise RunFileError(f'{table}.{name}: required')
    if key.default in (OPTIONAL, PRESET):
        return None
    return copy.deepcopy(key.default)


def _quantity(value, kind, label, scales):
    """A run-file quantity to natural units: a string through the
    boundary and the scale factor, a bare number as it is."""
    if value is None:
        return None
    if isinstance(value, str):
        return units.parse(value, kind, label) / factor(scales, kind)
    return float(value)


def _vector(value, kind, label, scales):
    if value is None:
        return None
    if all(isinstance(part, str) for part in value):
        return units.parse_vector(value, kind, label) / factor(scales, kind)
    return np.asarray(value, dtype=float)


def _fill_from_preset(data, the_preset):
    """Write the preset's values into the data where the run file
    left them out, so that the words hold every value used."""
    frame = data.setdefault('frame', {})
    if 'rate' not in frame:
        frame['rate'] = f'{the_preset.rate_si!r} rad/s'
    if 'length_scale' not in frame:
        frame['length_scale'] = f'{the_preset.length_si!r} m'
    force = data.setdefault('force', {})
    force.setdefault('kind', the_preset.force_kind)
    if the_preset.force_kind == 'uniform':
        force.setdefault('fixed_in', the_preset.force_fixed_in)
        if 'magnitude' not in force:
            force['magnitude'] = f'{the_preset.gravity_si!r} m/s^2'
    run = data.setdefault('run', {})
    run.setdefault('stop', the_preset.stop_rules[-1])
    return data


def _fill_defaults(data):
    """Write every plain default into the data, so that the resolved
    copy is complete."""
    for (table, name), key in KEYS.items():
        if table == 'launch':
            for launch in data.get('launch', []):
                if name in ('azimuth', 'elevation') and \
                        'speed' not in launch:
                    continue                # meaningless without a speed
                if name not in launch and key.default not in (
                        REQUIRED, PRESET, OPTIONAL):
                    launch[name] = copy.deepcopy(key.default)
            continue
        if table == 'ring' and 'ring' not in data:
            continue
        if key.default in (REQUIRED, PRESET, OPTIONAL):
            continue
        data.setdefault(table, {}).setdefault(name,
                                              copy.deepcopy(key.default))
    return data


def load_run_file(path, overrides=(), rc=None):
    """Read `path`, apply `overrides`, and resolve (pseudocode 8.4)."""
    path = Path(path)
    try:
        text = path.read_text()
    except OSError as problem:
        raise RunFileError(f'{path}: cannot read ({problem.strerror})') \
            from None
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as problem:
        raise RunFileError(f'{path}: not valid TOML ({problem})') from None
    data = apply_overrides(data, overrides)
    return resolve(data, rc)


def resolve(data, rc=None):
    """A parsed and overridden run file to a `RunSpec`. A units error
    from the boundary is reported as a run-file error, since to the
    student it is one."""
    try:
        return _resolve(data, rc)
    except units.UnitsError as problem:
        raise RunFileError(str(problem)) from None


def _resolve(data, rc):
    if rc is None:
        rc = load_rc()
    validate_raw(data)
    data = copy.deepcopy(data)
    the_preset = preset_table.preset(data['frame']['preset'])
    _fill_from_preset(data, the_preset)
    _fill_defaults(data)
    frame_words = data['frame']

    # The scales come first: everything else is measured in them.
    rate_si = units.parse(frame_words['rate'], 'rate', 'frame.rate')
    length_si = units.parse(frame_words['length_scale'], 'length',
                            'frame.length_scale')
    exaggeration = float(frame_words['exaggeration'])
    scales = make_scales(rate_si, length_si, None, exaggeration)
    latitude = None
    if the_preset.requires_latitude:
        latitude = _quantity(frame_words['latitude'], 'angle',
                             'frame.latitude', scales)
        check_latitude(latitude)

    frame = Frame(the_preset.axis, 1.0)
    east, north, up = preset_table.local_axes_si(the_preset, latitude,
                                                 scales.rate)
    launch_point = (preset_table.launch_point_si(the_preset, latitude)
                    / scales.length)
    axes = LocalAxes(east, north, up, launch_point)

    force_words = data['force']
    if force_words['kind'] == 'none':
        field = make_field('none', None, None, frame)
    else:
        magnitude = _quantity(force_words['magnitude'], 'acceleration',
                              'force.magnitude', scales)
        direction = preset_table.gravity_vector_si(the_preset, latitude)
        if direction is None:                    # a platform asked for
            direction = np.array([0.0, 0.0, -1.0])   # gravity anyway
        direction = direction / np.linalg.norm(direction)
        gravity_vector = magnitude * direction
        approximation = None
        if force_words['fixed_in'] == 'frame' and \
                the_preset.radius_si is not None:
            magnitude_si = magnitude * scales.acceleration
            timescale_si = np.sqrt(the_preset.radius_si / magnitude_si)
            approximation = Approximation(UNIFORM_APPROXIMATION_NOTE,
                                          timescale_si / scales.time)
        field = make_field('uniform', force_words['fixed_in'],
                           gravity_vector, frame, approximation)

    stop = data['run']['stop']
    if stop not in the_preset.stop_rules:
        raise RunFileError(f'run.stop: {stop!r} is not a rule the '
                           f'{the_preset.name} stage has; one of '
                           f'{", ".join(the_preset.stop_rules)}')

    specs = []
    for index, launch in enumerate(data.get('launch', [])):
        label = f'launch[{index}]'
        specs.append(LaunchSpec(
            position=_vector(launch['position'], 'length',
                             f'{label}.position', scales),
            velocity=_vector(launch.get('velocity'), 'speed',
                             f'{label}.velocity', scales),
            speed=_quantity(launch.get('speed'), 'speed', f'{label}.speed',
                            scales),
            azimuth=_quantity(launch.get('azimuth', 0.0), 'angle',
                              f'{label}.azimuth', scales),
            elevation=_quantity(launch.get('elevation', 0.0), 'angle',
                                f'{label}.elevation', scales),
            frame=launch['frame'],
            mass=(None if launch.get('mass') is None else
                  units.parse(launch['mass'], 'mass', f'{label}.mass')
                  if isinstance(launch['mass'], str) else
                  float(launch['mass'])),
            label=launch['label']))
    ring = None
    if 'ring' in data:
        ring_words = data['ring']
        ring = RingSpec(
            count=int(ring_words['count']),
            radius=_quantity(ring_words['radius'], 'length', 'ring.radius',
                             scales),
            speed=_quantity(ring_words['speed'], 'speed', 'ring.speed',
                            scales),
            target=_vector(ring_words['target'], 'length', 'ring.target',
                           scales),
            sense=ring_words['sense'],
            phase=_quantity(ring_words['phase'], 'angle', 'ring.phase',
                            scales),
            height=_quantity(ring_words['height'], 'length', 'ring.height',
                             scales))
        try:
            check_ring(ring, stop)
        except ValueError as problem:
            raise RunFileError(str(problem)) from None
        specs += expand_ring(ring)
    if not specs:
        raise RunFileError('no launch and no ring: nothing to throw')
    for spec in specs:
        try:
            check_launch(spec, stop)
        except ValueError as problem:
            raise RunFileError(str(problem)) from None
    launches = [resolve_launch(spec, axes, frame) for spec in specs]

    view_words = data['view']
    if view_words['tracked'] >= len(launches):
        raise RunFileError(f'view.tracked: {view_words["tracked"]} but '
                           f'there are only {len(launches)} particles')
    duration = _quantity(data['run']['duration'], 'time', 'run.duration',
                         scales)
    if duration <= 0.0:
        raise RunFileError('run.duration: must be positive')
    overlay_note = None
    if view_words['overlay'] == 'on' and not overlay_applies(frame,
                                                             duration):
        overlay_note = OVERLAY_OFF_NOTE
    check_words = data['check']
    check = CheckSettings(enabled=check_words['enabled'],
                          integrator=check_words['integrator'],
                          substeps=int(check_words['substeps']),
                          rtol=float(check_words['rtol']),
                          atol=float(check_words['atol']))
    camera = dict(KEYS[('view', 'camera')].default)
    camera.update(view_words['camera'])
    view = ViewSettings(palette=view_words['palette'],
                        views=view_words['views'],
                        arrows=frozenset(view_words['arrows']),
                        ghost=view_words['ghost'],
                        check_path=view_words['check_path'],
                        overlay=view_words['overlay'],
                        triads=view_words['triads'],
                        stage=view_words['stage'],
                        panels=view_words['panels'],
                        legend=view_words['legend'],
                        arrow_scale=view_words['arrow_scale'],
                        tracked=int(view_words['tracked']), camera=camera)
    data['view']['camera'] = camera
    return RunSpec(preset=the_preset, frame=frame, scales=scales,
                   latitude=latitude, axes=axes, field=field,
                   launches=launches, ring=ring, duration=duration,
                   stop=stop, samples=int(data['run']['samples']),
                   method=data['run']['method'], check=check, view=view,
                   exaggeration=exaggeration, overlay_note=overlay_note,
                   words=data, version=rotating_frame.__version__)


def resolved_words(spec, view=None):
    """The run's words with the session's view state written in, if
    given (pseudocode 10.4), ready to write."""
    words = copy.deepcopy(spec.words)
    if view is not None:
        words['view'] = {'palette': view.palette, 'views': view.views,
                         'arrows': sorted(view.arrows), 'ghost': view.ghost,
                         'check_path': view.check_path,
                         'overlay': view.overlay, 'triads': view.triads,
                         'stage': view.stage, 'panels': view.panels,
                         'legend': view.legend,
                         'arrow_scale': view.arrow_scale,
                         'tracked': view.tracked,
                         'camera': dict(view.camera)}
    return words


def write_resolved(spec, path, view=None):
    """Write the resolved run file with a header naming the scale
    factors. A write that fails is one line on standard error and
    returns False (contract C16); it never stops a run."""
    scales = spec.scales
    header = (f'# Resolved by rfsim {spec.version}: every default filled '
              'in, the preset written out.\n'
              f'# Omega = {scales.rate!r} rad/s (exaggeration '
              f'{spec.exaggeration!r}), L = {scales.length!r} m, '
              f'T = {scales.time!r} s.\n\n')
    body = tomli_w.dumps(resolved_words(spec, view))
    try:
        Path(path).write_text(header + body)
    except OSError as problem:
        print(f'note: cannot write {path} ({problem.strerror})',
              file=sys.stderr)
        return False
    return True
