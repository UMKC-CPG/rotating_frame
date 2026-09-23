"""Verifies physdemo PSEUDOCODE 4.5 and 4.7: the packaged examples,
the rc copy, the self-check, and errors that are messages. Everything
here must hold in a clone, in a linked suite, and in an installed
copy, so nothing here looks for a file except through the package.
PLACEHOLDER in part: the run-specific cases at the end are replaced
with the tool's own; the utility cases stay."""

import os
import sys
from pathlib import Path

import pytest

pytest.skip('placeholder test: replaced when pseudocode 10 is coded',
            allow_module_level=True)

from rotating_frame.cli import support
from rotating_frame.cli import rfsim as cli
from rotating_frame.run import load_run_file

REPO = Path(__file__).resolve().parents[2]


def test_packaged_examples_load_and_match_runs():
    packaged = support.example_files()
    assert 'circle' in packaged
    for path in packaged.values():
        load_run_file(path)                      # raises if one is broken
    # `runs` is a link to the package directory: one set of files.
    assert {p.name for p in (REPO / 'runs').glob('*.toml')} == \
        {p.name for p in packaged.values()}


def test_locate_run_file(run_directory, capsys):
    packaged = support.example_files()['circle']
    assert support.locate_run_file(str(packaged), 'rfsim') == packaged
    assert support.locate_run_file('circle', 'rfsim') == packaged
    assert support.locate_run_file('circle.toml', 'rfsim') == packaged
    assert 'using the packaged example' in capsys.readouterr().err
    # A real file in the working directory always wins.
    (run_directory / 'circle.toml').write_text('schema = 1\n')
    assert support.locate_run_file('circle.toml', 'rfsim') == \
        Path('circle.toml')
    # A directory part, or an unknown name, is never rescued.
    for wrong in ('sub/circle', 'no_such_example'):
        with pytest.raises(FileNotFoundError, match='circle'):
            support.locate_run_file(wrong, 'rfsim')


def test_copy_examples_never_overwrites(tmp_path, capsys):
    target = tmp_path / 'my runs'
    assert support.copy_examples(target, 'rfsim') == 0
    written = sorted(p.name for p in target.iterdir())
    assert written == sorted(p.name
                             for p in support.example_files().values())
    edited = target / 'circle.toml'
    edited.write_text('# my edit\n')
    capsys.readouterr()
    assert support.copy_examples(target, 'rfsim') == 0
    assert edited.read_text() == '# my edit\n'
    assert capsys.readouterr().out.count('kept') == len(written)


def test_copy_into_a_read_only_directory_is_a_message(tmp_path, capsys):
    locked = tmp_path / 'shared'
    locked.mkdir()
    locked.chmod(0o555)
    if os.access(locked, os.W_OK):
        pytest.skip('this user can write a read-only directory')
    try:
        assert support.copy_examples(locked, 'rfsim') == 1
    finally:
        locked.chmod(0o755)
    assert 'Choose a directory you can write' in capsys.readouterr().err


def test_written_rc_file_loads_and_equals_the_defaults(tmp_path):
    assert support.copy_rc_file(cli.RC_FILENAME, tmp_path, 'rfsim') == 0
    assert support.load_rc_defaults(cli.RC_FILENAME, {}, [tmp_path]) == \
        support.load_rc_defaults(cli.RC_FILENAME, {},
                                 [support.PACKAGE_DEFAULTS_DIR])


def test_missing_run_file_is_status_2_not_a_traceback(run_directory,
                                                      capsys):
    assert cli.main(['no_such.toml']) == 2
    assert 'Packaged examples: circle' in capsys.readouterr().err


def test_a_bad_run_file_is_status_2(run_directory, capsys):
    (run_directory / 'bad.toml').write_text('schema = 1\n[motion]\n'
                                            'radius = "wide"\n')
    assert cli.main(['bad.toml']) == 2
    assert 'motion.radius' in capsys.readouterr().err


def test_usage_errors(run_directory):
    for argv in ([], ['circle', '--examples'],
                 ['circle', '--offscreen']):
        with pytest.raises(SystemExit) as leaving:
            cli.main(argv)
        assert leaving.value.code == 2


def test_record_command_writes_nothing_for_a_utility(run_directory,
                                                     monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['rfsim', '--check'])
    support.record_command()
    assert not (run_directory / 'command').exists()
    monkeypatch.setattr(sys, 'argv', ['rfsim', 'circle'])
    support.record_command()
    assert 'Cmnd: rfsim circle' in (run_directory / 'command').read_text()


def test_self_check_passes_and_writes_nothing(run_directory, capsys,
                                              offscreen_context):
    assert cli.main(['--check']) == 0
    assert 'RESULT: PASS' in capsys.readouterr().out
    assert list(run_directory.iterdir()) == []


def test_an_offscreen_run_draws_and_saves(run_directory,
                                          offscreen_context):
    assert cli.main(['circle', '--offscreen', '--frames', '3',
                     '--screenshot', 'last.png',
                     '--set', 'motion.n_steps=10']) == 0
    assert (run_directory / 'last.png').stat().st_size > 0
