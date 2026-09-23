# Site notes

What is true of one computer and not of the tool. Nothing outside
this directory may name a machine (physdemo contract C10).

## Frame rates

The window's top-left readout ends with a line `drawing R frames/s
(M ms per frame)`, measured over the last thirty redraws, so the
number below is read off the screen and not guessed. A tick is asked
for every 33 ms; the rate is set by the redraw. One redraw is: the
scene description (a few milliseconds), the dynamic actors (tens of
milliseconds), and the OpenGL render, which on a real GPU is a few
milliseconds and on software OpenGL is set by the window's pixels.
The plotted panels are drawn once per run and kept, so the strip
costs nothing per frame after the first.

| computer | window | frames/s | date |
| --- | --- | --- | --- |
| Hellbender login node, offscreen, software GL | 1280 × 800 | 3 | 2026-09-23 |
| the same | 640 × 400 | 6 | 2026-09-23 |
| instructor's laptop, Windows, a window | 1280 × 800 | 5 | 2026-09-23 |

On software OpenGL the window size in `rfsimrc.py` is the lever:
the render time scales with the number of pixels.

The laptop's 5 frames/s (2026-09-23, before the actor pool) split
as describe 5, panels 0, actors 90, render 25 ms: the actors, rebuilt
every frame, were the cost, and the rest of the 200 ms was the timer
waiting for its next tick after a slow handler. The renderer now
keeps its dynamic actors between frames and only places them
(pseudocode 9.5); offscreen here that took the actors from 84 ms to
15 ms on the Earth throw and 21 ms on the thirteen-particle
turntable. Record the laptop's reading after the change below.

| computer | window | frames/s | date |
| --- | --- | --- | --- |
| the laptop, Windows, with the actor pool | 1280 × 800 | (from the readout) | |
