"""The architectural tests of ARCHITECTURE 8.6 that can be checked by
reading the source: the ground-truth rule (6.1), the import rule (5),
and the units boundary (6.6)."""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / 'src' / 'rotating_frame'
PHYSICS_GROUPS = ('core', 'forces', 'launch', 'motion', 'pseudoforces',
                  'analysis', 'geometry')


def imports_of(path):
    names = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def modules_under(group):
    directory = PACKAGE / group
    return sorted(directory.rglob('*.py')) if directory.is_dir() else []


@pytest.mark.parametrize('group', ['render', 'ui', 'geometry'])
def test_nothing_that_draws_imports_the_integration(group):
    for path in modules_under(group):
        for name in imports_of(path):
            assert not name.startswith('rotating_frame.motion'), \
                f'{path.relative_to(PACKAGE)} imports {name}'


@pytest.mark.parametrize('group', PHYSICS_GROUPS)
def test_physics_groups_do_not_import_presentation_or_run(group):
    forbidden = ('rotating_frame.render', 'rotating_frame.ui',
                 'rotating_frame.run')
    for path in modules_under(group):
        for name in imports_of(path):
            assert not name.startswith(forbidden), \
                f'{path.relative_to(PACKAGE)} imports {name}'


def test_pseudoforces_imports_only_core():
    for path in modules_under('pseudoforces'):
        for name in imports_of(path):
            if name.startswith('rotating_frame.'):
                assert name.startswith(('rotating_frame.core',
                                        'rotating_frame.pseudoforces')), \
                    f'{path.relative_to(PACKAGE)} imports {name}'


def test_only_the_units_module_imports_pint():
    offenders = []
    for path in PACKAGE.rglob('*.py'):
        if path.name == 'units.py' and path.parent.name == 'core':
            continue
        if any(name == 'pint' or name.startswith('pint.')
               for name in imports_of(path)):
            offenders.append(str(path.relative_to(PACKAGE)))
    assert offenders == []
