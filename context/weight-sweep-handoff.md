# Weight sweep and validation report handoff

## Current analysis after removing the initial proximity case
The user requested excluding the 100 m initial-offset case because its no-burn
control already met the success criterion. Original validation artifacts are
preserved in `original_validation_including_100m_20261031_001251.zip` inside the
current validation directory. Its active configuration, CSV/JSON, report, figures,
numerical checks and Appendix C now retain eight cases and 32 powered attempts.
All retained numerical records are unchanged; source weights were not retuned.
Overall weights pass two of seven new cases; each other selection passes zero.
No optimization rerun was needed. Historical nine-case/36-attempt statements
below refer to the archived original batch. Future validation also uses eight cases.

## Latest fixed-Sun +/-1000 experiment is complete

Verified from the saved files for run `20261029_144240`: all 1,312 sweep trials
completed (1,000 coarse, 312 additional refined), all 36 powered validation trials
completed, and nine coast controls are saved. All powered rows have status `ok`.
The launcher status is `completed` and validation report says `Complete: True`.
No duplicate production run was launched.

Overall weights (0.0075, 5000, 2.5) pass the project criterion in 3/8 new states;
coarse and velocity selections each pass 1/8 and position passes 0/8. The 100 m
case already passes under coast. The other overall passes are the 1 km and 10 km
along-track cases. Five new-state weight/state pairs pass in total.

All 28 code checks passed. Independent tighter-tolerance fixed-schedule replays
preserve the pass/fail classifications for all 36 trials. The five production
passes also pass at rtol=1e-12 with atol=1e-8. These are replays, not reoptimization.
Evidence/figures: `outputs/weight_validation_fixed_sun_20261029_144240/report_checks.json`,
`report_validation.png`, `report_success_history.png`; runner `verify_report_results.py`.

Report Sections 4 and 5 are written and the 12-page PDF is compiled and checked
in both root and `out`. Discussion and Conclusion are unchanged for the user.
Completed outputs and these report changes have not yet been committed/pushed.

## Fixed-Sun model supersedes the moving-Sun rerun

The user requested a physically fixed Sun on 2026-10-29. Sun position and
velocity are now held at zero while the other bodies move under gravity.
The corrected moving-Sun rerun `20261029_140808` was stopped with 75 readable
saved trials. Its outputs are preserved, its status is superseded, and no
validation batch for it was started.

New visible terminal PID 7828 runs `context/run-corrected-experiments.ps1`
with tag `20261029_142048`. It performs the full sweep then all 36 validations.
See `context/current-task.md` for live status and output paths. All 28 code
checks pass. Fingerprints now include both spacecraft and body dynamics;
old moving-Sun results cannot be resumed or validated as fixed-Sun results.

## Corrected-model assessment (2026-10-29, after pulling b692bc8)

This update supersedes the earlier "No rerun is needed" statement for work
using the corrected Earth-relative burn model. The old batches are complete,
but evaluated a different burn-direction convention. Preserve them as historical
results rather than reusing their rankings or success counts for the new model.

- Pulled `origin/main` by fast-forward to `b692bc8` and reapplied local changes
  without conflicts. A backup of those local changes remains in the Git stash.
- Verified 1,252 sweep rows (552 ok, 700 errors), 36 completed powered validation
  trials and nine coast controls. All 700 sweep errors are invalid returned burns.
- The user-authorized fix in `Multiple_Gravitational_Objects.py` now subtracts
  Earth's velocity at each burn time in both scoring and trajectory reconstruction.
- Both weight selection and powered validation must be reoptimized for conclusions
  about the corrected model. A new coarse sweep may select a different refinement
  neighbourhood, so its final trial count need not be exactly 1,252.
- Existing body initial states, test scenarios and no-burn coast controls remain
  applicable when the remaining dynamics/settings are unchanged. New reporting
  must distinguish their provenance and use the project criterion of 1 km / 1 m/s.
- Diagnostic only: replaying the old overall winner's unchanged burn schedule
  under the corrected model gives 1,809,598.297 m / 1,148.808 m/s, compared with
  the recorded 589,358.494 m / 299.374 m/s. This was not a new optimization and
  does not establish the attainable performance of the corrected model.
