# Task List

> **Document hierarchy:** this is a work queue, not a level of the
> chain. Tasks are organized by the level they affect, and each item
> cites the document section it touches.

---

## How to write an entry

```
- [ ] (D3.2) One-line statement of what must be true when done.
      Any constraint or gotcha the doer needs. Blocked by: (P1.4).
```

The leading tag is the citation: `V4` for VISION section 4, `A2` for
ARCHITECTURE 2, `D3.2` for design section 3.2, `P1.4` for pseudocode
1.4, and a path for code. An entry with no citation is an entry
nobody can check against anything.

**Keep entries short on purpose.** When a task's plan grows detailed
enough to implement from, naming the functions, the files, and the
call sequence, that specificity belongs in a `pseudocode/` section,
not here. A detailed TODO entry looks like a specification and is
not one: `/refine` never checks it against DESIGN, and once its box
is ticked nobody reads it again. Move the detail up and leave the
entry pointing at the section.

Completed items move to ARCHIVE with a `- [x]`, keeping their
numbering so older cross-references still resolve.

---

## VISION

(none)

---

## ARCHITECTURE

- [ ] (A2–A5) The structural idea, the module map, the dependency
      graph, and the boundaries, from VISION. Tag `v0.2-architecture`.
- [ ] (A9) Replace the placeholder run in `README.md` ("What It Will
      Do") once VISION is ratified.

---

## DESIGN

- [ ] (D1) The first design section, and the notation table.

---

## PSEUDOCODE

- [ ] (P1) The first pseudocode section. Move the placeholder files
      it replaces out of row 0.

---

## CODE

- [ ] (src/rotating_frame/core/motion.py) Replace the placeholder physics
      after P1 exists; delete `tests/unit/test_motion.py` with it.

---

## ARCHIVE

- [x] (V1–V6) `dev/VISION.md` written and ratified 2026-09-22;
      tagged `v0.1-vision`.
- [x] Generated from the physdemo member-tool skeleton; both routes,
      the self-check, and the tests work on the placeholder.
