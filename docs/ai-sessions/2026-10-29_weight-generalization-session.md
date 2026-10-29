# Sweep-weight generalization validation

## Request
Test the returned weight-sweep weights on other initial states and provide a
separate `.txt` summary of everything tried and its results.

## Context
- Source: `outputs/weight_sweep_20261027_200627_547397`.
- Completed sweep: 1,252 trials; 552 `ok`, 700 `error`.
- Overall winner `(0.05, 50000, 250000)` still finished 589,358 m apart at
  299.374 m/s. `ok` in the sweep means finite, sampled surface-safe output,
  not successful rendezvous.

## Implementation
- `validate_sweep_weights.py` freezes four candidates using only source results.
- Original control and eight new cases: 100 m / 1 km along-track, 10 km along-track
  with velocity error, radial, cross-track, mixed 100 km scale, higher target orbit,
  inclined target orbit.
- Each case has a no-burn coast and four independently optimized burn schedules.
- Reuses saved initial ephemeris, 3,600 s horizon, two burns, 1,000 samples/segment,
  existing optimizer seed 42 and full defaults. No optimizer/dynamics edits.
- Every completed trial is flushed to CSV and JSON; `summary.txt` is updated
  incrementally and labels incomplete runs explicitly.
- Important observed limitation: `burn_size` follows full Sun-frame velocity,
  not Earth-relative velocity. No independent tighter-tolerance verification.

## Verification
`python -B -m unittest discover -s tests -v`: all 23 tests pass.

## Production command
`python -B -u validate_sweep_weights.py --output outputs/weight_validation_20261029`

Launched as a background process. Final production status and measurements must
be read from `outputs/weight_validation_20261029/summary.txt`; launch alone does
not imply completion.