- Before a full rerun, address the existing finite invalid-sequence penalty and
  verify promising terminal results with tighter numerical tolerances. The present
  `1e12` penalty can beat valid costs; changing it is separate from the burn fix.
- Use fresh output locations; do not resume the old sweep with changed physics.
  Update the validation report generator's historical full-inertial-burn wording
  before generating a corrected-model report.
- All 24 unit tests passed after the pull. No production sweep or 36-trial batch
  was restarted as part of this assessment.

## User goal
Take the returned weight-sweep weights, test them on other initial spacecraft
states, assess rendezvous performance, and provide a separate `.txt` report of
everything tried. The user also requested a table view and pushed the current
version to `main`. This handoff is a status snapshot, not a claim of completion.

## Start here
- Original completed sweep: `outputs/weight_sweep_20261027_200627_547397/`.
- New validation report: `outputs/weight_validation_20261029/summary.txt`.
- Exact states, ephemeris and candidates: validation `configuration.json`.
- Raw validation measurements: validation `results.csv` and `results.json`.
- Validation runner: `validate_sweep_weights.py`.
- Source sweep runner: `weight_sweep.py`.
- Dynamics and optimization: `Multiple_Gravitational_Objects.py`.
- Body constants and propagation: `celestial_body_simulator.py`.
- Tests: `tests/test_validate_sweep_weights.py`, `tests/test_weight_sweep.py`.

## Live status at handoff (2026-10-29)
### Completion update
The background command has now finished successfully. Verified **36 powered
trials, nine coast controls, and `Complete: True`** in the saved report.
All 36 powered trials are `ok`. Across the 32 new-state trials, there are
**four project-criterion passes** (one per candidate, all the same 100 m case)
and **zero strict passes**. Coast already meets the project criterion for that
case. Both terminal metrics improve versus coast in 7/8 new states for
`best_overall` and 6/8 for each other candidate.

Final inclined-target results (separation m, relative speed m/s):
- Overall: 34521.098, 11.231.
- Coarse: 17481.164, 13.465.
- Position: 3795.742, 6.901.
- Velocity: 17652.268, 8.959.

No rerun is needed. Reporting-wording reconciliation and any requested final
commit/push remain pending. The earlier status, process ID, results table and
next-action list below are preserved as historical snapshots, superseded by
this completion update where applicable.

### Historical in-progress snapshot
- `summary.txt` says `Complete: False`.
- 33/36 powered optimization trials saved: all four candidates on the original
  state and first seven new states, plus `best_overall` on the inclined target.
- Remaining: inclined-target `best_coarse`, `best_position`, `best_velocity`.
- All nine coast controls are saved.
- All 33 completed powered trials are `ok` (sampled surface-safe).
- An active Python process was confirmed: PID **40816**, command:
  `python -B -u validate_sweep_weights.py --output outputs/weight_validation_20261029`.
  PID and counts are snapshots; verify again before taking action.
- Background shell ID: `sh_18897ab17001Sc2wMgWEHxqyFP`.
- Do NOT start a second process against the existing output directory. Do NOT
  overwrite its files while the runner is active. The runner updates the report
  and raw outputs after every trial and marks `Complete: True` after all 36.

## Original sweep: complete
- 1,252 combinations: 1,000 coarse plus 252 additional refined combinations.
- 552 `ok`, 700 `error`; both sweep stages completed.
- A sweep `ok` is not successful rendezvous: it indicates a finite output that
  passes the sampled surface screen.
- Weight order is always **position, velocity, delta-v**.

| Candidate | Weights | Original final separation (m) | Original final relative speed (m/s) | Total delta-v (m/s) |
|---|---|---:|---:|---:|
| best_overall | (0.05, 50000, 250000) | 589358.494 | 299.374 | 999.749 |
| best_coarse | (0.01, 10000, 1000000) | 590151.313 | 298.570 | 998.919 |
| best_position | (0.05, 5000, 250000) | 586014.325 | 316.212 | 999.824 |
| best_velocity | (0.001, 100000, 1000000) | 1008913.686 | 143.281 | 704.011 |

These candidates were selected using source results only, before validation.
Raw weighted costs cannot be compared between different weight tuples. The
fixed cross-weight comparison is:

