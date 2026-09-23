"""The one place that knows the order of the stages (pseudocode 8.6;
design 8.6).

For each particle: the motion provider gives the exact inertial
samples; the frame carries them into the rotating description; the
pseudo-force terms and the true force are evaluated there; the ghost
path, the check, the comparison, the conserved quantities, and the
first-order overlay follow; the stop, if any, is recorded. A run
above the memory cap is refused before anything is allocated.

Attribution: this module is part of the rotating_frame teaching tool
of the UMKC Computational Physics Group (GPL-3.0-or-later).
"""

import numpy as np

from rotating_frame.analysis import (compare, first_order_deflection,
                                     ghost_path, monitor, overlay_applies,
                                     run_check)
from rotating_frame.motion import make_rule, provide
from rotating_frame.pseudoforces import stacked
from rotating_frame.run.results_store import (ResultsStore, StopRecord,
                                              estimate_bytes)
from rotating_frame.run.schema import RunFileError


def build_store(spec, rc, progress=None):
    """Build the results store of `spec` (pseudocode 8.6). `progress`,
    if given, is called with (particle index, particle count) after
    each particle."""
    n_particles = len(spec.launches)
    samples = spec.samples
    estimate = estimate_bytes(n_particles, samples)
    if estimate > rc.max_store_bytes:
        raise RunFileError(f'this run needs about {estimate / 1e6:.0f} MB '
                           f'of memory; the rc cap is '
                           f'{rc.max_store_bytes / 1e6:.0f} MB')
    times = np.linspace(0.0, spec.duration, samples)
    rule = make_rule(spec.stop, spec.axes.launch_point, spec.axes.up,
                     spec.frame.axis)
    check_on = spec.check.enabled
    overlay_on = (spec.view.overlay != 'off'
                  and overlay_applies(spec.frame, spec.duration))

    def blank(*shape):
        return np.full((n_particles, samples) + shape, np.nan)

    positions_in, velocities_in = blank(3), blank(3)
    positions_rot, velocities_rot = blank(3), blank(3)
    terms = blank(3, 3)
    true_force, ghost = blank(3), blank(3)
    check_positions = blank(3) if check_on else None
    check_velocities = blank(3) if check_on else None
    overlay = blank(3) if overlay_on else None
    mask = np.zeros((n_particles, samples), dtype=bool)
    comparisons = [] if check_on else None
    conserved = []
    stops = []

    for index, launch in enumerate(spec.launches):
        launch_in = (launch.position_in, launch.velocity_in)
        trajectory = provide(launch_in, spec.field, spec.frame,
                             spec.duration, samples, rule, spec.method,
                             spec.check.integrator, spec.check.substeps,
                             spec.check.rtol, spec.check.atol)
        valid = len(trajectory.times)
        mask[index, :valid] = True
        positions_in[index, :valid] = trajectory.positions_in
        velocities_in[index, :valid] = trajectory.velocities_in
        rotating = spec.frame.to_rotating(trajectory.times,
                                          trajectory.positions_in,
                                          trajectory.velocities_in)
        positions_rot[index, :valid], velocities_rot[index, :valid] = \
            rotating
        terms[index, :valid] = stacked(spec.frame, trajectory.times,
                                       *rotating)
        true_force[index, :valid] = spec.field.acceleration_rotating(
            spec.frame, trajectory.times, *rotating)
        ghost[index, :valid] = ghost_path(spec.field, spec.frame, launch_in,
                                          spec.axes.launch_point,
                                          trajectory.times, spec.check)
        check = None
        if check_on:
            check = run_check(spec.field, spec.frame, launch_in,
                              trajectory.times, spec.check)
            check_positions[index, :valid] = check[0]
            check_velocities[index, :valid] = check[1]
            comparisons.append(compare(*rotating, *check,
                                       ghost[index, :valid],
                                       spec.axes.launch_point))
        conserved.append(monitor(spec.field, spec.frame, launch_in,
                                 trajectory.times,
                                 (trajectory.positions_in,
                                  trajectory.velocities_in),
                                 rotating, check))
        if overlay_on:
            force_at_launch = true_force[index, 0]
            overlay[index, :valid] = first_order_deflection(
                spec.frame, spec.axes.launch_point, launch.velocity_rot,
                force_at_launch, trajectory.times)
        if trajectory.stop is None:
            stops.append(None)
        else:
            stops.append(StopRecord(index=trajectory.stop.index,
                                    time=trajectory.stop.time,
                                    kind=trajectory.stop.kind))
        if progress is not None:
            progress(index, n_particles)

    return ResultsStore(times=times, positions_in=positions_in,
                        velocities_in=velocities_in,
                        positions_rot=positions_rot,
                        velocities_rot=velocities_rot, terms=terms,
                        true_force=true_force, ghost=ghost,
                        check_positions=check_positions,
                        check_velocities=check_velocities,
                        comparison=comparisons, conserved=conserved,
                        overlay=overlay, stops=stops, mask=mask, spec=spec)
