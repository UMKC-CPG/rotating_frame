"""The scrubber and the session: the pure state machine, the key
chords, the two controls sources, and the loop that ties them to the
renderer (pseudocode 10; design 10; ARCHITECTURE 3.9).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from rotating_frame.ui.controls import (KEY_CHORDS, command_for,
                                        legend_lines)
from rotating_frame.ui.interactive_session import (TICK_MILLISECONDS,
                                                   Session, run_session)
from rotating_frame.ui.session_state import (ARROW_NAMES, OTHER_COMMANDS,
                                             PATH_NAMES, RATES,
                                             RUN_COMMANDS, SCENERY_NAMES,
                                             VIEWING_COMMANDS, VIEWS,
                                             SessionState, initial_state,
                                             tick, transition)
from rotating_frame.ui.vedo_controls import (ControlsSource,
                                             ScriptedControls,
                                             VedoControls, parse_script)

__all__ = ['KEY_CHORDS', 'command_for', 'legend_lines',
           'TICK_MILLISECONDS', 'Session', 'run_session', 'ARROW_NAMES',
           'OTHER_COMMANDS', 'PATH_NAMES', 'RATES', 'RUN_COMMANDS',
           'SCENERY_NAMES', 'VIEWING_COMMANDS', 'VIEWS', 'SessionState',
           'initial_state', 'tick', 'transition', 'ControlsSource',
           'ScriptedControls', 'VedoControls', 'parse_script']