`(final_separation/100 m)^2 + (final_relative_speed/0.1 m/s)^2 + total_delta_v/(500 m/s)`.

## Validation method
- Four frozen weight candidates, nine cases = 36 full optimizer trials.
- Each state gets its own newly optimized burn schedule; original burn schedules
  are NOT applied unchanged to new states. This tests transfer of weights.
- Saved epoch: 2026-10-27 12:00:00 UTC; no new network ephemeris fetch.
- Same saved body states, Sun/Earth/Moon/Jupiter dynamics, 3,600 s duration,
  two burns, 1,000 samples per powered segment, and optimizer seed 42.
- Full existing differential-evolution defaults, not shortened test settings.
- Burn bounds: signed magnitude -500 to +500 m/s per burn, times 60 to 3540 s,
  strictly ordered. Original optimizer/dynamics were not modified.
- Coast control: no burns, 3,000 trajectory samples.
- Original state: chaser `[7000000,-500000,300000,0,7400,500]`,
  target `[7000000,0,0,0,7546,0]`.
- Eight new states: 100 m along-track; 1 km along-track; 10 km along-track with
  velocity error; 10 km radial with velocity error; 10 km cross-track; mixed
  approximately 100 km; higher target orbit (8,000 km radius); target inclined 20 degrees.
- All full six-component states are in the report/configuration, Earth-relative
  in metres and metres/second, J2000 ecliptic-aligned. Earth's saved inertial state
  is added for propagation.

## Success thresholds: important wording update needed
The validation originally used two explicit evaluation criteria:
- **Strict:** final separation <=100 m AND final relative speed <=0.1 m/s.
- **Loose:** final separation <=1,000 m AND final relative speed <=1 m/s.
- Both require sampled surface-safe output, and both use terminal metrics,
  not minimum flyby distance.

The user subsequently edited `report_outline.tex` to define project success as
**<=1,000 m AND <=1 m/s**, excluding final docking/approach. Therefore the report's
currently labelled "loose" criterion matches the user's project-success criterion.
When presenting final results, lead with the user's project criterion and retain
100 m / 0.1 m/s only as a stricter secondary diagnostic. Do not silently change the
historical experiment or state that all trials failed project success based only
on the stricter test. `summary.txt` currently still calls these evaluation choices
"not official mission requirements"; clarify the later report definition once
the process finishes, preferably by updating the generator then regenerating the
report from saved measurements without rerunning optimization.

## Results at the 33/36 snapshot
New states only (original control excluded):

| Candidate | New-state trials saved | Strict passes | Project-criterion passes (currently "loose") | Both final metrics better than coast |
|---|---:|---:|---:|---:|
| best_overall | 8 | 0 | 1 | 7 |
| best_coarse | 7 | 0 | 1 | 5 |
| best_position | 7 | 0 | 1 | 5 |
| best_velocity | 7 | 0 | 1 | 5 |

- No strict successes among the 29 new-state trials saved so far.
- The project-criterion passes so far are all the 100 m initial-offset case:
  approximately 255 m terminal separation, 0.218-0.241 m/s relative speed,
  essentially zero delta-v. Coast also passes that criterion (256.741 m,
  0.201 m/s). Do not claim these successes demonstrate meaningful active control.
- Original control exactly reproduced saved source winner metrics. Its coast
  intersects Earth's sampled surface, so its terminal coast metrics describe
  point-mass continuation, not a physically flyable trajectory.
- Overall weights on the 10 km along-track case: 3,525.937 m and 5.574 m/s,
  delta-v 30.345 m/s, versus coast 91,560.036 m and 83.754 m/s. Strong improvement,
  but neither project success nor strict success.
- Cross-track runs approach within about 67-76 m at an intermediate time but
  finish about 13.64 km apart: flyby proximity is not terminal rendezvous.
- Higher-orbit position weights: 4,249.148 m and 8.368 m/s; still not success.
- Inclined-target overall weights: 34,521.098 m and 11.231 m/s; still not success.
- All conclusions are provisional until the last three trials finish.

## Caveats to preserve
1. `burn_size` uses the FULL inertial spacecraft velocity, including Earth's
   Sun-frame velocity. Burns are not general 3-axis controls and are not
   necessarily tangential to Earth-relative motion. Do not fix this as part of
   reporting; that would change the experiment. It is a candidate future study.
