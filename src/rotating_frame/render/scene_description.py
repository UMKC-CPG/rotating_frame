"""The scene as a renderer-agnostic list of drawables, one list per
view (pseudocode 9.1 and 9.3; design 9.2 to 9.4, 9.7).

Nothing here knows vedo. A drawable is a small record with a palette
role; the renderer realizes each kind. Every point of every drawable
is expressed relative to the view's camera target, the launch point
as that view sees it, so that VTK's single-precision vertices see
numbers of order the scene and not the Earth's radius over the
length scale (ARCHITECTURE 4.2); the camera then looks at the origin.

The arrows follow design 5.3: the inertial view draws the true force
and the velocity at the tracked particle and no pseudo-force at all;
the rotating view draws the true force, the three terms, their sum,
and the velocity. Two arrow scales, one for the true force and the
sum and one for the three terms, are chosen so that the largest
arrow of each group at the launch is a quarter of the scene, and
their ratio is stated when it is not one (design 9.4, VISION P12).

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import textwrap
from dataclasses import dataclass, field, replace

import numpy as np

from rotating_frame.core import units
from rotating_frame.core.natural_units import to_real
from rotating_frame.geometry import (extra_trails, ghost_now,
                                     stage_surface, trail, triads)
from rotating_frame.pseudoforces import TERM_NAMES

ARROW_FRACTION = 0.25          # the largest arrow of a group, at launch
SAME_SCALE_WITHIN = 3.0        # the two scales are made equal within this
TINY = 1e-30                   # a magnitude taken as zero
TRACKED_GLYPH_FACTOR = 1.8
GHOST_GLYPH_FACTOR = 0.7
READOUT_WIDTH = 62               # characters, for a half-width view
LABEL_BEYOND = 0.03              # a label sits this far past its tip
LABEL_CLEARANCE = 0.10           # labels closer than this are spread
LABEL_STEP = 0.07                # by this much along the view's up
                                 #   (all fractions of the extent)
ARROW_LABELS = {'true': 'true force', 'centrifugal': 'centrifugal',
                'coriolis': 'Coriolis', 'euler': 'Euler', 'sum': 'sum',
                'velocity': 'v'}


@dataclass(frozen=True)
class Polyline:
    points: np.ndarray
    role: str
    width: float = 2.0
    style: str = 'solid'          # solid | dashed | dotted | thin
    label: object = None
    label_at: object = None       # where the label sits; the last
                                  #   point when None


@dataclass(frozen=True)
class Arrow:
    base: np.ndarray
    tip: np.ndarray
    role: str
    label: str
    label_at: object = None       # the tip when None


@dataclass(frozen=True)
class Glyph:
    center: np.ndarray
    radius: float
    role: str
    label: object = None


@dataclass(frozen=True)
class Triad:
    origin: np.ndarray
    axes: np.ndarray              # columns
    role: str
    labels: tuple


@dataclass(frozen=True)
class Surface:
    points: np.ndarray            # at rest
    faces: list
    role: str
    markings: list                # of Polyline, at rest
    labels: list = field(default_factory=list)   # of (point, text)
    rotation: object = None       # (3, 3) turning rest into the view;
                                  #   identity when None


@dataclass(frozen=True)
class Text:
    lines: tuple
    corner: str                   # top_left top_right bottom_left ...
    role: str = 'text'


@dataclass(frozen=True)
class Image:
    rgb: np.ndarray
    rect: tuple                   # (x, y, w, h) in window fractions


@dataclass
class SceneInfo:
    extent: float
    scale_true: float
    scale_pseudo: float
    scale_velocity: float
    arrow_ratio: object
    camera_follows: bool
    camera_target: np.ndarray
    camera_basis: np.ndarray


@dataclass
class ViewScene:
    view: str
    static: list
    dynamic: list
    info: SceneInfo


@dataclass(frozen=True)
class Strip:
    """What the panel strip shows: plotted images, each with the
    cursor's fraction of its plot box or None, and the budget as
    text lines (pseudocode 9.6)."""

    images: list
    lines: tuple


def extent(store, spec):
    """The scene's size: the largest displacement from the launch
    point over every valid sample, and at least one."""
    launch_point = spec.axes.launch_point
    displacement = store.positions_rot - launch_point
    distances = np.linalg.norm(displacement, axis=-1)
    largest = np.nanmax(np.where(store.mask, distances, np.nan))
    return float(max(1.0, largest))


def arrow_scales(store, spec, tracked, mode, rc, scene_extent,
                 view='rotating'):
    """The three arrow scales and the stated ratio (design 9.4). The
    velocity scale is the view's own: on the Earth the inertial
    velocity is the ground's hundreds of metres a second plus the
    throw, and one scale for both views would make one of the two
    arrows invisible or enormous."""
    terms, true_force = store.terms_at(tracked, 0)
    true0 = float(np.linalg.norm(true_force))
    pseudo0 = float(np.max(np.linalg.norm(terms, axis=-1)))
    quarter = ARROW_FRACTION * scene_extent
    scale_pseudo = quarter / max(pseudo0, TINY)
    if true0 <= TINY:
        # No true force (the turntable): one scale, nothing to state.
        scale_true, ratio = scale_pseudo, None
    else:
        scale_true = quarter / true0
        ratio = scale_pseudo / scale_true
        if (mode == 'same'
                or 1.0 / SAME_SCALE_WITHIN <= ratio <= SAME_SCALE_WITHIN):
            scale_pseudo, ratio = scale_true, None
    _, velocity_in, _, velocity_rot = store.state_at(tracked, 0)
    velocity0 = velocity_in if view == 'inertial' else velocity_rot
    speed0 = max(float(np.linalg.norm(velocity0)), TINY)
    scale_velocity = quarter / speed0
    factor = rc.arrow_scale
    return (scale_true * factor, scale_pseudo * factor, ratio,
            scale_velocity * factor)


def arrows(store, spec, particle, sample, view, info, shown):
    """The arrows at the particle, relative to the camera target
    (design 5.3)."""
    position_in, velocity_in, position_rot, velocity_rot = store.state_at(
        particle, sample)
    terms, force_rot = store.terms_at(particle, sample)
    time = store.time_at(particle, sample)
    if view == 'inertial':
        force_in = spec.frame.rotation(time) @ force_rot
        candidates = [('true', force_in, info.scale_true),
                      ('velocity', velocity_in, info.scale_velocity)]
        base = position_in
    else:
        candidates = [('true', force_rot, info.scale_true),
                      ('centrifugal', terms[0], info.scale_pseudo),
                      ('coriolis', terms[1], info.scale_pseudo),
                      ('euler', terms[2], info.scale_pseudo),
                      ('sum', force_rot + terms.sum(axis=0), info.scale_true),
                      ('velocity', velocity_rot, info.scale_velocity)]
        base = position_rot
    base = base - info.camera_target
    return [Arrow(base=base, tip=base + scale * vector, role=name,
                  label=ARROW_LABELS[name])
            for name, vector, scale in candidates if name in shown]


def spread_labels(drawables, up, extent):
    """Give every labeled arrow and polyline a place for its label
    that clears the others: just past an arrow's tip, at a path's
    end, and nudged along the view's up until no earlier label is
    within LABEL_CLEARANCE. At a landing, where every arrow is short
    and shares a base, the words would otherwise sit on one spot."""
    placed = []
    spread = []
    for drawable in drawables:
        if isinstance(drawable, Arrow):
            shaft = drawable.tip - drawable.base
            length = np.linalg.norm(shaft)
            direction = shaft / length if length > TINY else up
            anchor = drawable.tip + LABEL_BEYOND * extent * direction
        elif isinstance(drawable, Polyline) and drawable.label:
            anchor = np.asarray(drawable.points[-1], dtype=float)
        else:
            spread.append(drawable)
            continue
        while any(np.linalg.norm(anchor - other) < LABEL_CLEARANCE * extent
                  for other in placed):
            anchor = anchor + LABEL_STEP * extent * up
        placed.append(anchor)
        spread.append(replace(drawable, label_at=anchor))
    return spread


def _format(spec, value_natural, kind, unit=None):
    display = spec.preset.display_units
    return units.format_real(to_real(spec.scales, value_natural, kind), kind,
                             unit or display[kind])


def readouts(store, spec, state, info, view, frame_note=None):
    """The text block of design 9.7 for this view; `frame_note` is
    the session's drawing-rate line, appended last when given."""
    tracked = state.tracked
    sample = min(state.k, store.valid_samples(tracked) - 1)
    time = store.time_at(tracked, state.k)       # the grid's clock
    lines = [f'{view} view',
             f't = {time:.4g}  ({_format(spec, time, "time")}); '
             f'θ = {np.degrees(spec.frame.angle(time)):.4g}°']
    if view == 'rotating':
        launch = spec.launches[tracked].spec
        if launch.speed is not None:
            lines.append(f'launch: {_format(spec, launch.speed, "speed")} '
                         f'at {np.degrees(launch.azimuth):.1f}° from N, '
                         f'{np.degrees(launch.elevation):.1f}° up '
                         f'({launch.frame})')
        elif launch.velocity is not None:
            components = ', '.join(_format(spec, part, 'speed')
                                   for part in launch.velocity)
            lines.append(f'launch: ({components}) E, N, U ({launch.frame})')
        else:
            lines.append(f'launch: at rest ({launch.frame})')
        _, _, position_rot, velocity_rot = store.state_at(tracked, sample)
        local = spec.axes.basis().T @ (position_rot - spec.axes.launch_point)
        east, north, up = local
        if spec.preset.name == 'earth' and abs(east) < 1.0:
            east_text = _format(spec, east, 'length', 'cm')
        else:
            east_text = _format(spec, east, 'length')
        speed_text = _format(spec, np.linalg.norm(velocity_rot), 'speed')
        lines.append(f'E {east_text}, N {_format(spec, north, "length")}, '
                     f'U {_format(spec, up, "length")}; speed {speed_text}')
        terms, force_rot = store.terms_at(tracked, sample)
        mass = launch.mass
        for name, vector in (('true force', force_rot),
                             *zip(('centrifugal', 'Coriolis', 'Euler'),
                                  terms)):
            magnitude = _format(spec, np.linalg.norm(vector), 'acceleration')
            if mass is not None:
                newtons = (to_real(spec.scales, np.linalg.norm(vector),
                                   'acceleration') * mass)
                magnitude += f' ({newtons:.4g} N)'
            lines.append(f'{name}: {magnitude}')
    scale_note = (f'1 unit = {spec.scales.length:.4g} m, 1 time unit = '
                  f'{spec.scales.time:.4g} s')
    if spec.exaggeration != 1.0:
        scale_note += f'; Ω exaggerated × {spec.exaggeration:g}'
    if info.arrow_ratio is not None:
        scale_note += (f'; pseudo-force arrows × {info.arrow_ratio:.3g} '
                       'relative to the true force')
    if view == 'inertial' and info.camera_follows:
        scale_note += '; camera follows P'
    lines.append(scale_note)
    if spec.field.approximation is not None:
        lines.append(spec.field.approximation.sentence(spec.duration))
    if spec.overlay_note is not None:
        lines.append(spec.overlay_note)
    if frame_note:
        lines.append(frame_note)
    wrapped = []
    for line in lines:
        wrapped += textwrap.wrap(line, READOUT_WIDTH,
                                 subsequent_indent='  ') or ['']
    return Text(lines=tuple(wrapped), corner='top_left')


