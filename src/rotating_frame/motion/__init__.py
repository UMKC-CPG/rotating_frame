"""How each particle moves: the closed forms, the equations of motion,
the integrators, the stopping rules, and the provider that ties them
together (pseudocode 4; design 4; ARCHITECTURE 3.4 and 6.2).

The motion provider turns a launch, a force field, a frame, and a
duration into inertial samples. It takes the closed form whenever the
field declares one, which in the first version is always, and
integrates only where none exists or where a run asks for the
numerical route to see an integrator's error against an exact answer.
The integrators serve the rotating-frame check of design 6 as well.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from rotating_frame.motion.motion_provider import (METHODS, Trajectory,
                                                   provide)
from rotating_frame.motion.stopping import (DurationRule, LandsRule,
                                            LeavesRule, StopEvent,
                                            make_rule)

__all__ = ['METHODS', 'Trajectory', 'provide', 'DurationRule',
           'LandsRule', 'LeavesRule', 'StopEvent', 'make_rule']
