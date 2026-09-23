"""The two views realized with vedo, the only module that imports it
(pseudocode 9.5; design 9.1 and 9.2; ARCHITECTURE 6.5).

One vedo window holds three sub-renderers from the start: two views
side by side with unshared cameras, and a strip along the bottom
that holds the panel images under a flat camera. `realize` lays the
viewports out from what it is given, one or two scenes and a strip
or none, so that a change of view or of the panel switch is a change
of viewports and never a new window.

Dynamic actors are KEPT between frames in a pool per view, keyed by
what would need a rebuild (kind, role, label, width, style, radius,
and an ordinal among equals), and only placed each frame: an arrow
is a unit arrow under a matrix of rotation, scale, and translation;
a glyph and a label are moved; a trail's points are reassigned into
a line of fixed capacity with the tail collapsed onto the last
point; a surface takes its rotation as its matrix; a text block
takes new text. Building an actor costs milliseconds in vedo and
placing one costs microseconds, which is the difference between a
frame of ninety milliseconds and one of a few. Static actors are
built once per run and kept by a signature.

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
from dataclasses import dataclass, field

import numpy as np
import vedo
from vtkmodules.vtkCommonMath import vtkMatrix4x4

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
READOUT_TEXT_SIZE = 0.6
STRIP_GAP = 20                   # pixels between the strip's images
STRIP_TEXT_WIDTH = 520           # pixels left for the budget text
STRIP_TEXT_SIZE = 0.55
TINY_LENGTH = 1e-12              # an arrow shorter than this is hidden
LINE_CAPACITY_MINIMUM = 16
TEXT_POSITIONS = {'top_left': 'top-left', 'top_right': 'top-right',
                  'bottom_left': 'bottom-left',
                  'bottom_right': 'bottom-right'}
MAX_VIEWS = 2
X_HAT = np.array([1.0, 0.0, 0.0])


# -- viewports ----------------------------------------------------------

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


# -- placement: matrices and moves ---------------------------------------

def rotation_to(direction):
    """The rotation taking x-hat to the unit vector `direction`
    (Rodrigues), or a half turn about z when they are opposite."""
    axis = np.cross(X_HAT, direction)
    cosine = float(X_HAT @ direction)
    if np.linalg.norm(axis) < 1e-12:
        return np.eye(3) if cosine > 0.0 else np.diag([-1.0, -1.0, 1.0])
    cross = np.array([[0.0, -axis[2], axis[1]],
                      [axis[2], 0.0, -axis[0]],
                      [-axis[1], axis[0], 0.0]])
    return np.eye(3) + cross + cross @ cross / (1.0 + cosine)


def user_matrix(rotation, translation, scale=1.0):
    """A VTK 4 x 4 matrix: rotate and scale, then translate."""
    matrix = vtkMatrix4x4()
    for row in range(3):
        for column in range(3):
            matrix.SetElement(row, column,
                              float(rotation[row, column] * scale))
        matrix.SetElement(row, 3, float(translation[row]))
    return matrix


def place_arrow(actor, base, tip):
    """Place a unit arrow (built from the origin along x-hat) so that
    it runs from `base` to `tip`; a vanishing arrow is hidden."""
    shaft = np.asarray(tip, dtype=float) - np.asarray(base, dtype=float)
    length = float(np.linalg.norm(shaft))
    if length < TINY_LENGTH:
        actor.actor.VisibilityOff()
        return
    actor.actor.VisibilityOn()
    actor.actor.SetUserMatrix(user_matrix(rotation_to(shaft / length),
                                          base, length))


def place_at(actor, position):
    """Move an actor built at the origin to `position` (a label's
    follower keeps facing the camera; see `_label`)."""
    actor.actor.SetPosition(*np.asarray(position, dtype=float))


def place_rotated(actor, rotation):
    """Turn an actor built at rest by `rotation` about the origin."""
    matrix = np.eye(3) if rotation is None else np.asarray(rotation)
    actor.actor.SetUserMatrix(user_matrix(matrix, np.zeros(3)))


def padded(points, capacity):
    """`points` as an array of exactly `capacity` rows, the tail
    collapsed onto the last point, so that a line of fixed size can
    show a trail of any shorter length."""
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    if len(points) == 0:
        points = np.zeros((1, 3))
    filled = np.empty((capacity, 3))
    shown = min(len(points), capacity)
    filled[:shown] = points[:shown]
    filled[shown:] = points[shown - 1]
    return filled


# -- makers: canonical actors, placed afterwards --------------------------

def _label(text, size, tint):
    """A 3D label at the origin that turns to face the camera. The
    text is built at the origin and moved by its actor's position:
    vedo bakes `pos` into the letters' points, and a camera-following
    actor turns about its own origin, so a label built in place would
    swing around the scene's origin instead of standing at its
    point."""
    return vedo.Text3D(text, s=size, c=tint).follow_camera()


def _unit_arrow(tint):
    """An arrow from the origin along x-hat of length one, whose
    shaft and head scale with it under `place_arrow`."""
    return vedo.Arrow((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                      shaft_radius=ARROW_SHAFT, head_radius=ARROW_HEAD_RADIUS,
                      head_length=ARROW_HEAD_LENGTH, c=tint)


def _sphere(radius, tint):
    return vedo.Sphere(pos=(0.0, 0.0, 0.0), r=radius, res=16).c(tint)


def _line(points, tint, width, style):
    """A polyline; dashed and dotted styles are vedo's dashed line,
    which cannot be resized and so is rebuilt when its points
    change."""
    points = np.asarray(points, dtype=float)
    if len(points) < 2:
        points = np.vstack((points, points))
    if style == 'dashed':
        return vedo.DashedLine(points, spacing=0.4, c=tint, lw=width)
    if style == 'dotted':
        return vedo.DashedLine(points, spacing=0.15, c=tint, lw=width)
    return vedo.Line(points).c(tint).lw(width)


def _mesh(points, faces, tint):
    return vedo.Mesh([np.asarray(points, dtype=float), faces]).c(tint) \
        .alpha(0.5)


def _text2d(drawable, tint_of):
    text = '\n'.join(drawable.lines)
    if drawable.role == 'legend':
        # Left-justified at a fixed offset on an opaque background,
        # so that the chords line up and the scene never shows
        # through the words.
        return vedo.Text2D(text, pos=LEGEND_POSITION, justify='bottom-left',
                           s=LEGEND_TEXT_SIZE, c=tint_of('text'),
                           bg=tint_of('background'), alpha=1.0)
    return vedo.Text2D(text, pos=TEXT_POSITIONS[drawable.corner],
                       s=READOUT_TEXT_SIZE, c=tint_of(drawable.role),
                       alpha=0.9)


def build_actor(drawable, palette_name, extent=1.0):
    """The vedo objects that realize one drawable, built and placed
    in one go: for the static actors, and for tests. `extent` sizes
    the labels."""
    tint = lambda role: color(palette_name, role)      # noqa: E731
    label_size = LABEL_SIZE * extent

    def labeled(text, position, size, tint_name):
        label = _label(text, size, tint(tint_name))
        place_at(label, position)
        return label

    if isinstance(drawable, Polyline):
        points = np.asarray(drawable.points, dtype=float)
        actors = [_line(points, tint(drawable.role), drawable.width,
                        drawable.style)]
        if drawable.label:
            where = (points[-1] if drawable.label_at is None
                     else drawable.label_at)
            actors.append(labeled(drawable.label, where, label_size, 'text'))
        return actors
    if isinstance(drawable, Arrow):
        arrow = _unit_arrow(tint(drawable.role))
        place_arrow(arrow, drawable.base, drawable.tip)
        where = (drawable.tip if drawable.label_at is None
                 else drawable.label_at)
        return [arrow, labeled(drawable.label, where, label_size,
                               drawable.role)]
    if isinstance(drawable, Glyph):
        sphere = _sphere(drawable.radius, tint(drawable.role))
        place_at(sphere, drawable.center)
        actors = [sphere]
        if drawable.label:
            actors.append(labeled(drawable.label, drawable.center,
                                  label_size, 'text'))
        return actors
    if isinstance(drawable, Triad):
        actors = []
        for column, label in zip(drawable.axes.T, drawable.labels):
            tip = drawable.origin + column
            arrow = _unit_arrow(tint(drawable.role))
            place_arrow(arrow, drawable.origin, tip)
            actors.append(arrow)
            actors.append(labeled(label, tip, 1.3 * label_size,
                                  drawable.role))
        return actors
    if isinstance(drawable, Surface):
        rotation = (np.eye(3) if drawable.rotation is None
                    else np.asarray(drawable.rotation))
        mesh = _mesh(drawable.points, drawable.faces, tint(drawable.role))
        place_rotated(mesh, rotation)
        actors = [mesh]
        for marking in drawable.markings:
            line = _line(marking.points, tint(marking.role), marking.width,
                         marking.style)
            place_rotated(line, rotation)
            actors.append(line)
        for point, text in drawable.labels:
            actors.append(labeled(text, rotation @ np.asarray(point),
                                  1.6 * label_size, 'stage_marks'))
        return actors
    if isinstance(drawable, Text):
        return [_text2d(drawable, tint)]
    if isinstance(drawable, Image):
        return [vedo.Image(drawable.rgb)]
    raise TypeError(f'no actor for {type(drawable).__name__}')


# -- the pool -----------------------------------------------------------

@dataclass
class PoolEntry:
    """Kept actors under one key, with what a rebuild depends on."""

    actors: list
    capacity: int = 0             # a solid line's point capacity
    extra: dict = field(default_factory=dict)


class ViewPool:
    """The kept dynamic actors of one view (pseudocode 9.5). Each
    frame `begin` clears the wanted set, the `want_*` methods build
    or place, and `end` removes what was not wanted."""

    def __init__(self, view, palette_name, extent):
        self.view = view
        self.entries = {}
        self.wanted = set()
        self.counters = {}
        self.palette_name = palette_name
        self.label_size = LABEL_SIZE * extent

    def tint(self, role):
        return color(self.palette_name, role)

    def begin(self, palette_name, extent):
        self.palette_name = palette_name
        self.label_size = LABEL_SIZE * extent
        self.wanted = set()
        self.counters = {}

    def key_for(self, *parts):
        """`parts` plus an ordinal among equal parts this frame, so
        that two alike drawables keep two actors."""
        ordinal = self.counters.get(parts, 0)
        self.counters[parts] = ordinal + 1
        return parts + (ordinal,)

    def take(self, key, make):
        """The entry under `key`, made and added when new."""
        self.wanted.add(key)
        entry = self.entries.get(key)
        if entry is None:
            entry = make()
            self.view.add(*entry.actors)
            self.entries[key] = entry
        return entry

    def drop(self, key):
        entry = self.entries.pop(key, None)
        if entry is not None:
            self.view.remove(*entry.actors)

    def end(self):
        for key in [key for key in self.entries if key not in self.wanted]:
            self.drop(key)

    # -- one method per kind of drawable --

    def want_label(self, text, position, size, tint_name):
        key = self.key_for('label', text, tint_name, round(size, 9))
        entry = self.take(key, lambda: PoolEntry(
            [_label(text, size, self.tint(tint_name))]))
        place_at(entry.actors[0], position)

    def want_arrow(self, kind, role, base, tip):
        key = self.key_for(kind, role)
        entry = self.take(key, lambda: PoolEntry(
            [_unit_arrow(self.tint(role))]))
        place_arrow(entry.actors[0], base, tip)

    def want_glyph(self, drawable):
        key = self.key_for('glyph', drawable.role, round(drawable.radius, 9))
        entry = self.take(key, lambda: PoolEntry(
            [_sphere(drawable.radius, self.tint(drawable.role))]))
        place_at(entry.actors[0], drawable.center)
        if drawable.label:
            self.want_label(drawable.label, drawable.center, self.label_size,
                            'text')

    def want_polyline(self, drawable):
        points = np.asarray(drawable.points, dtype=float).reshape(-1, 3)
        if drawable.style in ('dashed', 'dotted'):
            # Rebuilt only when the number of points changes: a whole
            # path (design 9.3) is built once.
            key = self.key_for('dashed', drawable.role, drawable.style,
                               drawable.width, len(points))
            self.take(key, lambda: PoolEntry(
                [_line(points, self.tint(drawable.role), drawable.width,
                       drawable.style)]))
        else:
            key = self.key_for('line', drawable.role, drawable.width)
            entry = self.entries.get(key)
            if entry is not None and len(points) > entry.capacity:
                self.drop(key)
                entry = None
            if entry is None:
                capacity = max(2 * len(points), LINE_CAPACITY_MINIMUM)
                entry = self.take(key, lambda: PoolEntry(
                    [_line(padded(points, capacity), self.tint(drawable.role),
                           drawable.width, 'solid')], capacity=capacity))
            else:
                self.wanted.add(key)
                entry.actors[0].vertices = padded(points, entry.capacity)
        if drawable.label:
            where = (points[-1] if drawable.label_at is None
                     else drawable.label_at)
            self.want_label(drawable.label, where, self.label_size, 'text')

    def want_triad(self, drawable):
        for index, (column, label) in enumerate(zip(drawable.axes.T,
                                                    drawable.labels)):
            tip = drawable.origin + column
            self.want_arrow(('triad', index), drawable.role, drawable.origin,
                            tip)
            self.want_label(label, tip, 1.3 * self.label_size, drawable.role)

    def want_surface(self, drawable):
        rotation = (np.eye(3) if drawable.rotation is None
                    else np.asarray(drawable.rotation))
        key = self.key_for('surface', drawable.role, len(drawable.points),
                           len(drawable.markings))

        def make():
            actors = [_mesh(drawable.points, drawable.faces,
                            self.tint(drawable.role))]
            for marking in drawable.markings:
                actors.append(_line(marking.points, self.tint(marking.role),
                                    marking.width, marking.style))
            return PoolEntry(actors)
        entry = self.take(key, make)
        for actor in entry.actors:
            place_rotated(actor, rotation)
        for point, text in drawable.labels:
            self.want_label(text, rotation @ np.asarray(point),
                            1.6 * self.label_size, 'stage_marks')

    def want_text(self, drawable):
        key = self.key_for('text', drawable.corner, drawable.role)
        entry = self.take(key, lambda: PoolEntry([_text2d(drawable,
                                                          self.tint)]))
        entry.actors[0].text('\n'.join(drawable.lines))

    def want(self, drawable):
        if isinstance(drawable, Polyline):
            self.want_polyline(drawable)
        elif isinstance(drawable, Arrow):
            self.want_arrow('arrow', drawable.role, drawable.base,
                            drawable.tip)
            where = (drawable.tip if drawable.label_at is None
                     else drawable.label_at)
            self.want_label(drawable.label, where, self.label_size,
                            drawable.role)
        elif isinstance(drawable, Glyph):
            self.want_glyph(drawable)
        elif isinstance(drawable, Triad):
            self.want_triad(drawable)
        elif isinstance(drawable, Surface):
            self.want_surface(drawable)
        elif isinstance(drawable, Text):
            self.want_text(drawable)
        else:
            key = self.key_for('other', type(drawable).__name__)
            self.take(key, lambda: PoolEntry(
                build_actor(drawable, self.palette_name)))

    def clear(self):
        for key in list(self.entries):
            self.drop(key)


# -- the window ---------------------------------------------------------

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
        self.pool = {}                   # view index -> ViewPool
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

    def _forget_everything(self):
        """On a palette change: colors are baked into every actor."""
        for index, actors in self.static_actors.items():
            self.plotter.at(index).remove(*actors)
        self.static_actors = {}
        self.static_signature = {}
        for pool in self.pool.values():
            pool.clear()
        self.pool = {}

    def realize(self, scenes, palette_name, strip=None):
        """Draw the scenes; `strip` (a Strip, or None) fills the panel
        strip."""
        if palette_name != self.palette_name:
            self.palette_name = palette_name
            self._forget_everything()
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
            pool = self.pool.get(index)
            if pool is None:
                pool = self.pool[index] = ViewPool(view, palette_name,
                                                   scene.info.extent)
            pool.begin(palette_name, scene.info.extent)
            for drawable in scene.dynamic:
                pool.want(drawable)
            pool.end()
        for index in range(len(scenes), MAX_VIEWS):
            if index in self.pool:
                self.pool[index].clear()
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
