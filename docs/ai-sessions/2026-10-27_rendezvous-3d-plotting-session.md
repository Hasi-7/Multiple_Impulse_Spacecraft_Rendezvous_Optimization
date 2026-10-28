# 3D rendezvous graphing integration

## Request
Update `Multiple_Gravitational_Objects.py` and `celestial_body_simulator.py` graphing to support the user's new 3D four-body rendezvous model. Follow-up: account for each body's radius.

## Changes
- Added reusable `plot_rendezvous(history, body_solution)` with xyz separation, a Sun-centered four-body/spacecraft overview, and an Earth-centered rendezvous close-up.
- Reference-body positions are interpolated independently at target, chaser and burn times, so all plotted positions are time-matched.
- Mark initial/final spacecraft positions and burns in 3D; retain printed optimizer/trajectory scores and final separation.
- Draw Sun, Earth, Moon and Jupiter surfaces using representative physical radii in `BODY_RADII`, aligned with `BODY_NAMES`. Convert metres to AU/km per view. Draw Earth as a sphere instead of the obsolete 2D circle.
- Keep equal spatial axis scale and include sphere extents in bounds. Visibility markers are explicitly not to scale.
- Main displays both the existing body-system overview and new rendezvous figure.
- Fixed blockers in the user's current integration: one-element `args` tuples, forwarding the body solution into optimizer scoring, six-component spacecraft input and `[3:6]` burn-velocity slices. Reuse the already computed target solution in trajectory reconstruction.
- Retained the existing gravity/optimizer methodology, DOP853 and rtol=1e-6. No changes to the other spacecraft scripts.

## Validation
- `python -B -m unittest discover -s tests -v`: nine tests passed.
- Tests cover full 3D separation (including z), time-matched reference transforms, equal axis scales, physical radius arguments in every view, trajectory/score agreement, a one-generation real optimizer smoke test, and main integration with mocked initial states and optimization.
- Both figures were rendered with the noninteractive Agg backend and inspected as PNG previews in the approved temporary directory. Reserved additional header space in the body overview after inspection.

## Limitations
- Body radii are for visualization, not collision detection or extended-body gravity.
- Small bodies and nearby spacecraft cannot be resolved at the global Jupiter/AU scale; use the local views.
- Earth-relative inputs must use nonrotating J2000 ecliptic-aligned axes. The existing burn direction follows the current origin-frame spacecraft velocity, unchanged from the user's approach except for correcting its 3D slice.
- Full default optimization and a fresh live Horizons request were not run during this graphing update; initial-state network behavior was tested in the earlier session.
