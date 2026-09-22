"""The bodies of the commands, and what every command shares.

A command's body is a module here, not in `src/scripts/`, because the
command is reached in two ways that must run the same code (physdemo
contract C5): the executable front in `src/scripts/`, which the
physdemo suite links and a clone runs directly, and the console script
that `pip install` creates from `pyproject.toml`. `support.py` is the
module every command uses and is inherited from the skeleton; the
other modules are one per command.

Attribution: this module is part of the Rotating Frame teaching tool.
"""
