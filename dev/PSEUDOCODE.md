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
     `defaults/rfsimrc.py`, `pyproject.toml` (`cli/rfsim.py` is now
     section 10's).
   - *Placeholders, replace under this tool's own sections:*
     `core/motion.py`, `examples/circle.toml`,
     `tests/unit/test_motion.py`,
     `tests/integration/test_rfsim_cli.py`.
   Suite section 4. *inherited*

1. [`pseudocode/01-frame-and-transform.md`](
   pseudocode/01-frame-and-transform.md) — governs `core/frame.py`
   and `tests/unit/test_frame.py`: the `Frame`, Rodrigues' rotation,
   the transforms, the launch conversion, the triads. Design 1.
   *implemented*
2. [`pseudocode/02-natural-units-and-presets.md`](
   pseudocode/02-natural-units-and-presets.md) — governs
   `core/natural_units.py`, `core/units.py`, `core/presets.py`, and
   their tests: the scales, the pint boundary, the three presets,
   the launch point and the local axes. Design 2. *reviewed*
3. [`pseudocode/03-force-fields.md`](pseudocode/03-force-fields.md)
   — governs `forces/force_interface.py`, `forces/fields.py`, and
   `tests/unit/test_fields.py`: the contract, the three members,
   `make_field`, the approximation note. Design 3. *reviewed*
4. [`pseudocode/04-motion-and-stopping.md`](
   pseudocode/04-motion-and-stopping.md) — governs
   `motion/closed_forms.py`, `motion/equations_of_motion.py`,
   `motion/integrators.py`, `motion/stopping.py`,
   `motion/motion_provider.py`, and their tests, with the drop
   oracle as an integration test. Design 4. *reviewed*
5. [`pseudocode/05-pseudo-forces.md`](pseudocode/05-pseudo-forces.md)
   — governs `pseudoforces/terms.py`, `tests/unit/test_terms.py`, and
   `tests/integration/test_closure.py`: `terms`, `stacked`, `total`,
   the sign checks, the closure test. Design 5. *reviewed*
6. [`pseudocode/06-check-and-error-budget.md`](
   pseudocode/06-check-and-error-budget.md) — governs
   `analysis/comparison.py`, `analysis/ghost_path.py`,
   `analysis/conservation_monitor.py`,
   `analysis/closed_form_deflections.py`, `analysis/error_budget.py`,
   and their tests. Design 6. *reviewed*
7. [`pseudocode/07-launches-and-the-ring.md`](
   pseudocode/07-launches-and-the-ring.md) — governs
   `launch/launch_spec.py`, `launch/ring.py`, and
   `tests/unit/test_launch.py`: `LaunchSpec`, `resolve_launch`,
   `expand_ring`, the physical refusals. Design 7. *reviewed*
8. [`pseudocode/08-run-file.md`](pseudocode/08-run-file.md) —
   governs `run/schema.py`, `run/rc.py`, `run/run_spec.py`,
   `run/serialization.py`, `run/results_store.py`, `run/driver.py`,
   `tests/unit/test_architecture.py`, and the other tests it names;
   replaces the placeholder `run/run_file.py`. Design 8. *reviewed*
9. [`pseudocode/09-scene-and-geometry.md`](
   pseudocode/09-scene-and-geometry.md) — governs `geometry/`,
   `render/scene_description.py`, `render/palettes.py`,
   `render/vedo_renderer.py`, `render/panels.py`, and their tests;
   replaces the placeholder `render/palettes.py` and
   `render/vedo_renderer.py`. Design 9. *reviewed*
10. [`pseudocode/10-scrubber-and-session.md`](
    pseudocode/10-scrubber-and-session.md) — governs `ui/`,
    `cli/rfsim.py` (taken over from row 0), and their tests; replaces
    the placeholder `tests/integration/test_rfsim_cli.py`; deletes
    `core/motion.py`, `examples/circle.toml`, and
    `tests/unit/test_motion.py` when coded. Design 10. *reviewed*

<!-- When a placeholder file is replaced, move its name from row 0
to the row that now governs it, in the same edit. -->

Status is one of: planned, draft, reviewed, implemented, superseded,
inherited. All ten sections were reviewed together and ratified on
2026-09-22 (`v0.4-pseudocode`); a section becomes *implemented* when
its code and tests exist and pass.

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
