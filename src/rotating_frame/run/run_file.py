"""Loading and validating a TOML run file (physdemo PSEUDOCODE 4.4).

The schema is a small table from `table.key` to a type and a default.
Every key in a run file must be in the table, so that a misspelled key
is an error rather than a silently ignored one, and every key in the
table has a value after loading, so that the rest of the tool never
looks up a default. Command-line overrides of the form
`table.key=value` are applied before validation, with the value parsed
as TOML so that strings, numbers, and lists all work.

A tool replaces this table with its own schema under its DESIGN, and
keeps the shape: the resolved run is a plain dictionary of tables.

Attribution: this module is part of the Rotating Frame teaching tool.
"""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:                      # Python 3.10
    import tomli as tomllib

# The run-file schema version that this code understands. A run file
# says `schema = 1` at its top so that a later, incompatible layout
# can be told apart from a typo.
SCHEMA_VERSION = 1

# table.key -> (type, default). The placeholder physics of core/motion
# and the one presentation choice a run file records.
SCHEMA = {
    'motion.radius':        (float, 1.0),
    'motion.angular_speed': (float, 1.0),
    'motion.n_steps':       (int, 200),
    'motion.dt':            (float, 0.05),
    'view.palette':         (str, 'light'),
}


class RunFileError(Exception):
    """A run file that cannot be used, with a message a student can
    act on. The command prints it and exits with status 2; it is
    never a traceback."""


def _coerce(name, value, expected_type):
    """Return `value` as `expected_type`, or raise RunFileError.

    An integer is accepted where a float is expected (TOML writes
    `1` and `1.0` differently, and a student should not have to
    care), but a boolean is never accepted as a number, and nothing
    is accepted as a string but a string.
    """
    if isinstance(value, bool):
        raise RunFileError(f'{name}: expected {expected_type.__name__}, '
                           f'got the boolean {value}')
    if expected_type is float and isinstance(value, int):
        return float(value)
    if not isinstance(value, expected_type):
        raise RunFileError(f'{name}: expected {expected_type.__name__}, '
                           f'got {value!r}')
    return value


def _apply_override(data, override):
    """Set one `table.key=value` override into the raw TOML data."""
    if '=' not in override or '.' not in override.split('=', 1)[0]:
        raise RunFileError(f'--set {override!r}: expected '
                           'TABLE.KEY=VALUE')
    dotted, raw_value = override.split('=', 1)
    table, key = dotted.strip().split('.', 1)
    try:
        value = tomllib.loads(f'v = {raw_value.strip()}')['v']
    except tomllib.TOMLDecodeError as problem:
        raise RunFileError(f'--set {override!r}: cannot read the value '
                           f'({problem})') from None
    data.setdefault(table, {})[key] = value


def load_run_file(path, overrides=()):
    """Read `path`, apply `overrides`, validate against SCHEMA, and
    return the resolved run as {table: {key: value}} with every
    schema key present."""
    path = Path(path)
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as problem:
        raise RunFileError(f'{path}: not valid TOML ({problem})') from None
    if data.get('schema') != SCHEMA_VERSION:
        raise RunFileError(f'{path}: expected schema = {SCHEMA_VERSION} '
                           'at the top of the run file')
    for override in overrides:
        _apply_override(data, override)
    for table, contents in data.items():
        if table == 'schema':
            continue
        if not isinstance(contents, dict):
            raise RunFileError(f'{path}: [{table}] must be a table')
        for key in contents:
            if f'{table}.{key}' not in SCHEMA:
                raise RunFileError(f'{path}: unknown key [{table}] {key}')
    resolved = {}
    for dotted, (expected_type, default) in SCHEMA.items():
        table, key = dotted.split('.', 1)
        value = data.get(table, {}).get(key, default)
        resolved.setdefault(table, {})[key] = _coerce(dotted, value,
                                                      expected_type)
    return resolved
