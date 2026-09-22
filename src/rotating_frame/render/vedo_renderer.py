"""The scene: a trail and a glyph, drawn with vedo (physdemo
PSEUDOCODE 4.6). PLACEHOLDER: a tool replaces this with its own
renderer under its own DESIGN, keeping the two rules that the
skeleton's tests rely on. First, this is the only module that imports
vedo, so that everything else can be imported on a computer that
cannot draw. Second, `screenshot(as_array=True)` returns the
framebuffer, because a picture that was actually drawn is the only
evidence that drawing works (physdemo VISION P4).

Attribution: this module is part of the Rotating Frame teaching tool.
"""

import vedo

from rotating_frame.render.palettes import PALETTES


class TrailRenderer:
    """Draw the samples of a motion as a trail with a glyph at the
    current sample. `window_size` is (width, height) in pixels;
    `offscreen=True` draws to memory and never opens a window."""

    def __init__(self, palette_name, window_size, offscreen=False,
                 glyph_radius=0.05, title='rfsim'):
        self.colors = PALETTES[palette_name]
        self.glyph_radius = glyph_radius
        self.plotter = vedo.Plotter(offscreen=offscreen,
                                    size=tuple(window_size), axes=1,
                                    title=title)
        self.plotter.background(self.colors['background'])
        self._actors = []
        self._shown = False

    def show_samples(self, samples, upto):
        """Draw the trail through samples 0..upto and the glyph at
        sample `upto`, replacing what was drawn before."""
        trail = vedo.Line(samples[:upto + 1]).c(self.colors['trail'])
        glyph = vedo.Sphere(pos=samples[upto], r=self.glyph_radius,
                            res=24).c(self.colors['glyph'])
        self.plotter.remove(*self._actors)
        self._actors = [trail, glyph]
        self.plotter.add(*self._actors)
        if not self._shown:
            # The first show creates the window (or the offscreen
            # buffer); after that, render() redraws in place.
            self.plotter.show(interactive=False)
            self._shown = True
        self.plotter.render()

    def run(self, samples, frames=0):
        """`frames == 0`: draw the whole trail and hand the window to
        the user until it is closed. Otherwise draw `frames` frames,
        one sample further each time, and return."""
        if frames == 0:
            self.show_samples(samples, len(samples) - 1)
            self.plotter.show(interactive=True)
            return
        for index in range(min(frames, len(samples))):
            self.show_samples(samples, index)

    def screenshot(self, path=None, as_array=False):
        """Write the current frame to `path`, or return it as an
        array of shape (height, width, 3) when `as_array` is set."""
        if as_array:
            return self.plotter.screenshot(asarray=True)
        self.plotter.screenshot(str(path))
        return None

    def close(self):
        self.plotter.close()
