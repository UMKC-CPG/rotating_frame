# Design 10: The Scrubber and the Session

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. Implements ARCHITECTURE 3.9 (`ui/`) and the
> session half of 3.10; serves G5 (scrub time both ways), G3 and G1
> (what is shown), P4 (real-time manipulation), P12, and P5. Uses
> Designs 6, 8, and 9. *Status: draft.*

The session owns one number, the sample index, and a handful of
switches, and it turns keystrokes and a slider into changes of them.
This section fixes the two kinds of control and the one rule between
them, the session state, the loop, the time slider, every key chord
and why every key is a chord, the run controls and what they rebuild,
the scripted controls the tests drive, and the invariants.

---

## 10.1 Two kinds of control, one rule

A **viewing control** changes what is shown: the sample, the play
state, the speed, the view, which arrows and paths and panels are
drawn, the palette, the tracked particle, the camera. A **run
control** changes the run: the exaggeration factor, or the check's
substeps. The rule, taken from the scattering tool's design 12.2:

> A run control makes a new store. A viewing control never touches
> the store.

Any sequence of viewing controls leaves the store bit-identical
(Design 8.7). A run control resolves a new `RunSpec` with the one
changed key, rebuilds the store through the driver (Design 8.6),
which for the first version's closed forms takes well under a
second (P4), and keeps every piece of viewing state, clamping the
sample index to the new length. The screen's distortion column shows
the new factor (Design 6.4). There are two run controls and no more:
anything else about a run is edited in the run file, because the run
file is the record (G6), and a control that could change the launch
from the keyboard would leave a student with a picture no file
describes.

## 10.2 The session state

```
  k            sample index, 0 … N−1
  playing      bool
  direction    +1 | −1
  rate         samples per tick: 1, 2, 4, 8, 16
  loop         bool: at the end, wrap instead of stopping
  view         "both" | "inertial" | "rotating"
  arrows       set of {"true", "centrifugal", "coriolis", "euler",
               "sum", "velocity"}
  paths        set of {"check", "ghost", "overlay"}
  scenery      set of {"triads", "stage"}
  panels       bool: the panel strip
  legend       bool
  palette      "light" | "dark" | "colorblind"
  tracked      particle index
  camera_mode  "follow" | "fixed"        (Design 9.1)
  arrow_mode   "auto" | "same"           (Design 9.4)
```

The initial state comes from the run file's `[view]` table (Design
8.1), so a classroom setup opens as saved; `Ctrl+w` writes the
current viewing state back into the resolved run file (Design 8.4).
The state is a plain object with pure transition functions
(`ui/session_state.py`), testable without a window.

## 10.3 The loop

vedo's timer fires at a fixed tick, thirty times a second. On each
tick, if playing, `k` advances by `direction × rate`; at either end
it stops, or wraps when `loop` is set. Whenever `k` or a switch has
changed since the last tick, the per-sample drawables of both views
are rebuilt from the store (Design 9.2) and the window is rendered;
otherwise nothing is done, so an idle window costs nothing. Keys
arrive through vedo's key callback, the slider through its own, and
both go through one dispatcher: a chord or a slider position becomes
a named command, and the command becomes a state transition. A
scripted controls source (10.6) feeds the same dispatcher.

**Pacing is by samples, not by wall time.** A tick advances a fixed
number of samples, so a run plays at the same speed on a fast machine
and a slow one, and `rate` is what a student changes to see a flight
slowly. The clock on screen shows `t̃_k`, never the wall clock.

## 10.4 The time slider

A slider along the bottom of the window (vedo's, the one widget that
can share the scene), from sample `0` to `N−1`, whose handle follows
`k` while playing and sets `k` when dragged, pausing playback. Its
labels show `t̃` at the ends and `t_k` in the preset's units at the
handle. Dragging it is a viewing control and yields the same state
as the equivalent sequence of steps (10.7). Reverse scrubbing is
exact because every sample is stored (G5, Design 4.3).

## 10.5 The key chords

**Every key is a Ctrl chord.** vedo binds the plain letters to its
own viewer actions (`r` resets the camera, `s` and `w` change the
surface style, and more), and the rigid-body and scattering tools
both learned that a plain-key binding of the tool's own is shadowed
by one of vedo's sooner or later. Keys arrive from vedo already
prefixed (`Ctrl+s`, `Ctrl+minus`, `Ctrl+space`) and are matched
case-sensitively, because Shift changes the key symbol: `Ctrl+S` is
Ctrl+Shift+s, which is how step back is reached from step forward.
The legend in the window (`Ctrl+h`) lists every chord, so nothing
needs memorizing (P5).

**Shared with the scattering tool**, same chord, same meaning:

| Chord | Command |
| --- | --- |
| `Ctrl+space` | play / pause |
| `Ctrl+s`, `Ctrl+S` | one sample forward / back, then pause |
| `Ctrl+plus`, `Ctrl+minus` | rate × 2 (to 16) / rate ÷ 2 (to 1) |
| `Ctrl+n` | rate 1 |
| `Ctrl+r` | reverse direction |
| `Ctrl+Home`, `Ctrl+End` | first sample / last sample |
| `Ctrl+l` | toggle loop at the end |
| `Ctrl+Tab` | next tracked particle |
| `Ctrl+a` | toggle all arrows |
| `Ctrl+c` | cycle the palette |
| `Ctrl+w` | write the resolved run file, with the view |
| `Ctrl+h` | hide / show the legend |
| `Ctrl+q` (and `q`) | quit |

