"""The units boundary: the one module that imports pint (pseudocode
2.2; design 2.5; ARCHITECTURE 6.6).

Three jobs and no others: turn a dimensioned string from the run file
("33.3 rpm", "39 deg", "10 m/s") into an SI number of a stated
dimension, refusing a string of the wrong dimension with the run-file
key named; turn a vector of such strings into three numbers; and
format an SI number back into a chosen display unit for the readouts.
Bare numbers never come here: the schema decides which keys may be
bare and takes them as natural units.

Below `run/`, no module imports pint, accepts a pint quantity, or
returns one; the architectural test enforces it. The reason is the
scattering tool's: pint's cost and its verbosity stay at the edge,
and a student reading the physics sees numbers.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np
import pint

# Built once, at import; every quantity in the tool goes through it.
REGISTRY = pint.UnitRegistry()

# The SI unit every dimension is reduced to. "rpm" and "deg" parse
# through pint's own definitions (a revolution is 2 pi radians).
SI_UNIT = {'length': 'meter', 'time': 'second', 'speed': 'meter/second',
           'acceleration': 'meter/second**2', 'angle': 'radian',
           'rate': 'radian/second', 'mass': 'kilogram'}

# What a student is told to write when a string is refused.
EXAMPLE = {'length': '1.2 m', 'time': '10 s', 'speed': '3 m/s',
           'acceleration': '9.8 m/s^2', 'angle': '39 deg',
           'rate': '33.3 rpm', 'mass': '0.2 kg'}


class UnitsError(ValueError):
    """A run-file value that cannot be read as the quantity its key
    requires. `key` names the run-file key; `message` is one line a
    student can act on."""

    def __init__(self, key, message):
        super().__init__(message)
        self.key = key
        self.message = message


def parse(text, kind, key):
    """A dimensioned string to an SI float of dimension `kind`.

    Strict about dimension on purpose: a speed where a length was
    asked for is an error naming the key, never a silent number."""
    if kind not in SI_UNIT:
        raise ValueError(f'unknown kind {kind!r}')
    try:
        quantity = REGISTRY.Quantity(text)
    except (pint.errors.PintError, ValueError, TypeError,
            AttributeError) as problem:
        raise UnitsError(key, f'{key}: cannot read {text!r} as a {kind} '
                              f'({problem})') from None
    try:
        return float(quantity.to(SI_UNIT[kind]).magnitude)
    except pint.errors.DimensionalityError:
        raise UnitsError(key, f'{key}: {text!r} is not a {kind}; expected '
                              f'units like {EXAMPLE[kind]!r}') from None


def parse_vector(texts, kind, key):
    """Three dimensioned strings to an SI array of shape (3,). A
    bare number among them is refused; the schema converts a fully
    bare vector itself."""
    if len(texts) != 3:
        raise UnitsError(key, f'{key}: expected three components, got '
                              f'{len(texts)}')
    return np.array([parse(text, kind, f'{key}[{index}]')
                     for index, text in enumerate(texts)])


def format_real(value_si, kind, unit):
    """An SI number shown in the display unit `unit`, four
    significant figures, with pint's compact unit symbol:
    `format_real(0.0155, 'length', 'cm')` is `'1.55 cm'`."""
    quantity = REGISTRY.Quantity(value_si, SI_UNIT[kind]).to(unit)
    return f'{quantity.magnitude:.4g} {quantity.units:~}'
