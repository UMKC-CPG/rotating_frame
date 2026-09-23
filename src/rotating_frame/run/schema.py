"""The run-file schema: every key, its kind, its default, and what is
refused (pseudocode 8.1; design 8.1 and 8.2).

A run file is TOML beginning `schema = 1` with the tables frame,
force, launch (an array of tables), ring, run, check, and view. Every
key is one `Key` here: its kind, the dimension a quantity must have,
its default (a value, REQUIRED, PRESET for one the preset fills, or
OPTIONAL for one that may be absent), whether a bare number is
accepted in natural units, and its choices. `validate_raw` checks a
parsed file against the table and refuses, with a message naming the
key as `table.key`, everything design 8.2 lists. Nothing here knows
units; the boundary (`core/units.py`) converts strings after the
schema has said which keys hold them.

One point where this schema is stricter than the pseudocode's table:
`frame.rate` and `frame.length_scale` must be dimensioned strings,
because they define the natural units that a bare number would be
expressed in.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from dataclasses import dataclass

SCHEMA_VERSION = 1

REQUIRED = 'REQUIRED'
PRESET = 'PRESET'
OPTIONAL = 'OPTIONAL'

ARROW_NAMES = ('true', 'centrifugal', 'coriolis', 'euler', 'sum',
               'velocity')


class RunFileError(Exception):
    """A run file that cannot be used, with a message a student can
    act on. The command prints it and exits with status 2."""


@dataclass(frozen=True)
class Key:
    """One run-file key."""

    table: str
    name: str
    kind: str                    # number int bool string choice
                                 #   quantity vector table string_list
    dimension: str = None        # for quantity and vector
    default: object = None
    bare: bool = False
    choices: tuple = ()


SCHEMA = [
    Key('frame', 'preset', 'choice', default=REQUIRED,
        choices=('turntable', 'merry_go_round', 'earth')),
    Key('frame', 'rate', 'quantity', 'rate', PRESET),
    Key('frame', 'latitude', 'quantity', 'angle', OPTIONAL, bare=True),
    Key('frame', 'length_scale', 'quantity', 'length', PRESET),
    Key('frame', 'exaggeration', 'number', default=1.0),
    Key('force', 'kind', 'choice', default=PRESET,
        choices=('none', 'uniform')),
    Key('force', 'fixed_in', 'choice', default=PRESET,
        choices=('space', 'frame')),
    Key('force', 'magnitude', 'quantity', 'acceleration', PRESET, bare=True),
    Key('launch', 'position', 'vector', 'length', default=[0.0, 0.0, 0.0],
        bare=True),
    Key('launch', 'velocity', 'vector', 'speed', OPTIONAL, bare=True),
    Key('launch', 'speed', 'quantity', 'speed', OPTIONAL, bare=True),
    Key('launch', 'azimuth', 'quantity', 'angle', 0.0, bare=True),
    Key('launch', 'elevation', 'quantity', 'angle', 0.0, bare=True),
    Key('launch', 'frame', 'choice', default='rotating',
        choices=('rotating', 'inertial')),
    Key('launch', 'mass', 'quantity', 'mass', OPTIONAL, bare=True),
    Key('launch', 'label', 'string', default=''),
    Key('ring', 'count', 'int', default=REQUIRED),
    Key('ring', 'radius', 'quantity', 'length', REQUIRED, bare=True),
    Key('ring', 'target', 'vector', 'length', default=[0.0, 0.0, 0.0],
        bare=True),
    Key('ring', 'speed', 'quantity', 'speed', REQUIRED, bare=True),
    Key('ring', 'sense', 'choice', default='inward',
        choices=('inward', 'outward')),
    Key('ring', 'phase', 'quantity', 'angle', 0.0, bare=True),
    Key('ring', 'height', 'quantity', 'length', 0.0, bare=True),
    Key('run', 'duration', 'quantity', 'time', REQUIRED, bare=True),
    Key('run', 'stop', 'choice', default=PRESET,
        choices=('duration', 'lands', 'leaves')),
    Key('run', 'samples', 'int', default=1000),
    Key('run', 'method', 'choice', default='auto',
        choices=('auto', 'closed_form', 'numerical')),
    Key('check', 'enabled', 'bool', default=True),
    Key('check', 'integrator', 'choice', default='rk4',
        choices=('euler', 'rk4', 'dop853')),
    Key('check', 'substeps', 'int', default=4),
    Key('check', 'rtol', 'number', default=1e-10),
    Key('check', 'atol', 'number', default=1e-12),
    Key('view', 'palette', 'choice', default='light',
        choices=('light', 'dark', 'colorblind')),
    Key('view', 'views', 'choice', default='both',
        choices=('both', 'inertial', 'rotating')),
    Key('view', 'arrows', 'string_list', default=list(ARROW_NAMES),
        choices=ARROW_NAMES),
    Key('view', 'ghost', 'bool', default=True),
    Key('view', 'check_path', 'bool', default=False),
    Key('view', 'overlay', 'choice', default='auto',
        choices=('auto', 'on', 'off')),
    Key('view', 'triads', 'bool', default=True),
    Key('view', 'stage', 'bool', default=True),
    Key('view', 'panels', 'bool', default=True),
    Key('view', 'legend', 'bool', default=True),
    Key('view', 'arrow_scale', 'choice', default='auto',
        choices=('auto', 'same')),
    Key('view', 'tracked', 'int', default=0),
    Key('view', 'camera', 'table',
        default={'azimuth_deg': 35.0, 'elevation_deg': 25.0,
                 'distance': 3.0, 'follow': True}),
]

KEYS = {(key.table, key.name): key for key in SCHEMA}
TABLES = ('frame', 'force', 'launch', 'ring', 'run', 'check', 'view')
CAMERA_KEYS = {'azimuth_deg': 'number', 'elevation_deg': 'number',
               'distance': 'number', 'follow': 'bool'}

# The latitude beyond which the local east vector is undefined
# (pseudocode 2.4), in degrees.
LATITUDE_LIMIT_DEG = 89.9


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_value(key, value, label):
    """Refuse `value` if it is not of `key`'s kind."""
    kind = key.kind
    if kind == 'number' and not _is_number(value):
        raise RunFileError(f'{label}: expected a number, got {value!r}')
    if kind == 'int' and not (isinstance(value, int)
                              and not isinstance(value, bool)):
        raise RunFileError(f'{label}: expected an integer, got {value!r}')
    if kind == 'bool' and not isinstance(value, bool):
        raise RunFileError(f'{label}: expected true or false, got '
                           f'{value!r}')
    if kind == 'string' and not isinstance(value, str):
        raise RunFileError(f'{label}: expected a string, got {value!r}')
    if kind == 'choice':
        if not isinstance(value, str) or value not in key.choices:
            raise RunFileError(f'{label}: {value!r} is not one of '
                               f'{", ".join(key.choices)}')
    if kind == 'quantity':
        if isinstance(value, str):
            return
        if _is_number(value) and key.bare:
            return
        if _is_number(value):
            raise RunFileError(f'{label}: needs units, for example a '
                               f'string like "1 {key.dimension}"')
        raise RunFileError(f'{label}: expected a quantity, got {value!r}')
    if kind == 'vector':
        if not isinstance(value, list) or len(value) != 3:
            raise RunFileError(f'{label}: expected three components')
        strings = all(isinstance(part, str) for part in value)
        numbers = all(_is_number(part) for part in value)
        if not (strings or (numbers and key.bare)):
            raise RunFileError(f'{label}: give three strings with units, '
                               'or three bare numbers')
    if kind == 'string_list':
        if not isinstance(value, list) or not all(
                isinstance(part, str) and part in key.choices
                for part in value):
            raise RunFileError(f'{label}: expected a list drawn from '
                               f'{", ".join(key.choices)}')
    if kind == 'table':
        if not isinstance(value, dict):
            raise RunFileError(f'{label}: expected a table')
        for name, part in value.items():
            if name not in CAMERA_KEYS:
                raise RunFileError(f'{label}.{name}: unknown key')
            wanted = CAMERA_KEYS[name]
            if wanted == 'number' and not _is_number(part):
                raise RunFileError(f'{label}.{name}: expected a number')
            if wanted == 'bool' and not isinstance(part, bool):
                raise RunFileError(f'{label}.{name}: expected true or '
                                   'false')