**This tool's own:**

| Chord | Command |
| --- | --- |
| `Ctrl+v` | cycle the view: both, inertial, rotating |
| `Ctrl+1` … `Ctrl+6` | toggle one arrow: true force, centrifugal, |
| | Coriolis, Euler, sum, velocity |
| `Ctrl+g` | toggle the ghost path |
| `Ctrl+k` | toggle the check's path |
| `Ctrl+o` | toggle the first-order overlay (where offered) |
| `Ctrl+t` | toggle the triads |
| `Ctrl+d` | toggle the stage (disc, platform, or ground) |
| `Ctrl+f` | camera: follow P / fixed |
| `Ctrl+m` | arrow scales: auto / same |
| `Ctrl+p` | hide / show the panel strip |
| `Ctrl+e` | jump to the tracked particle's stop event |
| `Ctrl+0` | restore the run file's cameras |
| `Ctrl+bracketright`, `Ctrl+bracketleft` | exaggeration × 2 / ÷ 2 |
| | (a run control) |
| `Ctrl+period`, `Ctrl+comma` | check substeps × 2 / ÷ 2 (a run |
| | control) |

The rigid-body tool's display toggles (its body, ellipsoid, vectors,
and triads) are the model for `Ctrl+1` … `Ctrl+6`, `Ctrl+t`, and
`Ctrl+d`. Where a chord exists in the scattering tool with another
meaning (`Ctrl+e`, `Ctrl+p`, `Ctrl+d`, `Ctrl+m`, `Ctrl+comma`,
`Ctrl+period`, `Ctrl+bracketleft`, `Ctrl+bracketright`), the
meanings are that tool's own subject and this one's, and the legend
is what a student reads; the shared table above is what stays fixed
across the suite.

## 10.6 Scripted controls, `--frames`, and `--script`

A scripted controls source replaces the window's keys and slider
with a list of `(tick, command)` pairs and a frame count, for the
tests, for `--check`, and for `--offscreen --frames N --script
"tick:command,..."`. It feeds the same dispatcher with the same
command names, so a test drives every command a student can and the
offscreen capture of Design 9.8 exercises the loop as the window
does. `--frames N` alone plays `N` ticks from the initial state.

## 10.7 Invariants and verification

- **Viewing controls never touch the store**: a scripted session
  that issues every viewing command, in a scrambled order, on every
  packaged run leaves the store's checksum unchanged (Design 8.7).
- **A run control makes a new store and keeps the view**:
  `Ctrl+bracketright` doubles `α` in the new spec, the new store's
  `Ω` is doubled, `k` and every switch survive, and the distortion
  column reads the new factor; `Ctrl+period` doubles the check's
  substeps and reduces `δ̃` by about sixteen (Design 6.6) while
  leaving the exact arrays identical to the old store's.
- The state machine, without a window: play then pause leaves `k`;
  step forward then back returns `k`; reverse then step moves the
  other way; at the last sample with `loop` off, a tick stops
  playback and `k` stays; with `loop` on, `k` wraps to `0`; rate
  saturates at `1` and `16`; every toggle is its own inverse.
- Every chord in 10.5 maps to a command and every command appears
  in the legend; no plain letter is bound except `q`.
- Dragging the slider to sample `k` yields the same state as `Ctrl+
  Home` followed by `k` steps.
- `Ctrl+v` changes the number of sub-renderers as Design 9.8 says;
  `Ctrl+f` changes the inertial camera's target from `R(t̃_k) r̃_P`
  to `r̃_P` at `t̃ = 0`, which a scene-description test reads.
- `Ctrl+e` sets `k` to the tracked particle's stop index, or to
  `N−1` when it has none, and `Ctrl+Tab` wraps around the ring.
- `Ctrl+w` writes a file that loads to the current spec with the
  current viewing state in its `[view]` table.
- `--script "5:play_pause,20:reverse,40:play_pause"` offscreen
  produces the frames the state machine predicts, checked by the
  session's `k` after each tick.

## 10.8 Rejected

- **Plain keys.** Shadowed by vedo's own bindings; both older tools
  moved to chords for this reason.
- **Live editing of the launch or the rate from the keyboard.** A
  picture no run file describes cannot be reproduced (G6). The two
  run controls are the ones whose result the screen labels.
- **An "exaggerate the deflection" control.** The deflection is not
  a thing apart from the physics (Design 2.6); exaggerating `Ω` is,
  and it is labeled.
- **Wall-clock pacing.** It would make a run play differently on
  different machines and make "slow motion" a property of the
  computer.

## Sources

The controls split, the loop, and the slider follow the scattering
tool's design 12.2 to 12.4 and its `ui/controls.py` (design 12.15,
the chord rule); the display toggles follow the rigid-body tool's
design 15.7.
