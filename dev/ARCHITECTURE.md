# Architecture

> **Document hierarchy:** VISION → **ARCHITECTURE** → DESIGN →
> PSEUDOCODE → Code. For goals and principles, see `VISION.md`.
> Principles are cited as `P<n>`, goals as `G<n>`, future directions
> as `FD<n>`.

> **SKELETON.** Sections 1, 7, 8, and 9 are filled in, because the
> suite fixes them; keep them and edit the details. Sections 2 to 6
> are the tool's own and are written from `VISION.md`.

---

## 1. Repository Layout

```
rotating_frame/
  dev/
    README.md         What lives in dev/, and what is not the chain
    VISION.md         Goals and principles
    ARCHITECTURE.md   This document
    DESIGN.md         Index of design sections
    design/           One file per design section
    PSEUDOCODE.md     Index of pseudocode sections
    pseudocode/       One file per pseudocode section
    TODO.md           Task list by level
    notes/            Dated working notes (not binding)
    figures/          Diagrams and their editable sources
    spikes/           Throwaway checks whose results the chain cites
  runs                Symbolic link to src/rotating_frame/examples/
  src/
    rotating_frame/          The importable library (Section 3), including
      cli/            the entry points' bodies (Section 6),
      defaults/       the shipped rc file (Section 7), and
      examples/       the example run files (TOML)
    scripts/          Thin executable fronts for cli/ (Section 6)
  tests/
    unit/             One module under test per file
    integration/      Several modules together, or an entry point
    regression/       Frozen reference outputs
  .claude/            Slash commands and reflow helpers
  .rotating_frame/           Machine-local rc overrides (never tracked)
  CLAUDE.md           AI assistant guidance
  README.md           User-facing description
  pyproject.toml      Packaging
```

Output (images, video, data files) is regenerable from a run file
and is excluded from version control; the run file that produced it
is what is tracked.

**Everything the tool needs at run time lives under `src/rotating_frame/`,**
because that directory is all that an installed copy contains
(Section 9): the code, the shipped rc defaults, and the example run
files. `runs` at the top level is a symbolic link so that
`runs/circle.toml` is a short path in a clone; it is a convenience of
a checkout and nothing may depend on it.

---

## 2. The Structural Idea

<!-- The one or two structural ideas that everything else hangs off:
scattering's "the forward and inverse chains are the same modules"
and "precompute, then view"; rigid_body's "the simulation drives,
single-threaded" and "physics decoupled from presentation". Written
from VISION. -->

---

## 3. Module Map

<!-- One subsection per subpackage, one table row per module with its
single responsibility. The skeleton's core/motion.py is a placeholder
and is replaced; render/, cli/, defaults/, and examples/ stay. -->

### 3.1 `core/`

| Module | Single responsibility |
| --- | --- |
| `motion.py` | PLACEHOLDER: uniform circular motion (replace) |

### 3.2 `run/`

| Module | Single responsibility |
| --- | --- |
| `run_file.py` | The run-file schema, loading, validation, `--set` |

### 3.3 `render/`

| Module | Single responsibility |
| --- | --- |
| `offscreen.py` | The window-class rule; imports no VTK (inherited) |
| `palettes.py` | Named visual encodings; imports no vedo |
| `vedo_renderer.py` | The only module that imports vedo (replace) |

---

## 4. Dependency Graph

<!-- Dependencies point downward only, and this is tested. Draw the
graph once the module map exists. The fixed part: -->

```
  scripts/  (fronts only; import cli/ and nothing else)
  cli/
    +-- render/
    +-- run/
          +-- core/
```

---

## 5. Key Boundaries

<!-- The interfaces that exist to protect a VISION principle, each
one stable. -->

---

## 6. `cli/` and `scripts/`: Entry Points

An entry point is reached in two ways (Section 9), and both must run
the same code. So the body of each command is a module in the
library, and what differs is only the few lines that start it.

