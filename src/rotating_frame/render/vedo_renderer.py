"""The two views realized with vedo, the only module that imports it
(pseudocode 9.5; design 9.1 and 9.2; ARCHITECTURE 6.5).

One vedo window holds three sub-renderers from the start: two views
side by side with unshared cameras, and a strip along the bottom
that holds the panel images under a flat camera. `realize` lays the
viewports out from what it is given, one or two scenes and panel
images or none, so that a change of view or of the panel switch is
a change of viewports and never a new window. The renderer keeps the
static actors of each view between frames and replaces the dynamic
ones, so that a change of sample rebuilds only what moved. It offers
the session the hooks it needs: the slider, the key callback, the
timer that counts ticks, the blocking interactive loop, `stop`, the
screenshot, and close.

vedo's own key table binds Ctrl+w (this tool's save) and Ctrl+q to
closing the window, so vedo's default keyboard callbacks are turned
off before the window is made; the mouse keeps vedo's camera
interaction, which is the interactor style and not a callback.
Offscreen there is no interactor: the slider, the keys, and the
timer are no-ops, and a scripted loop drives the session.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import time

import numpy as np
import vedo

from rotating_frame.render.palettes import color
from rotating_frame.render.panels import PLOT_BOX
from rotating_frame.render.scene_description import (Arrow, Glyph, Image,
                                                     Polyline, Surface,
                                                     Text, Triad)

PANEL_STRIP_FRACTION = 0.28      # of the window's height
ARROW_SHAFT = 0.015              # fractions of the arrow's length
ARROW_HEAD_RADIUS = 0.05
ARROW_HEAD_LENGTH = 0.2
LABEL_SIZE = 0.03                # of the scene's extent
LEGEND_TEXT_SIZE = 0.45
LEGEND_POSITION = (0.5, 0.01)    # window fractions of the view
STRIP_GAP = 20                   # pixels between the strip's images
STRIP_TEXT_WIDTH = 520           # pixels left for the budget text
STRIP_TEXT_SIZE = 0.55
READOUT_TEXT_SIZE = 0.6
TEXT_POSITIONS = {'top_left': 'top-left', 'top_right': 'top-right',
                  'bottom_left': 'bottom-left',
                  'bottom_right': 'bottom-right'}


MAX_VIEWS = 2


def _viewports(n_views, with_panels):
    """The three viewports as (xmin, ymin, xmax, ymax) or None for
    one that is off: the views across the top, the strip along the
    bottom when asked for."""
    top = PANEL_STRIP_FRACTION if with_panels else 0.0
    ports = []
    for index in range(MAX_VIEWS):
        if index < n_views:
            ports.append((index / n_views, top, (index + 1) / n_views,
                          1.0))
        else:
            ports.append(None)
    ports.append((0.0, 0.0, 1.0, top) if with_panels else None)
    return ports


def _initial_shape():
    return [{'bottomleft': (0.0, 0.3), 'topright': (0.5, 1.0)},
            {'bottomleft': (0.5, 0.3), 'topright': (1.0, 1.0)},
            {'bottomleft': (0.0, 0.0), 'topright': (1.0, 0.3)}]


def _label(text, position, size, tint):
    """A 3D label that turns to face the camera. The text is built at
    the origin and moved by its actor's position: vedo bakes `pos`
    into the letters' points, and a camera-following actor turns
    about its own origin, so a label built in place would swing
    around the scene's origin instead of standing at its point."""
    label = vedo.Text3D(text, s=size, c=tint).follow_camera()
    label.actor.SetPosition(*np.asarray(position, dtype=float))
    return label


def _arrow(base, tip, tint):
    """An arrow whose shaft and head scale with its length."""
    return vedo.Arrow(base, tip, shaft_radius=ARROW_SHAFT,
                      head_radius=ARROW_HEAD_RADIUS,
                      head_length=ARROW_HEAD_LENGTH, c=tint)


