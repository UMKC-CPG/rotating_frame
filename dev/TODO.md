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

- [x] (A9) Replace the placeholder run in `README.md` ("What It Will
      Do") once VISION is ratified. (Done 2026-09-23 with section 10.)

---

## DESIGN

(none)

---

## PSEUDOCODE

(none)

---

## CODE

- [x] (P10.6, src/rotating_frame/core/motion.py) Delete the placeholder
      physics, its example, and `tests/unit/test_motion.py` when
      section 10 is coded; the examples of D8.1 replace the example.
      (Done 2026-09-23 with section 10.)
- [x] (P9.5, render/vedo_renderer.py) The legend is right-justified
      by vedo's corner placement and its background is translucent;
      left-justify it at a fixed offset and make the background
      opaque. (Done 2026-09-23.)
- [x] (P9.3, render/scene_description.py) At a landing, where the
      arrows are short and share a base, their 3D labels collide;
      `spread_labels` nudges them apart along the view's up. (Done
      2026-09-23.)
- [x] (tests/integration/test_session.py) The run-control tests each
      build a store; share one built store per run across the tests.
      (Done 2026-09-23.)
- [x] (P1–P10) Code, in the checkpoint order of ARCHITECTURE 10:
      `v0.5-motion` (P1–P6 and the store's physics half), `v0.6-scene`
      (P8, P9, P10 with the turntable and merry-go-round runs),
      `v0.7-earth` (the Earth presets, the drop, the projectile, the
      ring). (Tagged 2026-09-23.)
- [ ] (A10) `v1.0-classroom`: usable in a graduate mechanics course.
      Needs a session in a real window on Hellbender and on a laptop
      (the keys, the slider, the timer), the Earth runs judged by the
      instructor, and a `site/` note with measured frame rates.

---

## ARCHIVE

- [x] Generated from the physdemo member-tool skeleton; both routes,
      the self-check, and the tests work on the placeholder.
- [x] (V1–V6) `dev/VISION.md` written and ratified 2026-09-22; tagged
      `v0.1-vision`.
- [x] (A2–A6) `dev/ARCHITECTURE.md` written and ratified 2026-09-22;
      tagged `v0.2-architecture`.
- [x] (D1–D10) The ten design sections written, refined (eleven
      findings, ten applied), and ratified 2026-09-22; tagged
      `v0.3-design`.
- [x] (D10) Done in design 10.5: the key bindings follow the scattering
      tool's scheme (design 12.15 there), every key a Ctrl chord matched
      case-sensitively with a legend in the window; the shared
      vocabulary carried over, the rigid-body tool's display toggles as
      the model for what is drawn, and this tool's own chords for the
      view, the terms, and the check overlay.
- [x] (P1–P10) The ten pseudocode sections written, refined (ten
      findings, all applied), and ratified 2026-09-22; tagged
      `v0.4-pseudocode`.
