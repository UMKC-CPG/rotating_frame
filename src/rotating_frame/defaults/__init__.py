"""The shipped resource-control (rc) defaults.

`rfsimrc.py` here is the documented set of machine-local defaults and
the last place `rotating_frame.cli.support.load_rc_defaults` looks. It is
inside the package, rather than beside the entry-point script, because
an installed copy of the tool has no script directory: the package is
the one location that exists however the tool was obtained (physdemo
contract C7). A user who wants to change a default copies the file to
their working directory with `rfsim --write-rc` and edits the copy.

Attribution: this module is part of the Rotating Frame teaching tool.
"""
