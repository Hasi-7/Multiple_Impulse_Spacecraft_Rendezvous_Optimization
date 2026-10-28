# Resume interrupted weight sweep

## Request
Continue the saved weight sweep interrupted during trial 298.

## Saved run
`outputs/weight_sweep_20261027_200627_547397` contains 297 completed coarse trials. Both the CSV and saved summary confirm that trial 298 had not finished.

## Changes
- Added `--resume DIRECTORY` to `weight_sweep.py`.
- Validate the saved configuration and CSV before appending. Restore numeric CSV fields for correct ranking and skip every recorded weight tuple, including failed trials.
- Restore the exact saved initial body states, spacecraft states, duration, burn count, sample count and comparison references. No fresh Horizons request is required.
- Preserve original configuration and CSV rows, append new results, and back up the previous summary before replacing it at completion/interruption.
- Refined-stage resumption always derives its search grid from the best coarse result, not a previously saved refined result.
- `--max-runs` caps total saved trials, including those from earlier invocations. Without that flag a resumed run continues through the remaining coarse and refined stages.
- Do not run multiple processes against the same output directory. Resume assumes the underlying model/optimizer code has not changed since the original run.

## Validation
- Nineteen tests passed, including resume/deduplication, reuse of saved ephemeris, preservation of existing CSV/configuration and summary backup, refined-stage continuity, and safe rejection of a truncated CSV.
- Dry-run of the actual saved directory successfully validated all 297 trials.
- Checked Python processes before restarting; no active production sweep was found.

## Resume command
```powershell
python -B -u weight_sweep.py --resume outputs/weight_sweep_20261027_200627_547397
```

The resumed production sweep is launched in the background with output redirected to a timestamped `resume_*.log` inside the saved run directory. Completion is not implied by this session note.
