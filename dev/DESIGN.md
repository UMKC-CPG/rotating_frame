# Design — Index

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. For goals and principles see `VISION.md`; for
> the module map and the boundaries see `ARCHITECTURE.md`.
> Principles are cited as `P<n>`, goals as `G<n>`, architecture
> sections as `A<n>`.

---

**This file is an index, not the design.** Each numbered section
lives in its own file under `dev/design/`. Read this table to find
the section you need, then read only that file.

## Sections

Each entry: number, file, topic, status.

<!-- SKELETON: no sections yet. The skeleton's placeholder physics,
run-file schema, and renderer are governed by the suite's
PSEUDOCODE 4 (see PSEUDOCODE.md row 0) and need no design section
here; the tool's first section is number 1. -->

Status is one of: planned, draft, reviewed, implemented, superseded.
A superseded section keeps its number and file; its header names the
replacement. Numbers are never reused.

## Conventions

**Numbering is stable.** Sections are cited by number from
PSEUDOCODE, from TODO, and from source comments. Append rather than
renumber.

**One topic per file.** A section file passing roughly 1,500 lines is
describing more than one thing; split it and add the row.

**Cite upward.** A design choice forced by a VISION principle names
it; one forced by an architectural boundary names the section.

**Record what was rejected.** The alternative that was considered and
dropped, with the reason, is what stops it being proposed again.

## Notation

Fixed here and used in every section and in PSEUDOCODE.

| Symbol | Meaning |
| --- | --- |
| | (the tool's symbols, once Section 1 exists) |
