"""The key chords (pseudocode 10.2; design 10.5).

Every key is a Ctrl chord, because vedo binds the plain letters to
viewer actions of its own and a plain binding of the tool's is
shadowed sooner or later. Keys arrive from vedo already prefixed
("Ctrl+s", "Ctrl+minus", "Ctrl+bracketleft") and are matched
case-sensitively, because Shift changes the key symbol: "Ctrl+S" is
Ctrl+Shift+s, which is how step back is reached from step forward.
The legend in the window (Ctrl+h) lists every chord, so nothing
needs memorizing (VISION P5).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
shared table is the scattering tool's `ui/controls.py`.
"""

# chord -> (command, one-line help); an alias carries None for help.
# The order is the legend's order: the table shared with the
# scattering tool first, then this tool's own (design 10.5).
_BINDINGS = (
    ('Ctrl+space', 'play_pause', 'play / pause'),
    ('Ctrl+s', 'step_forward', 'one sample forward, then pause'),
    ('Ctrl+S', 'step_back', 'one sample back, then pause (Shift)'),
    ('Ctrl+plus', 'faster', 'rate x 2, up to 16'),
    ('Ctrl+equal', 'faster', None),
    ('Ctrl+minus', 'slower', 'rate / 2, down to 1'),
    ('Ctrl+underscore', 'slower', None),
    ('Ctrl+n', 'normal', 'rate 1'),
    ('Ctrl+r', 'reverse', 'reverse direction'),
    ('Ctrl+Home', 'jump_start', 'first sample'),
    ('Ctrl+End', 'jump_end', 'last sample'),
    ('Ctrl+l', 'loop', 'toggle loop at the end'),
    ('Ctrl+Tab', 'next_tracked', 'next tracked particle'),
    ('Ctrl+a', 'toggle_all_arrows', 'toggle all arrows'),
    ('Ctrl+c', 'cycle_palette', 'cycle the palette'),
    ('Ctrl+w', 'save', 'write the resolved run file, with the view'),
    ('Ctrl+h', 'toggle_legend', 'hide / show this legend'),
    ('Ctrl+q', 'quit', 'quit (also q)'),
    ('q', 'quit', None),
    ('Ctrl+v', 'cycle_view', 'cycle the view: both, inertial, rotating'),
    ('Ctrl+1', 'toggle_arrow_true', 'toggle the true-force arrow'),
    ('Ctrl+2', 'toggle_arrow_centrifugal', 'toggle the centrifugal arrow'),
    ('Ctrl+3', 'toggle_arrow_coriolis', 'toggle the Coriolis arrow'),
    ('Ctrl+4', 'toggle_arrow_euler', 'toggle the Euler arrow'),
    ('Ctrl+5', 'toggle_arrow_sum', 'toggle the sum arrow'),
    ('Ctrl+6', 'toggle_arrow_velocity', 'toggle the velocity arrow'),
    ('Ctrl+g', 'toggle_ghost', 'toggle the ghost path'),
    ('Ctrl+k', 'toggle_check', "toggle the check's path"),
    ('Ctrl+o', 'toggle_overlay', 'toggle the first-order overlay'),
    ('Ctrl+t', 'toggle_triads', 'toggle the triads'),
    ('Ctrl+d', 'toggle_stage', 'toggle the stage'),
    ('Ctrl+f', 'toggle_camera_mode', 'camera: follow P / fixed'),
    ('Ctrl+m', 'toggle_arrow_mode', 'arrow scales: auto / same'),
    ('Ctrl+p', 'toggle_panels', 'hide / show the panel strip'),
    ('Ctrl+e', 'jump_event', "the tracked particle's stop event"),
    ('Ctrl+0', 'reset_camera', "restore the run file's cameras"),
    ('Ctrl+bracketright', 'exaggeration_up', 'exaggeration x 2 (run)'),
    ('Ctrl+bracketleft', 'exaggeration_down', 'exaggeration / 2 (run)'),
    ('Ctrl+period', 'substeps_up', 'check substeps x 2 (run)'),
    ('Ctrl+comma', 'substeps_down', 'check substeps / 2 (run)'),
    ('Ctrl+Up', 'speed_up', "tracked launch's speed x 2 (run)"),
    ('Ctrl+Down', 'speed_down', "tracked launch's speed / 2 (run)"),
    ('Ctrl+Right', 'azimuth_right', "tracked launch's azimuth + 15 deg"),
    ('Ctrl+Left', 'azimuth_left', "tracked launch's azimuth - 15 deg"),
    ('Ctrl+Prior', 'elevation_up', "tracked launch's elevation + 15 deg "
                                   '(Page Up)'),
    ('Ctrl+Next', 'elevation_down', "tracked launch's elevation - 15 deg "
                                    '(Page Down)'),
)

KEY_CHORDS = {chord: command for chord, command, _ in _BINDINGS}
LEGEND = [(chord, help_text) for chord, _, help_text in _BINDINGS]


def command_for(key):
    """The command bound to `key`, matched case-sensitively as vedo
    delivers it, or None."""
    return KEY_CHORDS.get(key)


def legend_lines():
    """The legend, one line per chord that carries help."""
    width = max(len(chord) for chord, help_text in LEGEND if help_text)
    return [f'{chord:<{width}}  {help_text}'
            for chord, help_text in LEGEND if help_text]
