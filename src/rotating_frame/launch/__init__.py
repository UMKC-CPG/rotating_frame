"""What is thrown: a launch in the student's words, resolved to the
inertial state the motion provider takes, and the ring as shorthand
for many launches (pseudocode 7; design 7; ARCHITECTURE 3.3).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from rotating_frame.launch.launch_spec import (LaunchSpec, LocalAxes,
                                               ResolvedLaunch,
                                               check_launch,
                                               local_velocity,
                                               resolve_launch)
from rotating_frame.launch.ring import RingSpec, check_ring, expand_ring

__all__ = ['LaunchSpec', 'LocalAxes', 'ResolvedLaunch', 'check_launch',
           'local_velocity', 'resolve_launch', 'RingSpec', 'check_ring',
           'expand_ring']