def build_actor(drawable, palette_name, extent=1.0):
    """The vedo objects that realize one drawable; `extent` sizes
    the labels."""
    tint = lambda role: color(palette_name, role)      # noqa: E731
    label_size = LABEL_SIZE * extent
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
            where = (points[-1] if drawable.label_at is None
                     else drawable.label_at)
            actors.append(_label(drawable.label, where, label_size,
                                 tint('text')))
        return actors
    if isinstance(drawable, Arrow):
        where = (drawable.tip if drawable.label_at is None
                 else drawable.label_at)
        return [_arrow(drawable.base, drawable.tip, tint(drawable.role)),
                _label(drawable.label, where, label_size,
                       tint(drawable.role))]
    if isinstance(drawable, Glyph):
        actors = [vedo.Sphere(pos=drawable.center, r=drawable.radius,
                              res=16).c(tint(drawable.role))]
        if drawable.label:
            actors.append(_label(drawable.label, drawable.center,
                                 label_size, tint('text')))
        return actors
    if isinstance(drawable, Triad):
        actors = []
        for column, label in zip(drawable.axes.T, drawable.labels):
            tip = drawable.origin + column
            actors.append(_arrow(drawable.origin, tip, tint(drawable.role)))
            actors.append(_label(label, tip, 1.3 * label_size,
                                 tint(drawable.role)))
        return actors
    if isinstance(drawable, Surface):
        mesh = vedo.Mesh([drawable.points, drawable.faces]).c(
            tint(drawable.role)).alpha(0.5)
        actors = [mesh]
        for marking in drawable.markings:
            actors += build_actor(marking, palette_name, extent)
        for point, text in drawable.labels:
            actors.append(_label(text, point, 1.6 * label_size,
                                 tint('stage_marks')))
        return actors
    if isinstance(drawable, Text):
        if drawable.role == 'legend':
            # Left-justified at a fixed offset on an opaque background,
            # so that the chords line up and the scene never shows
            # through the words.
            return [vedo.Text2D('\n'.join(drawable.lines),
                                pos=LEGEND_POSITION, justify='bottom-left',
                                s=LEGEND_TEXT_SIZE, c=tint('text'),
                                bg=tint('background'), alpha=1.0)]
        return [vedo.Text2D('\n'.join(drawable.lines),
                            pos=TEXT_POSITIONS[drawable.corner],
                            s=READOUT_TEXT_SIZE, c=tint(drawable.role),
                            alpha=0.9)]
    if isinstance(drawable, Image):
        return [vedo.Image(drawable.rgb)]
    raise TypeError(f'no actor for {type(drawable).__name__}')