def _check_table(table, contents, label):
    if not isinstance(contents, dict):
        raise RunFileError(f'{label}: expected a table')
    for name, value in contents.items():
        key = KEYS.get((table, name))
        if key is None:
            raise RunFileError(f'{label}.{name}: unknown key')
        _check_value(key, value, f'{label}.{name}')


def validate_raw(data):
    """Refuse a parsed run file that the schema cannot accept."""
    if not isinstance(data, dict):
        raise RunFileError('the run file must hold tables')
    if data.get('schema') != SCHEMA_VERSION:
        raise RunFileError(f'expected schema = {SCHEMA_VERSION} at the '
                           'top of the run file')
    for table, contents in data.items():
        if table == 'schema':
            continue
        if table not in TABLES:
            raise RunFileError(f'[{table}]: unknown table')
        if table == 'launch':
            if not isinstance(contents, list):
                raise RunFileError('[[launch]]: expected an array of '
                                   'tables')
            for index, launch in enumerate(contents):
                _check_table('launch', launch, f'launch[{index}]')
        else:
            _check_table(table, contents, table)
    frame = data.get('frame', {})
    if 'preset' not in frame:
        raise RunFileError('frame.preset: required')
    for table, name in (('run', 'duration'),):
        if name not in data.get(table, {}):
            raise RunFileError(f'{table}.{name}: required')
    if 'ring' in data:
        for name in ('count', 'radius', 'speed'):
            if name not in data['ring']:
                raise RunFileError(f'ring.{name}: required')
    for index, launch in enumerate(data.get('launch', [])):
        if 'velocity' in launch and 'speed' in launch:
            raise RunFileError(f'launch[{index}]: give velocity or speed, '
                               'not both')
        if 'elevation' in launch and 'speed' not in launch:
            raise RunFileError(f'launch[{index}].elevation: needs '
                               f'launch[{index}].speed')
    is_earth = frame['preset'] == 'earth'
    if is_earth and 'latitude' not in frame:
        raise RunFileError('frame.latitude: required for the earth preset')
    if not is_earth and 'latitude' in frame:
        raise RunFileError('frame.latitude: only the earth preset has one')
    if data.get('run', {}).get('samples', 2) < 2:
        raise RunFileError('run.samples: must be at least 2')
    if data.get('check', {}).get('substeps', 1) < 1:
        raise RunFileError('check.substeps: must be at least 1')
    if frame.get('exaggeration', 1.0) <= 0.0:
        raise RunFileError('frame.exaggeration: must be positive')
    if data.get('ring', {}).get('count', 1) < 1:
        raise RunFileError('ring.count: must be at least 1')
    if data.get('view', {}).get('tracked', 0) < 0:
        raise RunFileError('view.tracked: must not be negative')


