#!/usr/bin/env python3

"""Spike: does the frame-fixed closed form of design 4, carried into
the rotating frame by the transform of design 1, reproduce the
textbook eastward deflection of a dropped stone, and by how much does
the exact answer differ from the first-order formula?

The formula d = (1/3) g Omega t^3 cos(latitude) is first order in
Omega. The exact motion under the uniform approximation lands to the
east by that amount times (1 - Omega^2 R_E / g0), independent of
latitude, because the effective gravity is weaker by a factor
(1 - Omega^2 R_E cos^2(lat) / g0) and the plumb line is tilted so
that the Coriolis factor is cos(lat + tilt), which costs another
(1 - Omega^2 R_E sin^2(lat) / g0) at first order; the two together
are 1 - Omega^2 R_E / g0. That factor is 3.45e-3, and it is the
tolerance design 4.6 derives for the drop oracle.

Run from the repository root in the suite's environment:
    dev/spikes/drop_deflection.py
"""

import numpy as np
from scipy.optimize import brentq

OMEGA = 7.2921150e-5                 # rad/s, sidereal (design 2.4)
R_EARTH = 6.371e6                    # m
G_ZERO = 9.820                       # m/s^2, the bare attraction
AXIS = np.array([0.0, 0.0, 1.0])


def rotation(angle):
    """Rodrigues' rotation about AXIS by `angle` (design 1.2)."""
    cosine, sine = np.cos(angle), np.sin(angle)
    cross = np.array([[0, -AXIS[2], AXIS[1]], [AXIS[2], 0, -AXIS[0]],
                      [-AXIS[1], AXIS[0], 0]])
    return (cosine * np.eye(3) + sine * cross
            + (1 - cosine) * np.outer(AXIS, AXIS))


def drop(latitude_deg, height):
    """Drop a particle from rest in the rotating frame at `height`
    above the ground at `latitude_deg`; return the landing time, the
    eastward and northward landing offsets, and the effective g."""
    latitude = np.radians(latitude_deg)
    omega_vector = OMEGA * AXIS
    launch_point = R_EARTH * np.array([np.cos(latitude), 0.0,
                                       np.sin(latitude)])
    gravity_rot = -G_ZERO * launch_point / R_EARTH
    centrifugal = -np.cross(omega_vector, np.cross(omega_vector,
                                                   launch_point))
    g_effective = gravity_rot + centrifugal
    up = -g_effective / np.linalg.norm(g_effective)
    east = np.cross(AXIS, launch_point)
    east /= np.linalg.norm(east)
    north = np.cross(up, east)

    # Launch (design 1.5): at rest in the rotating frame.
    r_zero = launch_point + height * up
    v_zero = np.cross(omega_vector, r_zero)

    # The rotating-parabola closed form (design 4.2).
    g_parallel = np.dot(gravity_rot, AXIS) * AXIS
    g_perpendicular = gravity_rot - g_parallel
    axis_cross_g = np.cross(AXIS, g_perpendicular)

    def position(time):
        angle = OMEGA * time
        return (r_zero + v_zero * time
                + 0.5 * np.dot(gravity_rot, AXIS) * time**2 * AXIS
                + (1 - np.cos(angle)) / OMEGA**2 * g_perpendicular
                + (angle - np.sin(angle)) / OMEGA**2 * axis_cross_g)

    def height_above_ground(time):
        displacement = rotation(OMEGA * time).T @ position(time) \
            - launch_point
        return np.dot(displacement, up)

    landing_time = brentq(height_above_ground, 1e-3, 1e3)
    displacement = rotation(OMEGA * landing_time).T \
        @ position(landing_time) - launch_point
    return (landing_time, np.dot(displacement, east),
            np.dot(displacement, north), np.linalg.norm(g_effective))


if __name__ == '__main__':
    correction = 1 - OMEGA**2 * R_EARTH / G_ZERO
    print(f'predicted exact/textbook ratio 1 - W^2 R/g0 = {correction:.6f}')
    print(f'{"lat":>5} {"height":>7} {"t_land":>9} {"east (m)":>12} '
          f'{"textbook":>12} {"ratio":>9} {"north (m)":>11}')
    for latitude_deg in (10.0, 30.0, 45.0, 60.0, 80.0):
        for height in (100.0, 1000.0):
            t_land, east, north, g_eff = drop(latitude_deg, height)
            textbook = (G_ZERO * OMEGA * t_land**3
                        * np.cos(np.radians(latitude_deg)) / 3)
            print(f'{latitude_deg:5.0f} {height:7.0f} {t_land:9.4f} '
                  f'{east:12.6e} {textbook:12.6e} {east / textbook:9.6f} '
                  f'{north:11.3e}')
