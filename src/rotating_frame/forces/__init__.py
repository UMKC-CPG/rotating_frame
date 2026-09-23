"""The force fields: what acts on the particle (pseudocode 3;
design 3; ARCHITECTURE 3.2 and 6.3).

Every field satisfies one contract, `ForceField`, and declares by
name what it can do: a closed form the motion provider knows, a
potential with the frame it is fixed in, and an approximation note
for the screen. Consumers ask for these by capability and never by
field type. The first version ships no force and uniform gravity in
two kinds; central gravity, a spring, and a central attraction on
the turntable are future fields behind the same interface.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

from rotating_frame.forces.force_interface import (Approximation,
                                                   ForceField, Potential)
from rotating_frame.forces.fields import (NoForce,
                                          UniformGravityFrameFixed,
                                          UniformGravitySpaceFixed,
                                          make_field)

__all__ = ['Approximation', 'ForceField', 'Potential', 'NoForce',
           'UniformGravityFrameFixed', 'UniformGravitySpaceFixed',
           'make_field']
