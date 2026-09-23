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

The laptop's 5 frames/s, about 200 ms a frame with a GPU, is not the
render: offscreen here the whole frame costs 318 ms of which 210 ms
is software rendering. The frame note now splits the frame into
describe, panels, actors, and render, so the next reading from the
laptop says where its 200 ms go; record the split here.
