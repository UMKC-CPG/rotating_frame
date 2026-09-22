# Spikes

Throwaway experiments kept because their *results* are cited in the
design chain. A spike is not production code and is not held to the
architecture: it exists to answer one question, and it stays in the
repository only so that the answer can be re-checked when the
libraries, the formulas, or the conventions change.

Run every spike from the repository root inside the shared
environment (`sdemo`; ARCHITECTURE 9.2).

Give each spike an entry here recording: the question it answered,
the answer, where in the chain that answer is now cited, any trap it
guards against, and the exact command to re-run it.

---

## `drop_deflection.py`

**Question it answered:** does the frame-fixed closed form of design
4.2, carried into the rotating frame by the transform of design 1.3,
reproduce the textbook eastward deflection of a dropped stone,
`d = (1/3) g Ω t³ cos λ`, and by how much does the exact answer under
the uniform approximation differ from that first-order formula?

**Answer:** yes; the exact landing offset is the textbook value times
`1 − Ω² R_E / g₀ = 0.99655`, to six figures, at latitudes from 10° to
80° and drop heights of 100 m and 1000 m. The factor is independent
of latitude because the weaker effective gravity contributes
`(1 − Ω² R_E cos² λ / g₀)` and the plumb line's tilt contributes
`(1 − Ω² R_E sin² λ / g₀)`. The northward offset is second order,
below `10⁻⁵` relative.

**Where it is cited:** design 4.6, which sets the drop oracle's
tolerance from it; design 3.4.1 for the plumb line.

**The trap it guards against:** comparing the tool with the textbook
formula at a tolerance tighter than `3.5 × 10⁻³` would fail for a
correct tool, and loosening the tolerance until it passed would hide
a real sign error of the same size.

```bash
dev/spikes/drop_deflection.py
```