class TwoViewRenderer:
    """The window: one or two views and, optionally, the panel strip."""

    def __init__(self, window_size, offscreen, n_views, palette_name,
                 title='rfsim', with_panels=False):
        self.palette_name = palette_name
        self.offscreen = offscreen
        vedo.settings.enable_default_keyboard_callbacks = False
        self.plotter = vedo.Plotter(shape=_initial_shape(),
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
        self.layout = None
        self.last_seconds = {'actors': 0.0, 'render': 0.0}   # of the
                                                             #   last realize
        self.set_layout(n_views, with_panels)
        self._apply_background()

    @property
    def interactor(self):
        return getattr(self.plotter, 'interactor', None)

    def set_layout(self, n_views, with_panels):
        """Place the viewports; a view or the strip that is off
        draws nothing."""
        if self.layout == (n_views, with_panels):
            return
        self.layout = (n_views, with_panels)
        for renderer, port in zip(self.plotter.renderers,
                                  _viewports(n_views, with_panels)):
            if port is None:
                renderer.DrawOff()
                renderer.SetViewport(0.0, 0.0, 0.001, 0.001)
            else:
                renderer.SetViewport(*port)
                renderer.DrawOn()

    def _apply_background(self):
        background = color(self.palette_name, 'background')
        for index in range(MAX_VIEWS + 1):
            self.plotter.at(index).background(background)

    def realize(self, scenes, palette_name, strip=None):
        """Draw the scenes; `strip` (a Strip, or None) fills the panel
        strip."""
        if palette_name != self.palette_name:
            self.palette_name = palette_name
            self.static_signature = {}
            self._apply_background()
        self.set_layout(len(scenes), strip is not None)
        started = time.perf_counter()
        for index, scene in enumerate(scenes):
            view = self.plotter.at(index)
            signature = (scene.view, len(scene.static),
                         tuple(type(d).__name__ for d in scene.static))
            if self.static_signature.get(index) != signature:
                view.remove(*self.static_actors.get(index, []))
                self.static_actors[index] = [
                    actor for drawable in scene.static
                    for actor in build_actor(drawable, palette_name,
                                             scene.info.extent)]
                view.add(*self.static_actors[index])
                self.static_signature[index] = signature
            view.remove(*self.dynamic_actors.get(index, []))
            self.dynamic_actors[index] = [
                actor for drawable in scene.dynamic
                for actor in build_actor(drawable, palette_name,
                                         scene.info.extent)]
            view.add(*self.dynamic_actors[index])
        self._place_panels(strip)
        built = time.perf_counter()
        if not self.shown:
            self.plotter.show(interactive=False, resetcam=False)
            self.shown = True
        self.plotter.render()
        self.last_seconds = {'actors': built - started,
                             'render': time.perf_counter() - built}

    def _place_panels(self, strip):
        """The strip: the first image, the budget text, the other
        images, side by side under a flat camera, with a cursor line
        over each image at its fraction of the plot box."""
        renderer = self.plotter.at(MAX_VIEWS)
        renderer.remove(*self.panel_actors)
        self.panel_actors = []
        if strip is None:
            return
        tint = color(self.palette_name, 'text')
        left, bottom, right, top = PLOT_BOX
        x = 0.0
        height = 0
        for position, (rgb, cursor) in enumerate(strip.images):
            if position == 1 and strip.lines:
                x += STRIP_TEXT_WIDTH
            image = vedo.Image(rgb)
            image.pos(x, 0.0, 0.0)
            self.panel_actors.append(image)
            image_height, image_width = rgb.shape[:2]
            if cursor is not None:
                x_cursor = x + (left + cursor * (right - left)) * image_width
                self.panel_actors.append(vedo.Line(
                    [(x_cursor, bottom * image_height, 1.0),
                     (x_cursor, top * image_height, 1.0)]).c(tint).lw(1.5))
            x += image_width + STRIP_GAP
            height = max(height, image_height)
        camera = renderer.camera
        camera.ParallelProjectionOn()
        camera.SetFocalPoint(x / 2.0, height / 2.0, 0.0)
        camera.SetPosition(x / 2.0, height / 2.0, 1000.0)
        camera.SetViewUp(0.0, 1.0, 0.0)
        camera.SetParallelScale(0.55 * height)
        if strip.lines:
            # The flat camera shows 2 * parallel scale * aspect units
            # across, centred on x / 2; the text's 2D position is a
            # fraction of that, so that it starts where the first
            # image ends whatever the window's proportions.
            width_px, height_px = self.plotter.renderers[MAX_VIEWS].GetSize()
            half_width = 0.55 * height * max(width_px, 1) / max(height_px, 1)
            visible_left = x / 2.0 - half_width
            text_x = strip.images[0][0].shape[1] + STRIP_GAP
            text_left = (text_x - visible_left) / (2.0 * half_width)
            self.panel_actors.append(vedo.Text2D(
                '\n'.join(strip.lines), pos=(text_left, 0.92),
                justify='top-left', s=STRIP_TEXT_SIZE, c=tint))
        renderer.add(*self.panel_actors)

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
        """The time slider along the bottom of the first view; none
        offscreen."""
        if self.interactor is None:
            return None

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
        """Call `handler(key)` with the key as vedo names it."""
        if self.interactor is None:
            return

        def on_press(event):
            if event.keypress:
                handler(event.keypress)
        self.plotter.add_callback('KeyPress', on_press)

    def on_tick(self, handler, milliseconds):
        """Call `handler(tick)` from vedo's timer, counting from zero."""
        if self.interactor is None:
            return

        def on_timer(event):
            handler(self.tick_count)
            self.tick_count += 1
        self.plotter.add_callback('timer', on_timer)
        self.plotter.timer_callback('start', dt=int(milliseconds))

    def interactive(self):
        """Block until `stop` or the window closes."""
        if self.interactor is not None:
            self.plotter.interactive()

    def stop(self):
        """Leave the interactive loop, from a tick or a key."""
        if self.interactor is not None:
            self.plotter.break_interaction()

    def screenshot(self, path=None, as_array=False):
        if as_array:
            return self.plotter.screenshot(asarray=True)
        self.plotter.screenshot(str(path))
        return None

    def close(self):
        self.plotter.close()
