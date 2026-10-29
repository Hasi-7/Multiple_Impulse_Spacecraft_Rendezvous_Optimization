"""Earth/Moon/Jupiter propagation with the Sun fixed at the origin.

Run: python celestial_body_simulator.py
Initial states require internet access to JPL Horizons. Integration uses SI units.
"""

import csv
from datetime import datetime, timezone
from io import StringIO

import matplotlib.pyplot as plt
import numpy as np
import requests
from scipy.integrate import solve_ivp


HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
BODY_NAMES = ("Sun", "Earth", "Moon", "Jupiter")
BODY_IDS = ("10", "399", "301", "599")
# Gravitational parameters (m^3/s^2), in the same order as BODY_NAMES.
MU = np.array([1.3271e20, 3.986e14, 4.9028e12, 1.2671e17])
# Representative radii in metres, aligned with BODY_NAMES (spherical model).
BODY_RADII = np.array([6.957e8, 6.371e6, 1.7374e6, 6.9911e7])
AU = 149_597_870_700.0
COLORS = ("goldenrod", "tab:blue", "gray", "tab:orange")
DEFAULT_EPOCH = "2026-10-27 12:00:00"


def epoch_to_jd(epoch):
    """Convert a UTC calendar epoch to a Julian date for Horizons."""
    date = datetime.strptime(epoch, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return date.timestamp() / 86400.0 + 2440587.5


def get_initial_states(epoch=DEFAULT_EPOCH):
    """Return rows [x, y, z, vx, vy, vz] in metres and metres/second.

    Horizons supplies geometric, heliocentric J2000 ecliptic vectors at one
    UTC epoch. The Sun is exactly at rest at the initial origin in this frame.
    """
    jd = epoch_to_jd(epoch)
    states = np.zeros((len(BODY_NAMES), 6))
    for index in range(1, len(BODY_NAMES)):
        params = {
            "format": "text",
            "COMMAND": f"'{BODY_IDS[index]}'",
            "OBJ_DATA": "NO",
            "MAKE_EPHEM": "YES",
            "EPHEM_TYPE": "VECTORS",
            "CENTER": "'500@10'",
            "TLIST": f"'{jd:.9f}'",
            "TIME_TYPE": "UT",
            "OUT_UNITS": "KM-S",
            "REF_PLANE": "ECLIPTIC",
            "REF_SYSTEM": "J2000",
            "VEC_TABLE": "2",
            "VEC_CORR": "NONE",
            "CSV_FORMAT": "YES",
        }
        response = requests.get(HORIZONS, params=params, timeout=30)
        response.raise_for_status()
        text = response.text
        if "$$SOE" not in text or "$$EOE" not in text:
            raise ValueError(f"Horizons returned no state vector for {BODY_NAMES[index]}.")
        # Horizons CSV rows have no header within the ephemeris markers:
        # Julian date, calendar date, X, Y, Z, VX, VY, VZ, trailing empty field.
        rows = list(csv.reader(StringIO(text.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip())))
        try:
            vector = [float(value.replace("D", "E")) for value in rows[0][2:8]]
            if len(vector) != 6 or not np.all(np.isfinite(vector)):
                raise ValueError("Expected six finite vector components.")
            states[index] = np.asarray(vector) * 1000.0
        except (IndexError, ValueError) as exc:
            raise ValueError(f"Invalid Horizons state for {BODY_NAMES[index]}.") from exc
    return states


def n_body_ode(t, state):
    """Newtonian point-mass gravity with a physically fixed Sun (3D).

    State layout: [Sun x,y,z,vx,vy,vz, Earth x,y,z,vx,vy,vz, ...].
    The Sun attracts the other bodies but does not respond to their gravity.
    This is a fixed-source approximation, not a moving heliocentric frame.
    """
    bodies = np.asarray(state).reshape(len(BODY_NAMES), 6)
    positions = bodies[:, :3]
    # displacement[i, j] points from body i to body j.
    displacement = positions[None, :, :] - positions[:, None, :]
    distance = np.linalg.norm(displacement, axis=2)
    np.fill_diagonal(distance, np.inf)
    if np.any(distance == 0):
        raise ValueError("Two bodies occupy the same position; gravity is singular.")
    acceleration = np.sum(displacement * (MU[None, :] / distance**3)[:, :, None], axis=1)
    derivatives = np.empty_like(bodies)
    derivatives[:, :3] = bodies[:, 3:]
    derivatives[:, 3:] = acceleration
    derivatives[0] = 0.0  # Hold the Sun's position and velocity constant.
    return derivatives.ravel()


def simulate_system(initial_states, duration_seconds, samples=2000):
    """Integrate the fixed-Sun system for a positive duration."""
    states = np.asarray(initial_states, dtype=float)
    if states.shape != (4, 6) or not np.all(np.isfinite(states)):
        raise ValueError("Initial states must be a finite (4, 6) array.")
    if np.any(states[0] != 0):
        raise ValueError("The fixed Sun must start at the origin with zero velocity.")
    if not np.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("Duration must be a positive, finite number of seconds.")
    if not isinstance(samples, (int, np.integer)) or samples < 2:
        raise ValueError("At least two output samples are required.")
    solution = solve_ivp(
        n_body_ode,
        (0, duration_seconds),
        states.ravel(),
        t_eval=np.linspace(0, duration_seconds, samples),
        method="DOP853",
        rtol=1e-6,
        dense_output=True,
    )
    if not solution.success:
        raise RuntimeError(f"Body propagation failed: {solution.message}")
    return solution


def set_equal_3d_limits(ax, points):
    """Keep x/y/z at the same physical scale without clipping the data."""
    points = np.asarray(points)
    lower = points.min(axis=0)
    upper = points.max(axis=0)
    centre = (lower + upper) / 2
    half_width = max(float(np.max(upper - lower)) * 0.55, 1e-6)
    ax.set_xlim(centre[0] - half_width, centre[0] + half_width)
    ax.set_ylim(centre[1] - half_width, centre[1] + half_width)
    ax.set_zlim(centre[2] - half_width, centre[2] + half_width)
    ax.set_box_aspect((1, 1, 1))


def plot_body_surface(ax, centre, radius, color, alpha=0.4):
    """Draw a true-scale sphere; centre and radius must use the axis units."""
    longitude = np.linspace(0, 2 * np.pi, 40)
    latitude = np.linspace(0, np.pi, 20)
    return ax.plot_surface(
        centre[0] + radius * np.outer(np.cos(longitude), np.sin(latitude)),
        centre[1] + radius * np.outer(np.sin(longitude), np.sin(latitude)),
        centre[2] + radius * np.outer(np.ones_like(longitude), np.cos(latitude)),
        color=color, alpha=alpha,
    )


def plot_system(solution, epoch):
    """Show initial positions, heliocentric trajectories, and lunar motion."""
    states = solution.y.reshape(len(BODY_NAMES), 6, -1)
    heliocentric = states[:, :3, :] - states[0, :3, :][None, :, :]
    days = solution.t[-1] / 86400.0
    fig = plt.figure(figsize=(16, 6))
    initial_ax = fig.add_subplot(131, projection="3d")
    orbit_ax = fig.add_subplot(132, projection="3d")
    moon_ax = fig.add_subplot(133, projection="3d")

    for index, (name, color) in enumerate(zip(BODY_NAMES, COLORS)):
        xyz = heliocentric[index] / AU
        plot_body_surface(initial_ax, xyz[:, 0], BODY_RADII[index] / AU, color)
        plot_body_surface(orbit_ax, xyz[:, -1], BODY_RADII[index] / AU, color)
        initial_ax.scatter(*xyz[:, 0], color=color, label=name)
        orbit_ax.plot(*xyz, color=color, label=name)
        orbit_ax.scatter(*xyz[:, 0], color=color, marker="o")
        orbit_ax.scatter(*xyz[:, -1], color=color, marker="x")

    # A shared AU scale preserves the geometry (the orbits are nearly planar).
    extent = max(float(np.max(np.abs(heliocentric / AU)
                              + BODY_RADII[:, None, None] / AU)) * 1.1, 0.01)
    for ax in (initial_ax, orbit_ax):
        ax.set(xlabel="x (AU)", ylabel="y (AU)", zlabel="z (AU)")
        ax.set_xlim(-extent, extent)
        ax.set_ylim(-extent, extent)
        ax.set_zlim(-extent, extent)
        ax.set_box_aspect((1, 1, 1))
        ax.legend()
    initial_ax.set_title(f"Initial positions\n{epoch} UTC")
    orbit_ax.set_title(f"{days:g} days: initial (o), final (x)\nSun-centered trajectories")

    moon_relative = (states[2, :3] - states[1, :3]) / 1000.0
    plot_body_surface(moon_ax, np.zeros(3), BODY_RADII[1] / 1000, "tab:blue")
    plot_body_surface(moon_ax, moon_relative[:, -1], BODY_RADII[2] / 1000, "gray")
    moon_ax.plot(*moon_relative, color="gray", label="Moon")
    moon_ax.scatter(0, 0, 0, color="tab:blue", label="Earth")
    moon_ax.scatter(*moon_relative[:, 0], color="gray", marker="o", label="Initial")
    moon_ax.scatter(*moon_relative[:, -1], color="black", marker="x", label="Final")
    moon_extent = max(float(np.max(np.abs(moon_relative))) + BODY_RADII[2] / 1000,
                      BODY_RADII[1] / 1000) * 1.1
    moon_ax.set_xlim(-moon_extent, moon_extent)
    moon_ax.set_ylim(-moon_extent, moon_extent)
    moon_ax.set_zlim(-moon_extent, moon_extent)
    moon_ax.set_box_aspect((1, 1, 1))
    moon_ax.set(xlabel="x (km)", ylabel="y (km)", zlabel="z (km)", title="Earth-centered lunar trajectory")
    moon_ax.legend()
    fig.suptitle("Sun, Earth, Moon and Jupiter — true-scale spherical surfaces; markers not to scale")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def main():
    while True:
        epoch = input(f"Starting UTC epoch YYYY-MM-DD HH:MM:SS [{DEFAULT_EPOCH}]: ").strip() or DEFAULT_EPOCH
        try:
            epoch_to_jd(epoch)
            break
        except ValueError:
            print("Enter a valid date and time in YYYY-MM-DD HH:MM:SS format.")
    while True:
        try:
            duration = float(input("Simulation duration in seconds (86400 = one day): "))
            if np.isfinite(duration) and duration > 0:
                break
        except ValueError:
            pass
        print("Enter a positive, finite number of seconds.")

    try:
        print("Fetching initial states from JPL Horizons...")
        initial_states = get_initial_states(epoch)
        print("Propagating four-body system with DOP853 (rtol=1e-6)...")
        solution = simulate_system(initial_states, duration)
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        print(f"Simulation failed: {exc}")
        return
    plot_system(solution, epoch)
    plt.show()


if __name__ == "__main__":
    main()
