"""The two-dimensional panels, drawn with matplotlib into images the
renderer places in the window (pseudocode 9.6; design 9.6).

Three panels: the magnitudes of the three terms and the true force
against time, on a log axis when they span more than two decades;
the error budget's three columns as text; and the conserved
quantities' drift along the exact path and the check, or the
sentence saying why one is not reported.

A plotted panel depends on the run, the tracked particle, and the
palette only, and matplotlib costs hundreds of milliseconds an
image, so the session keeps the images and the renderer draws the
cursor over them as a line at `cursor_fraction`. The budget changes
with every sample, so it is text (`budget_lines`) and never an image
in the window; `render_panel('budget', ...)` still draws it for a
saved picture.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later). The
mechanism follows the scattering tool's `render/panels.py`.
"""

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from rotating_frame.pseudoforces import TERM_NAMES
from rotating_frame.render.palettes import color

PANEL_NAMES = ('terms', 'budget', 'conservation')
LOG_ABOVE = 100.0                # ratio of largest to smallest magnitude
PLOT_BOX = (0.2, 0.2, 0.97, 0.88)    # left, bottom, right, top: where
                                     #   the axes sit, as figure fractions
NONE = 'none'                    # an empty column (vedo's window font
                                 #   has no em dash)


def _figure(size, palette):
    width, height = size
    figure = Figure(figsize=(width / 100.0, height / 100.0), dpi=100)
    figure.patch.set_facecolor(color(palette, 'background'))
    left, bottom, right, top = PLOT_BOX
    figure.subplots_adjust(left=left, right=right, bottom=bottom, top=top)
    return figure


def _style(axes, palette):
    text = color(palette, 'text')
    axes.set_facecolor(color(palette, 'background'))
    for spine in axes.spines.values():
        spine.set_color(text)
    axes.tick_params(colors=text, labelsize=7)
    axes.xaxis.label.set_color(text)
    axes.yaxis.label.set_color(text)
    axes.title.set_color(text)


def _particle_times(store, particle):
    """The particle's own times over its valid samples: the grid, with
    the stop's event time last when it stopped early (pseudocode
    8.6), so that the axis ends where the data does."""
    valid = store.valid_samples(particle)
    return np.array([store.time_at(particle, sample)
                     for sample in range(valid)])


def _time_axis(axes, times):
    """The x axis exactly the particle's valid times, no margin, so
    that a cursor fraction maps straight onto the plot box."""
    axes.margins(x=0)
    if len(times) > 1 and times[-1] > times[0]:
        axes.set_xlim(times[0], times[-1])
    axes.set_xlabel('t (natural)')


def panel_terms(store, particle, palette, figure):
    """The terms against time for one particle."""
    valid = store.valid_samples(particle)
    times = _particle_times(store, particle)
    axes = figure.add_subplot(111)
    _style(axes, palette)
    magnitudes = {}
    for index, name in enumerate(TERM_NAMES):
        magnitudes[name] = np.linalg.norm(store.terms[particle, :valid,
                                                      index], axis=-1)
    magnitudes['true'] = np.linalg.norm(store.true_force[particle, :valid],
                                        axis=-1)
    positive = [values[values > 0] for values in magnitudes.values()]
    positive = np.concatenate(positive) if any(len(p) for p in positive) \
        else np.array([1.0])
    if positive.max() / positive.min() > LOG_ABOVE:
        axes.set_yscale('log')
    for name, values in magnitudes.items():
        axes.plot(times, values, color=color(palette, name), lw=1.2,
                  label=name)
    _time_axis(axes, times)
    axes.set_ylabel('|a| (natural)')
    axes.set_title('pseudo-force terms', fontsize=8)
    axes.legend(fontsize=6, loc='best')


