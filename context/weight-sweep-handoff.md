# Weight sweep and validation report handoff

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
