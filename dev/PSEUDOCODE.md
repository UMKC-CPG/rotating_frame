# Pseudocode — Index

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. For the rationale behind these algorithms
> see the corresponding section under `design/`.

---

**This file is an index, not the pseudocode.** Each numbered section
lives in its own file under `dev/pseudocode/`. Read this table to
find the section you need, then read only that file.

**This is the gate.** No file under `src/` is edited until the
governing section here exists and already describes the change. See
"Chain Discipline" in `../CLAUDE.md`. When beginning a coded task,
name the section from this table that governs it.

## Sections

Each entry: number, file, what it governs under `src/rotating_frame/`, the
design section it implements, status.

0. **Inherited from the physdemo suite** (its `dev/PSEUDOCODE.md`
   section 4; `github.com/UMKC-CPG/physdemo`). Three kinds of file:
   - *Keep, and change only in the suite first:*
     `src/scripts/rfsim.py`, `cli/support.py`,
     `render/offscreen.py`, `defaults/__init__.py`,
     `examples/__init__.py`, `tests/conftest.py`,
     `tests/unit/test_installed_copy.py`,
     `tests/unit/test_offscreen.py`.
   - *Extend under this tool's own section when it arrives:*
     `cli/rfsim.py`, `defaults/rfsimrc.py`, `pyproject.toml`.
   - *Placeholders, replace under this tool's own sections:*
     `core/motion.py`, `run/run_file.py`, `render/palettes.py`,
     `render/vedo_renderer.py`, `examples/circle.toml`,
     `tests/unit/test_motion.py`,
     `tests/integration/test_rfsim_cli.py`.
   Suite section 4. *inherited*

1. [`pseudocode/01-frame-and-transform.md`](
   pseudocode/01-frame-and-transform.md) — governs `core/frame.py`
   and `tests/unit/test_frame.py`: the `Frame`, Rodrigues' rotation,
   the transforms, the launch conversion, the triads. Design 1.
   *draft*

<!-- When a placeholder file is replaced, move its name from row 0
to the row that now governs it, in the same edit. -->

Status is one of: planned, draft, reviewed, implemented, superseded,
inherited.

## Conventions

**Section numbers track DESIGN where they can.** Pseudocode section N
implements design section N by default. Where one design section
needs several algorithms, use N.1, N.2 rather than breaking the
correspondence, and say so in the Design column.

**Use the names the code will use.** The variable names here should
be the ones that appear in `src/`, following the naming rules in
`../CLAUDE.md`. Pseudocode that renames everything cannot be checked
against the implementation by eye, which is the whole point of it.

**Language-agnostic, but concrete.** No language syntax, but no
hand-waving either: loop bounds, index origins, allocation, and error
paths are all specified. "Compute the overlap" is not pseudocode.

**Never edit upward to match code.** A disagreement between this
document and the source means the source is wrong, unless the source
has first been verified against DESIGN. See `../CLAUDE.md`.
