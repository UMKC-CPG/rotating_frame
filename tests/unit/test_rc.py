"""Verifies pseudocode 8.7 for `run/rc.py`: the built-in defaults,
the inherited search order, and an unknown key dropped with a note."""

from rotating_frame.run import RC_FILENAME, load_rc
from rotating_frame.run.rc import BUILTIN_RC


def test_defaults_without_a_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('ROTATING_FRAME_RC', raising=False)
    settings = load_rc([tmp_path])
    assert settings.window_size == tuple(BUILTIN_RC['window_size'])
    assert settings.max_store_bytes == BUILTIN_RC['max_store_bytes']


def test_the_search_order_and_an_unknown_key(tmp_path, monkeypatch,
                                             capsys):
    machine = tmp_path / 'machine'
    machine.mkdir()
    (machine / RC_FILENAME).write_text(
        "def parameters_and_defaults():\n"
        "    return {'arrow_scale': 2.0, 'colour': 'red'}\n")
    working = tmp_path / 'work'
    working.mkdir()
    (working / RC_FILENAME).write_text(
        "def parameters_and_defaults():\n    return {'arrow_scale': 3.0}\n")
    monkeypatch.setenv('ROTATING_FRAME_RC', str(machine))
    monkeypatch.chdir(tmp_path)
    assert load_rc().arrow_scale == 2.0
    assert 'colour' in capsys.readouterr().err
    monkeypatch.chdir(working)
    assert load_rc().arrow_scale == 3.0


def test_the_packaged_rc_file_loads():
    from rotating_frame.cli.support import PACKAGE_DEFAULTS_DIR
    settings = load_rc([PACKAGE_DEFAULTS_DIR])
    assert settings.default_palette in ('light', 'dark', 'colorblind')
