# Current Task

## Goal
Validate the completed weight sweep's returned weights on different initial
spacecraft states and write a separate plain-text report of all experiments.

## Relevant Files
- `weight_sweep.py`, `Multiple_Gravitational_Objects.py`
- `outputs/weight_sweep_20261027_200627_547397/{configuration.json,results.csv,summary.json}`
- New reproducible runner: `validate_sweep_weights.py`.

## Constraints
- Reuse saved ephemeris, duration, burns, sampling and unchanged optimizer/seed.
- Freeze candidate weights before testing; do not tune against validation states.
- Distinguish finite/surface-safe trajectories from actual rendezvous success.

## Do Not Touch
- Existing sweep output and unrelated user changes, including report_outline.tex.

## Acceptance Criteria
- Test baseline plus eight alternative initial-state scenarios, against coast controls.
- Report every trial, full states, weights, burns, metrics, thresholds and limitations.
- Save results and separate summary.txt under a new outputs directory.

## Test Plan
- Unit tests for scenario construction, selection and success classification.
- Existing tests, then full production optimizer trials (no shortened optimizer).

## Open Questions
