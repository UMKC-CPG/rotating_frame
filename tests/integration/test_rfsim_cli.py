"""Verifies pseudocode 10.7 for `cli/rfsim.py`, keeping the skeleton's
utility cases (physdemo PSEUDOCODE 4.5 and 4.7): the packaged
examples, the rc copy, the self-check, errors that are messages, and
the tool's own runs. Everything here must hold in a clone, in a
linked suite, and in an installed copy, so nothing here looks for a
file except through the package."""

import os
import sys
from pathlib import Path

import pytest

from rotating_frame.cli import rfsim as cli
from rotating_frame.cli import support
from rotating_frame.run import load_run_file

REPO = Path(__file__).resolve().parents[2]
FAST = ['--set', 'run.samples=40']


def test_packaged_examples_load_and_match_runs():
    packaged = support.example_files()
    assert set(packaged) == {'turntable', 'merry_go_round', 'earth_drop',
                             'earth_throw', 'earth_vertical'}
    for path in packaged.values():
        load_run_file(path)                      # raises if one is broken
    # `runs` is a link to the package directory: one set of files.
    assert {p.name for p in (REPO / 'runs').glob('*.toml')} == \
        {p.name for p in packaged.values()}


def test_locate_run_file(run_directory, capsys):
    packaged = support.example_files()['turntable']
    assert support.locate_run_file(str(packaged), 'rfsim') == packaged
    assert support.locate_run_file('turntable', 'rfsim') == packaged
    assert support.locate_run_file('turntable.toml', 'rfsim') == packaged
    assert 'using the packaged example' in capsys.readouterr().err
    # A real file in the working directory always wins.
    (run_directory / 'turntable.toml').write_text('schema = 1\n')
    assert support.locate_run_file('turntable.toml', 'rfsim') == \
        Path('turntable.toml')
    # A directory part, or an unknown name, is never rescued.
    for wrong in ('sub/turntable', 'no_such_example'):
        with pytest.raises(FileNotFoundError, match='turntable'):
            support.locate_run_file(wrong, 'rfsim')


def test_copy_examples_never_overwrites(tmp_path, capsys):
    target = tmp_path / 'my runs'
    assert support.copy_examples(target, 'rfsim') == 0
    written = sorted(p.name for p in target.iterdir())
    assert written == sorted(p.name
                             for p in support.example_files().values())
    edited = target / 'turntable.toml'
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
    assert 'Packaged examples: earth_drop' in capsys.readouterr().err


def test_a_bad_run_file_is_status_2(run_directory, capsys):
    (run_directory / 'bad.toml').write_text(
        'schema = 1\n[frame]\npreset = "turntable"\n[[launch]]\n'
        'speed = "wide"\n[run]\nduration = "1 s"\n')
    assert cli.main(['bad.toml']) == 2
    assert 'launch[0].speed' in capsys.readouterr().err
    (run_directory / 'ground.toml').write_text(
        'schema = 1\n[frame]\npreset = "earth"\nlatitude = "39 deg"\n'
        '[[launch]]\nspeed = "1 m/s"\nelevation = "-30 deg"\n'
        '[run]\nduration = "1 s"\n')
    assert cli.main(['ground.toml']) == 2
    assert 'no upward velocity' in capsys.readouterr().err


def test_usage_errors(run_directory):
    for argv in ([], ['turntable', '--examples'],
                 ['turntable', '--offscreen'],
                 ['turntable', '--palette', 'neon']):
        with pytest.raises(SystemExit) as leaving:
            cli.main(argv)
        assert leaving.value.code == 2


def test_a_bad_script_is_status_2(run_directory, capsys):
    assert cli.main(['turntable', '--offscreen', '--script', '3:dance']
                    + FAST) == 2
    assert 'dance' in capsys.readouterr().err


def test_record_command_writes_nothing_for_a_utility(run_directory,
                                                     monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['rfsim', '--check'])
    support.record_command()
    assert not (run_directory / 'command').exists()
    monkeypatch.setattr(sys, 'argv', ['rfsim', 'turntable'])
    support.record_command()
    assert 'Cmnd: rfsim turntable' in (run_directory / 'command').read_text()


def test_write_resolved_reloads_equal_and_shows_overrides(run_directory):
    assert cli.main(['earth_drop', '--set', 'frame.exaggeration=10',
                     '--write-resolved', 'drop.toml'] + FAST) == 0
    written = run_directory / 'drop.toml'
    assert written.exists()
    reloaded = load_run_file(written)
    assert reloaded.exaggeration == 10.0
    assert reloaded.samples == 40
    assert 'exaggeration = 10' in written.read_text()
    assert list(run_directory.iterdir()) == [written]


def test_self_check_passes_and_writes_nothing(run_directory, capsys,
                                              offscreen_context):
    assert cli.main(['--check']) == 0
    assert 'RESULT: PASS' in capsys.readouterr().out
    assert list(run_directory.iterdir()) == []


def test_an_offscreen_run_draws_and_saves(run_directory, offscreen_context):
    assert cli.main(['earth_drop', '--offscreen', '--frames', '3',
                     '--screenshot', 'last.png', '--view', 'rotating',
                     '--palette', 'dark'] + FAST) == 0
    assert (run_directory / 'last.png').stat().st_size > 0
    image = None
    try:
        import matplotlib.image
        image = matplotlib.image.imread(run_directory / 'last.png')
    except (ImportError, OSError):
        pytest.skip('cannot read the screenshot back')
    assert image.min() != image.max()


def test_an_offscreen_script_runs(run_directory, offscreen_context):
    assert cli.main(['turntable', '--offscreen',
                     '--script', '2:play_pause,6:reverse'] + FAST) == 0
    assert list(run_directory.iterdir()) == []
