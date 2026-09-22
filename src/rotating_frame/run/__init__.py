"""The run file: the complete, self-contained description of one run.

A run file holds everything that can affect a computed result; the rc
file (`defaults/`) holds only what is machine-local (physdemo
ARCHITECTURE 5, DESIGN 4). The schema lives in `run_file.py`, and a
tool extends it under its own DESIGN section.

Attribution: this module is part of the Rotating Frame teaching tool.
"""

from rotating_frame.run.run_file import SCHEMA, RunFileError, load_run_file

__all__ = ['SCHEMA', 'RunFileError', 'load_run_file']
