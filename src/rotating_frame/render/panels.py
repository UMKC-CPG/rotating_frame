"""The two-dimensional panels, drawn with matplotlib into images the
renderer places in the window (pseudocode 9.6; design 9.6).

Three panels: the magnitudes of the three terms and the true force
against time, on a log axis when they span more than two decades,
with a cursor at the current sample; the error budget's three columns
as text; and the conserved quantities' drift along the exact path
and the check, or the sentence saying why one is not reported.

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


def _figure(size, palette):
    width, height = size
    figure = Figure(figsize=(width / 100.0, height / 100.0), dpi=100)
    figure.patch.set_facecolor(color(palette, 'background'))
    figure.subplots_adjust(left=0.2, right=0.97, bottom=0.2, top=0.88)
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


def panel_terms(store, particle, sample, palette, figure):
    """The terms against time for one particle."""
    valid = store.valid_samples(particle)
    times = store.sample_times()[:valid]
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
    axes.axvline(store.time_at(particle, min(sample, valid - 1)),
                 color=color(palette, 'text'), lw=0.8)
    axes.set_xlabel('t (natural)')
    axes.set_ylabel('|a| (natural)')
    axes.set_title('pseudo-force terms', fontsize=8)
    axes.legend(fontsize=6, loc='best')


def panel_budget(budget, palette, figure):
    """The three columns as text; an empty column reads a dash."""
    axes = figure.add_subplot(111)
    _style(axes, palette)
    axes.set_axis_off()
    text = color(palette, 'text')
    numerical = budget.numerical
    columns = [
        ('numerical',
         ['—'] if numerical['delta'] is None else
         [f'δ = {numerical["delta"]:.2e}', f'η = {numerical["eta"]:.2e}',
          f'drift = {numerical["drift"]:.2e}'
          if numerical['drift'] is not None else 'drift = —',
          f'max δ = {numerical["max_delta"]:.2e}',
          f'max η = {numerical["max_eta"]:.2e}']),
        ('approximation',
         ['—'] if budget.approximation is None else
         [f'estimate = {budget.approximation["estimate"]:.1e}',
          'uniform gravity (see note)']),
        ('distortion',
         [f'Ω × {budget.distortion["exaggeration"]:g}'
          if budget.distortion['exaggeration'] != 1.0 else 'Ω × 1',
          'arrows × '
          + (f'{budget.distortion["arrow_ratio"]:.3g}'
             if budget.distortion['arrow_ratio'] is not None else '1'),
          'camera follows P' if budget.distortion['camera_follows']
          else 'camera fixed'])]
    for index, (title, lines) in enumerate(columns):
        x = 0.03 + 0.33 * index
        axes.text(x, 0.92, title, transform=axes.transAxes, fontsize=8,
                  color=text, weight='bold')
        for row, line in enumerate(lines):
            axes.text(x, 0.78 - 0.14 * row, line, transform=axes.transAxes,
                      fontsize=7, color=text)
    axes.set_title('error budget: three kinds, never combined',
                   fontsize=8)


def panel_conservation(store, particle, sample, palette, figure):
    """The drifts against time, or the sentence for what is not
    reported."""
    record = store.conserved[particle]
    valid = store.valid_samples(particle)
    times = store.sample_times()[:valid]
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
        axes.axvline(store.time_at(particle, min(sample, valid - 1)),
                     color=color(palette, 'text'), lw=0.8)
        axes.legend(fontsize=6, loc='best')
        axes.set_xlabel('t (natural)')
        axes.set_ylabel('drift / scale')
    for row, note in enumerate(record.notes):
        axes.text(0.02, 0.9 - 0.12 * row, note, transform=axes.transAxes,
                  fontsize=6, color=color(palette, 'text'), wrap=True)
    axes.set_title('conserved quantities', fontsize=8)


def render_panel(name, store, particle, sample, palette, budget=None,
                 size=(400, 300)):
    """One panel as an RGB array of shape (height, width, 3)."""
    figure = _figure(size, palette)
    if name == 'terms':
        panel_terms(store, particle, sample, palette, figure)
    elif name == 'budget':
        panel_budget(budget, palette, figure)
    elif name == 'conservation':
        panel_conservation(store, particle, sample, palette, figure)
    else:
        raise KeyError(name)
    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    width, height = canvas.get_width_height()
    buffer = np.frombuffer(canvas.buffer_rgba(), dtype=np.uint8)
    return buffer.reshape(height, width, 4)[:, :, :3].copy()
