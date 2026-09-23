"""The two views realized with vedo, the only module that imports it
(pseudocode 9.5; design 9.1 and 9.2; ARCHITECTURE 6.5).

One vedo window holds one or two sub-renderers side by side, with
unshared cameras, and, when panels are shown, a strip along the
bottom that holds their images under a flat camera. The renderer
keeps the static actors of each view between frames and replaces the
dynamic ones, so that a change of sample rebuilds only what moved.
It offers the session the hooks it needs: the slider, the key
callback, the timer that counts ticks, the blocking interactive
loop, the screenshot, and close.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np
import vedo

from rotating_frame.render.palettes import color
from rotating_frame.render.scene_description import (Arrow, Glyph, Image,
                                                     Polyline, Surface,
                                                     Text, Triad)

PANEL_STRIP_FRACTION = 0.28      # of the window's height
TEXT_POSITIONS = {'top_left': 'top-left', 'top_right': 'top-right',
                  'bottom_left': 'bottom-left',
                  'bottom_right': 'bottom-right'}


def _layout(n_views, with_panels):
    """The sub-renderers as vedo's custom shapes: the views across the
    top, and the panel strip along the bottom when asked for."""
    top = PANEL_STRIP_FRACTION if with_panels else 0.0
    shape = []
    for index in range(n_views):
        left = index / n_views
        right = (index + 1) / n_views
        shape.append({'bottomleft': (left, top), 'topright': (right, 1.0)})
    if with_panels:
        shape.append({'bottomleft': (0.0, 0.0), 'topright': (1.0, top)})
    return shape


def build_actor(drawable, palette_name):
    """The vedo objects that realize one drawable."""
    tint = lambda role: color(palette_name, role)      # noqa: E731
    if isinstance(drawable, Polyline):
        points = np.asarray(drawable.points, dtype=float)
        if len(points) < 2:
            points = np.vstack((points, points))
        if drawable.style == 'dashed':
            actor = vedo.DashedLine(points, spacing=0.4,
                                    c=tint(drawable.role),
                                    lw=drawable.width)
        elif drawable.style == 'dotted':
            actor = vedo.DashedLine(points, spacing=0.15,
                                    c=tint(drawable.role),
                                    lw=drawable.width)
        else:
            actor = vedo.Line(points).c(tint(drawable.role)).lw(
                drawable.width)
        actors = [actor]
        if drawable.label:
            actors.append(vedo.Text3D(drawable.label, pos=points[-1],
                                      s=0.03, c=tint('text')))
        return actors
    if isinstance(drawable, Arrow):
        actor = vedo.Arrow(drawable.base, drawable.tip, s=0.004,
                           c=tint(drawable.role))
        label = vedo.Text3D(drawable.label, pos=drawable.tip, s=0.03,
                            c=tint(drawable.role))
        return [actor, label]
    if isinstance(drawable, Glyph):
        actors = [vedo.Sphere(pos=drawable.center, r=drawable.radius,
                              res=16).c(tint(drawable.role))]
        if drawable.label:
            actors.append(vedo.Text3D(drawable.label, pos=drawable.center,
                                      s=0.03, c=tint('text')))
        return actors
    if isinstance(drawable, Triad):
        actors = []
        for column, label in zip(drawable.axes.T, drawable.labels):
            tip = drawable.origin + column
            actors.append(vedo.Arrow(drawable.origin, tip, s=0.003,
                                     c=tint(drawable.role)))
            actors.append(vedo.Text3D(label, pos=tip, s=0.04,
                                      c=tint(drawable.role)))
        return actors
    if isinstance(drawable, Surface):
        mesh = vedo.Mesh([drawable.points, drawable.faces]).c(
            tint(drawable.role)).alpha(0.5)
        actors = [mesh]
        for marking in drawable.markings:
            actors += build_actor(marking, palette_name)
        for point, text in drawable.labels:
            actors.append(vedo.Text3D(text, pos=point, s=0.05,
                                      c=tint('stage_marks')))
        return actors
    if isinstance(drawable, Text):
        return [vedo.Text2D('\n'.join(drawable.lines),
                            pos=TEXT_POSITIONS[drawable.corner], s=0.6,
                            c=tint(drawable.role), alpha=0.9)]
    if isinstance(drawable, Image):
        return [vedo.Image(drawable.rgb)]
    raise TypeError(f'no actor for {type(drawable).__name__}')


class TwoViewRenderer:
    """The window: one or two views and, optionally, the panel strip."""

    def __init__(self, window_size, offscreen, n_views, palette_name,
                 title='rfsim', with_panels=False):
        self.n_views = n_views
        self.with_panels = with_panels
        self.palette_name = palette_name
        self.offscreen = offscreen
        self.plotter = vedo.Plotter(shape=_layout(n_views, with_panels),
                                    size=tuple(window_size),
                                    offscreen=offscreen, sharecam=False,
                                    title=title)
        self.static_actors = {}          # view index -> list
        self.static_signature = {}       # view index -> what was built
        self.dynamic_actors = {}
        self.panel_actors = []
        self.slider = None
        self.tick_count = 0
        self.shown = False
        self._apply_background()

    def _apply_background(self):
        background = color(self.palette_name, 'background')
        for index in range(self.n_views + (1 if self.with_panels else 0)):
            self.plotter.at(index).background(background)

    def realize(self, scenes, palette_name, panel_images=()):
        """Draw the scenes; panel images, if any, go in the strip."""
        if palette_name != self.palette_name:
            self.palette_name = palette_name
            self.static_signature = {}
            self._apply_background()
        for index, scene in enumerate(scenes):
            view = self.plotter.at(index)
            signature = (scene.view, len(scene.static),
                         tuple(type(d).__name__ for d in scene.static))
            if self.static_signature.get(index) != signature:
                view.remove(*self.static_actors.get(index, []))
                self.static_actors[index] = [
                    actor for drawable in scene.static
                    for actor in build_actor(drawable, palette_name)]
                view.add(*self.static_actors[index])
                self.static_signature[index] = signature
            view.remove(*self.dynamic_actors.get(index, []))
            self.dynamic_actors[index] = [
                actor for drawable in scene.dynamic
                for actor in build_actor(drawable, palette_name)]
            view.add(*self.dynamic_actors[index])
        if self.with_panels:
            self._place_panels(panel_images)
        if not self.shown:
            self.plotter.show(interactive=False, resetcam=False)
            self.shown = True
        self.plotter.render()

    def _place_panels(self, images):
        strip = self.plotter.at(self.n_views)
        strip.remove(*self.panel_actors)
        self.panel_actors = []
        x = 0.0
        height = 0
        for rgb in images:
            image = vedo.Image(rgb)
            image.pos(x, 0.0, 0.0)
            self.panel_actors.append(image)
            x += rgb.shape[1] + 20
            height = max(height, rgb.shape[0])
        if self.panel_actors:
            strip.add(*self.panel_actors)
            camera = strip.camera
            camera.ParallelProjectionOn()
            camera.SetFocalPoint(x / 2.0, height / 2.0, 0.0)
            camera.SetPosition(x / 2.0, height / 2.0, 1000.0)
            camera.SetViewUp(0.0, 1.0, 0.0)
            camera.SetParallelScale(0.55 * height)

    def set_camera(self, view_index, camera, info):
        """Place the view's camera by azimuth, elevation, and distance
        in the scene's local basis, looking at the origin (the camera
        target, to which every point is relative)."""
        azimuth = np.radians(camera['azimuth_deg'])
        elevation = np.radians(camera['elevation_deg'])
        distance = camera['distance'] * info.extent
        east, north, up = info.camera_basis.T
        direction = (np.cos(elevation) * np.cos(azimuth) * east
                     + np.cos(elevation) * np.sin(azimuth) * north
                     + np.sin(elevation) * up)
        vtk_camera = self.plotter.at(view_index).camera
        vtk_camera.SetFocalPoint(0.0, 0.0, 0.0)
        vtk_camera.SetPosition(*(distance * direction))
        vtk_camera.SetViewUp(*up)
        self.plotter.at(view_index).renderer.ResetCameraClippingRange()

    def add_slider(self, callback, n_samples):
        """The time slider along the bottom of the first view."""
        def on_slide(widget, event):
            callback(widget.value)
        self.slider = self.plotter.at(0).add_slider(
            on_slide, 0, max(n_samples - 1, 1), value=0, pos=[(0.05, 0.06),
                                                              (0.45, 0.06)],
            title='sample')
        return self.slider

    def set_slider(self, value):
        if self.slider is not None:
            self.slider.value = value

    def on_key(self, handler):
        def on_press(event):
            if event.keypress:
                handler(event.keypress)
        self.plotter.add_callback('KeyPress', on_press)

    def on_tick(self, handler, milliseconds):
        """Call `handler(tick)` from vedo's timer, counting from zero."""
        def on_timer(event):
            handler(self.tick_count)
            self.tick_count += 1
        self.plotter.add_callback('timer', on_timer)
        self.plotter.timer_callback('start', dt=int(milliseconds))

    def interactive(self):
        self.plotter.interactive()

    def screenshot(self, path=None, as_array=False):
        if as_array:
            return self.plotter.screenshot(asarray=True)
        self.plotter.screenshot(str(path))
        return None

    def close(self):
        self.plotter.close()