def budget_lines(budget):
    """The three columns as text lines; an empty column reads
    "none" (design 6.4: never combined)."""
    numerical = budget.numerical
    if numerical['delta'] is None:
        numerical_lines = [f'numerical      {NONE}']
    else:
        drift = (NONE if numerical['drift'] is None
                 else f'{numerical["drift"]:.2e}')
        numerical_lines = [
            f'numerical      δ = {numerical["delta"]:.2e}  '
            f'η = {numerical["eta"]:.2e}  drift = {drift}',
            f'               max δ = {numerical["max_delta"]:.2e}  '
            f'max η = {numerical["max_eta"]:.2e}']
    if budget.approximation is None:
        approximation_text = NONE
    else:
        approximation_text = (f'uniform gravity, estimate '
                              f'{budget.approximation["estimate"]:.1e}')
    distortion = budget.distortion
    ratio = distortion['arrow_ratio']
    distortion_text = (f'Ω × {distortion["exaggeration"]:g}; arrows × '
                       + ('1' if ratio is None else f'{ratio:.3g}')
                       + ('; camera follows P' if distortion['camera_follows']
                          else '; camera fixed'))
    return (['error budget: three kinds, never combined']
            + numerical_lines
            + [f'approximation  {approximation_text}',
               f'distortion     {distortion_text}'])


def panel_budget(budget, palette, figure):
    """The budget lines as text in a figure, for a saved picture."""
    axes = figure.add_subplot(111)
    _style(axes, palette)
    axes.set_axis_off()
    for row, line in enumerate(budget_lines(budget)):
        axes.text(0.02, 0.9 - 0.2 * row, line, transform=axes.transAxes,
                  fontsize=7, color=color(palette, 'text'),
                  weight='bold' if row == 0 else 'normal')


def panel_conservation(store, particle, palette, figure):
    """The drifts against time, or the sentence for what is not
    reported."""
    record = store.conserved[particle]
    valid = store.valid_samples(particle)
    times = _particle_times(store, particle)
    axes = figure.add_subplot(111)
    _style(axes, palette)
    plotted = False
    for name, values, style in (('E exact', record.energy_exact, '-'),
                                ('E check', record.energy_check, '--'),
                                ('J exact', record.jacobi_exact, '-'),
                                ('J check', record.jacobi_check, '--')):
        if values is None:
            continue
        role = 'coriolis' if name.startswith('E') else 'centrifugal'
        axes.plot(times, values[:valid], style, color=color(palette, role),
                  lw=1.0, label=name)
        plotted = True
    if plotted:
        axes.legend(fontsize=6, loc='best')
        _time_axis(axes, times)
        axes.set_ylabel('drift / scale')
    for row, note in enumerate(record.notes):
        axes.text(0.02, 0.9 - 0.12 * row, note, transform=axes.transAxes,
                  fontsize=6, color=color(palette, 'text'), wrap=True)
    axes.set_title('conserved quantities', fontsize=8)


def cursor_fraction(store, particle, sample):
    """Where the cursor sits on a plotted panel: the sample's time as
    a fraction of the particle's valid times, or None when there are
    fewer than two."""
    valid = store.valid_samples(particle)
    if valid < 2:
        return None
    first = store.time_at(particle, 0)
    last = store.time_at(particle, valid - 1)
    if last <= first:
        return None
    time = store.time_at(particle, min(sample, valid - 1))
    return float(min(max((time - first) / (last - first), 0.0), 1.0))


def render_panel(name, store, particle, palette, budget=None,
                 size=(400, 300)):
    """One panel as an RGB array of shape (height, width, 3)."""
    figure = _figure(size, palette)
    if name == 'terms':
        panel_terms(store, particle, palette, figure)
    elif name == 'budget':
        panel_budget(budget, palette, figure)
    elif name == 'conservation':
        panel_conservation(store, particle, palette, figure)
    else:
        raise KeyError(name)
    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    width, height = canvas.get_width_height()
    buffer = np.frombuffer(canvas.buffer_rgba(), dtype=np.uint8)
    return buffer.reshape(height, width, 4)[:, :, :3].copy()