def describe_view(store, spec, state, rc, view, legend_lines=(),
                  frame_note=None):
    """One view's scene at the session's state (pseudocode 9.3)."""
    scene_extent = extent(store, spec)
    scale_true, scale_pseudo, ratio, scale_velocity = arrow_scales(
        store, spec, state.tracked, state.arrow_mode, rc, scene_extent,
        view)
    tracked = state.tracked
    sample = min(state.k, store.valid_samples(tracked) - 1)
    # The scene's clock is the grid's: a stopped particle sits at its
    # stop while the stage and the others go on (pseudocode 9.3).
    time = store.time_at(tracked, state.k)
    rotation = spec.frame.rotation(time)
    launch_point = spec.axes.launch_point
    follows = view == 'inertial' and state.camera_mode == 'follow'
    if view == 'inertial':
        target = rotation @ launch_point if follows else launch_point
        basis = rotation @ spec.axes.basis() if follows else spec.axes.basis()
    else:
        target = launch_point
        basis = spec.axes.basis()
    info = SceneInfo(extent=scene_extent, scale_true=scale_true,
                     scale_pseudo=scale_pseudo, scale_velocity=scale_velocity,
                     arrow_ratio=ratio, camera_follows=follows,
                     camera_target=target, camera_basis=basis)

    static, dynamic = [], []
    stage_turns = view == 'inertial'        # the stage moves in the
                                            #   inertial view; the floor
                                            #   moves in the rotating one
    if 'stage' in state.scenery:
        surfaces = []
        for piece in stage_surface(spec, view, time, scene_extent):
            surfaces.append(Surface(
                points=piece['points'], faces=piece['faces'],
                role=piece['role'], rotation=piece['rotation'],
                markings=[Polyline(points=line, role=role, width=1.0)
                          for role, line in piece['markings']],
                labels=piece['labels']))
        (dynamic if stage_turns or spec.preset.name == 'merry_go_round'
         else static).extend(surfaces)
    if 'triads' in state.scenery:
        pair, axis_arrow = triads(spec, view, time, scene_extent,
                                  np.zeros(3))
        for axes, role, labels, is_moving in pair:
            drawable = Triad(origin=np.zeros(3), axes=axes, role=role,
                             labels=labels)
            (dynamic if is_moving else static).append(drawable)
        if axis_arrow is not None:
            vector, role, label = axis_arrow
            static.append(Arrow(base=np.zeros(3), tip=vector, role=role,
                                label=label))

    glyph_radius = rc.glyph_radius * scene_extent
    for particle in range(store.n_particles):
        own_sample = min(state.k, store.valid_samples(particle) - 1)
        points, role = trail(store, particle, own_sample, view)
        is_tracked = particle == tracked
        label = spec.launches[particle].spec.label or f'{particle}'
        dynamic.append(Polyline(points=points - target, role=role,
                                width=rc.trail_width,
                                label=label if is_tracked else None))
        dynamic.append(Glyph(
            center=points[-1] - target,
            radius=glyph_radius * (TRACKED_GLYPH_FACTOR if is_tracked
                                   else 1.0),
            role='tracked_glyph' if is_tracked else 'glyph',
            label=label if is_tracked else None))
    if view == 'rotating':
        for points, role, style, label in extra_trails(store, spec, tracked,
                                                        state.paths):
            dynamic.append(Polyline(points=points - target, role=role,
                                    width=1.0 if style == 'thin' else 1.5,
                                    style=style, label=label))
        if 'ghost' in state.paths:
            # The ball the rider expected, where it is now.
            dynamic.append(Glyph(
                center=ghost_now(store, spec, tracked, sample) - target,
                radius=GHOST_GLYPH_FACTOR * glyph_radius, role='ghost'))
    dynamic += arrows(store, spec, tracked, sample, view, info, state.arrows)
    dynamic = spread_labels(dynamic, basis[:, 2], scene_extent)
    dynamic.append(readouts(store, spec, state, info, view, frame_note))
    if state.legend and legend_lines:
        dynamic.append(Text(lines=tuple(legend_lines), corner='bottom_right',
                            role='legend'))
    return ViewScene(view=view, static=static, dynamic=dynamic, info=info)


def describe(store, spec, state, rc, legend_lines=(), frame_note=None):
    """The scenes of the views the session shows; the legend, when
    shown, goes on the last view only."""
    views = (('inertial', 'rotating') if state.view == 'both'
             else (state.view,))
    return [describe_view(store, spec, state, rc, view,
                          legend_lines if view == views[-1] else (),
                          frame_note)
            for view in views]
