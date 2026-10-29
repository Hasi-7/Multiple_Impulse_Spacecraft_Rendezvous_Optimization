# Current Task

## Report follow-up requested by user
After the active fixed-Sun +/-1000 m/s sweep and validation finish, write only
Section 4 (Simulation Checks) and Section 5 (Experiments and Results) of
`report_outline.tex`, matching the user's existing tone. The user will write
Discussion and Conclusion; preserve those sections and all newer user edits.
Confirm sweep completion and 36 powered trials / nine coast controls from saved
files, not just a process exit. Base figures, tables and claims on verified data;
distinguish code tests, numerical checks, valid trajectories and rendezvous success.
Use the project success criterion of <=1 km and <=1 m/s; separate coast-already-
successful cases from active-control improvements. Do not invent numerical checks
that were not performed. Compile and visually inspect the resulting PDF in `out`.
No chat wakeup/automation tool is available in this session; the user must return
to this chat for the agent to perform this writing after the background run ends.

## Active fixed-Sun rerun (2026-10-29)
User requested a physically fixed Sun after authorizing full experiment reruns.
Terminal PID 31880 runs `context/run-corrected-experiments.ps1 -RunTag 20261029_144240`.
All 28 unit tests passed. Full sweep is running; validation starts automatically
after coarse and refinement finish. Check live status before starting any process.

- Status: `outputs/corrected_experiments_20261029_144240.status.json`.
- Sweep: `outputs/weight_sweep_fixed_sun_20261029_144240/`.
- Validation: `outputs/weight_validation_fixed_sun_20261029_144240/`.
- Window: `Spacecraft rendezvous - fixed Sun sweep and validation`.
- Fixed Sun, Earth-relative burns, infinite invalid-time penalty, saved initial ephemeris.
- Active 3D burn magnitude limit: +/-1000 m/s per burn, shared by optimizer and
  sweep validation. The original 2D script still uses +/-500 m/s.
- Previous fixed-Sun +/-500 sweep was stopped with 128 saved trials; its
  `20261029_142048` status is superseded. Do not merge old rows into this run.
- Stopped previous moving-Sun sweep at 75 completed trials; its outputs are preserved
  and its status is superseded. Never combine its rows with this new run.
- Earlier no-rerun wording below describes the historical model only.

## Goal
Validate the completed weight sweep's returned weights on different initial
spacecraft states and write a separate plain-text report of all experiments.

## Relevant Files
- Handoff and continuation instructions: `context/weight-sweep-handoff.md`.
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
- Validation completed: 36/36 powered trials, nine coast controls, `Complete: True`.
  See completion update in `context/weight-sweep-handoff.md`. Four new-state
  project-criterion passes, all in the 100 m case that also passes when coasting;
  zero strict passes. No rerun needed.
- The user's report now defines success as <=1 km and <=1 m/s, matching the
  validation report's existing "loose" criterion. Reconcile wording after the
  runner finishes; do not confuse zero strict passes with zero project passes.