| Module | Purpose |
| --- | --- |
| `cli/rfsim.py` | Body of the interactive tool: argument parsing, |
| | `main(argv)`, `run_offscreen()`, `console_main()` |
| `cli/support.py` | What every command shares: the rc lookup, the |
| | command log, the packaged examples, the self-check |
| | (inherited from the suite's skeleton) |

| Front | How it is reached |
| --- | --- |
| `scripts/rfsim.py` | Executable script; the `physdemo` suite links |
| | it, and a clone runs it directly. Puts `src/` on the path from |
| | its resolved location, then calls `cli.rfsim`. |
| console script `rfsim` | Declared in `pyproject.toml`; created by |
| | `pip install`. Calls `cli.rfsim.console_main`. |

Both fronts log the invocation to `command` and then call `main()`;
`main(argv)` itself never logs, so the test suite can call it freely
(`CLAUDE.md`, "Command Logging"). Neither the fronts nor `cli/` hold
any physics. `cli/` sits at the top of the dependency graph, and
nothing imports it.

---

## 7. Configuration

Two mechanisms hold different kinds of thing, and the division is a
rule.

**The rc file** (`rfsimrc.py`) holds what is *machine-dependent and
rarely changed*: window size, preferred palette, glyph size, output
directory. It is looked for in the working directory, then in
`$ROTATING_FRAME_RC`, and last in the package itself
(`rotating_frame/defaults/rfsimrc.py`), which is the documented set of
defaults and is always present, in a clone and in an installed copy
alike. `rfsim --write-rc` copies that file into the working
directory for a user who wants to change it.

**The run file** (TOML) holds the *physics*: everything that can
affect a computed result, and the viewpoint.

```
  rc file defaults  <  run file  <  command-line arguments
```

> **Any value that can affect a computed result must live in the run
> file, never only in the rc file.**

A run file must be self-contained: handing it to another user on
another machine reproduces the same result.

---

## 8. Testing Strategy

| Directory | Scope |
| --- | --- |
| `tests/unit/` | Pure functions, against closed-form oracles |
| `tests/integration/` | Stages together, or a whole run from a file |
| `tests/regression/` | Whole runs against stored reference output |

Every numerical tolerance is **derived and justified**, not tuned,
with the reasoning in a comment beside it. Mechanically checkable
rules are tested rather than left to discipline: the installed-copy
guarantee of Section 9 (`tests/unit/test_installed_copy.py`) and,
once the module map exists, the import rule of Section 4.

---

## 9. Build System: The Two Ways In

Python 3.10 or later, NumPy-based numerical core, vedo/VTK rendering.
The tool reaches a user in two ways that run the same code (Section
6).

**Route A: the `physdemo` suite, for a shared computer.** The tool
is one member of the suite (`github.com/UMKC-CPG/physdemo`): a set
of course demonstration tools that share one Python environment and
one `bin/` directory of commands. One person installs the suite;
everyone else only sources its `activate.sh`. The tool is *linked*,
never copied and never pip-installed into the suite, so a clone
stays live. The suite's contract (its `dev/ARCHITECTURE.md` section
4) says what this repository must do to be linked, and
`physdemo-check-tool .` verifies it.

**Route B: `pip install`, for a personal computer.** The tool
installs like any Python package, with its dependencies, into an
environment the user makes:

```
python -m venv physdemo
source physdemo/bin/activate        (Windows: physdemo\Scripts\activate)
pip install https://github.com/UMKC-CPG/rotating_frame/archive/refs/heads/main.zip
rfsim --check
```

This is why everything the tool needs at run time is inside the
package (Section 1), and why `pyproject.toml` **declares the
dependencies**: on this route nobody else will supply them.

**Who owns the versions.** The suite's `requirements.in` is the
single statement of what the course tools need; `pyproject.toml`
repeats the subset this tool imports, with lower bounds no tighter
than the suite's. A dependency this tool needs and the suite lacks is
added to the suite first.

**Offscreen drawing** (`--offscreen --frames N`, `--check`, the
tests) chooses VTK's window class by the suite's rule: EGL on Linux
whenever offscreen drawing is asked for, nothing on macOS or Windows
(`render/offscreen.py`).

**What has been tried.** Nothing yet on this tool; the skeleton it
came from was tested on Linux on both routes.

---

## 10. Development Checkpoints

<!-- Tagged baselines as each level is first considered complete:
v0.1-vision, v0.2-architecture, v0.3-design, v0.4-pseudocode, then
the milestones of the tool. -->
