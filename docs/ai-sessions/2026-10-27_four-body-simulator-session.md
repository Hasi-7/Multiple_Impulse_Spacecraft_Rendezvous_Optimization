# Four-body simulator

## Request
Plot the initial Sun (at origin), Earth, Moon and Jupiter positions and propagate their motion for a runtime-specified duration using `solve_ivp`, DOP853 and `rtol=1e-6`. Do not change spacecraft code.

## Changes
- Added `celestial_body_simulator.py` with runtime UTC starting epoch and duration in seconds.
- Fetch initial heliocentric J2000 ecliptic position/velocity vectors from JPL Horizons, converting km and km/s to SI units.
- Integrate mutual Newtonian gravity for all four bodies, including the Sun's acceleration.
- Plot initial positions, Sun-relative 3D trajectories with initial/final markers, and an Earth-relative lunar close-up.
- Added five offline tests in `tests/test_celestial_body_simulator.py` covering gravity/momentum balance, Horizons parsing, missing vectors, propagation/energy/plotting and invalid inputs.
- Existing source files and pre-existing user modifications were not changed.

## Validation
- `python -m unittest discover -s tests -v`: five tests passed.
- Live Horizons request for the default epoch and 86,400-second propagation succeeded.
- `git diff --check`: passed before documentation additions.

## Usage and limitations
Run `python celestial_body_simulator.py`. Dependencies: NumPy, SciPy, Matplotlib and requests. Internet access is required for initial states. Default epoch: 2026-10-27 12:00:00 UTC. The Sun starts at rest at the origin but moves under gravity; plots subtract its current position. Bodies are point masses and only these four bodies are included. No spacecraft coupling, animation or full-ephemeris accuracy is claimed.