def check_latitude(latitude_radians):
    """Refuse a latitude at which the local east is undefined."""
    limit = LATITUDE_LIMIT_DEG * 3.141592653589793 / 180.0
    if abs(latitude_radians) >= limit:
        raise RunFileError(f'frame.latitude: must lie strictly within '
                           f'±{LATITUDE_LIMIT_DEG} degrees')


def apply_overrides(data, overrides):
    """Apply `--set TABLE.KEY=VALUE` overrides to the parsed data, the
    value parsed as TOML. `launch[0].speed` addresses a launch."""
    try:
        import tomllib
    except ModuleNotFoundError:                  # Python 3.10
        import tomli as tomllib
    for override in overrides:
        if '=' not in override or '.' not in override.split('=', 1)[0]:
            raise RunFileError(f'--set {override!r}: expected '
                               'TABLE.KEY=VALUE')
        dotted, raw_value = override.split('=', 1)
        table, name = dotted.strip().split('.', 1)
        try:
            value = tomllib.loads(f'v = {raw_value.strip()}')['v']
        except tomllib.TOMLDecodeError as problem:
            raise RunFileError(f'--set {override!r}: cannot read the '
                               f'value ({problem})') from None
        if table.startswith('launch[') and table.endswith(']'):
            index = int(table[len('launch['):-1])
            launches = data.setdefault('launch', [])
            while len(launches) <= index:
                launches.append({})
            launches[index][name] = value
        else:
            data.setdefault(table, {})[name] = value
    return data