2. DOP853 uses existing `rtol=1e-6` in large Sun-frame coordinates. No independent
   tighter-tolerance verification has been done. Near-zero-burn cases show
   different terminal outcomes due to segment restarts/numerics; metre/sub-metre
   differences and tiny speed improvements must not be overinterpreted.
3. Invalid-order penalty `1e12` can be lower than valid high-weight costs.
   Validation rejects invalid burn outputs rather than counting them as successes.
4. Minima and collision checks are sampled, not continuous guarantees.
5. One deterministic seed, hand-selected states, no Monte Carlo reliability claim.
6. Delta-v is a fuel proxy, not propellant mass; no atmosphere, navigation error,
   finite thrust duration or collision-avoidance constraints.
7. One small coast-sampling issue to inspect before making precise minimum claims:
   the existing `trajectory` empty-burn path appends its final segment from index 1,
   omitting t=0 for coast. Powered/coast sample grids also differ. Terminal metrics
   are still included; do not mistake sampled coast minima for continuous minima.

## Files and report generation
The runner writes:
- `configuration.json`: source metadata, candidate source rows, full states.
- `results.csv`: one row per completed powered trial, flushed each time.
- `results.json`: powered trials and coast metrics.
- `summary.txt`: all states, weights, burns, final/minimum metrics, sampled
  altitude, coast comparisons, aggregate results, and limitations.

`write_report(output, configuration, trials, coasts, complete)` is a pure reporting
entry point in `validate_sweep_weights.py`. After the process stops, saved JSON can
be loaded and passed to this function to regenerate text without optimization.
Preserve the actual completeness flag; do not mark an interrupted batch complete.

There is **no resume option for the validation runner**. It refuses an existing
output directory. If interrupted, first preserve existing data, then either add
a carefully tested resume path or rerun in a NEW directory. The ORIGINAL
`weight_sweep.py` does support `--resume`, but the source sweep is already complete
and should not be restarted for this task.

## Tests and commands
All 23 tests passed before production execution:

```powershell
python -B -m unittest discover -s tests -v
```

Production command (already running; do not duplicate):

```powershell
python -B -u validate_sweep_weights.py --output outputs/weight_validation_20261029
```

Check live Python commands before considering restart:

```powershell
Get-CimInstance Win32_Process -Filter "name = 'python.exe'" | Select-Object ProcessId, CommandLine
```

Fresh reproduction, only if explicitly needed, using a NEW output directory:

```powershell
python -B -u validate_sweep_weights.py --output outputs/weight_validation_NEW_RUN
```

## Git and user-work protection
- Branch: `main`, remote `origin`.
- Last push requested by user succeeded: **`1f8a10d`**, message
  `Add weight generalization validation and update rendezvous report`.
- That commit contains an INCOMPLETE results snapshot. Later production results
  have modified `results.csv`, `results.json`, and `summary.txt` locally and have
  not been pushed by this handoff task.
- Existing unrelated generated changes were intentionally excluded from push:
  `__pycache__/celestial_body_simulator.cpython-314.pyc`, `out/report_outline.log`.
  Do not revert or discard them.
- Preserve the user's ongoing `report_outline.tex` prose and equations. We added
  the Sun/Earth/Moon/Jupiter parameter table at the requested location, using
  `celestial_body_simulator.py`: 1.3271e20, 3.986e14, 4.9028e12, 1.2671e17 m^3/s^2.
- Do not assume this handoff authorizes another commit/push or physics changes.

## Next actions
1. Let the active validation process finish; inspect `Complete` and confirm
   36 powered rows and nine coast controls after completion.
2. Reconcile report success wording with the user's 1 km / 1 m/s definition,
   retaining strict diagnostics and clearly identifying coast-already-successful cases.
3. Present the complete table: scenario, candidate, final separation, final relative
   speed, delta-v, surface status, project success; add coast rows for comparison.
4. Point the user to the finalized separate `summary.txt`. Keep raw results intact.
5. Update session notes/current task and this snapshot as appropriate. Push final
   results only when requested. Do not imply the earlier push included later results.
