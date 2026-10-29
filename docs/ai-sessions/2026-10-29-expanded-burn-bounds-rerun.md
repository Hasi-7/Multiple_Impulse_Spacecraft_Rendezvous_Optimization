# Expanded 3D burn bounds

- User changed 3D optimizer bounds to +/-1000 m/s and updated the report's displayed equation. Preserved these changes; original 2D optimizer still uses +/-500 m/s.
- Added `MAX_BURN_DELTA_V = 1000.0` to the 3D model and used it for both optimizer bounds and sweep burn validation. Saved the limit in new sweep metadata and made generated validation reports read that value (historical fallback 500).
- Updated the report's sentence to distinguish the 2D and 3D bounds. Left the cross-weight comparison fuel scale unchanged, since it is an evaluation scale rather than a per-burn constraint.
- Regression checks accept burns exactly at +/-1000 m/s and reject a 1000.001 m/s burn. All 28 unit tests passed and `git diff --check` passed.
- Stopped the verified Python PID 37116 running the old fixed-Sun +/-500 sweep. Preserved 128 readable rows and marked `outputs/corrected_experiments_20261029_142048.status.json` superseded.
- New visible terminal PID 31880, tag `20261029_144240`, runs the full fixed-Sun +/-1000 sweep, followed automatically by 36 powered validations and nine coasts. Saved initial body states and all other experiment settings remain unchanged.
- Status and outputs are recorded in `context/current-task.md`. Production is running, not complete. No commit or push performed; do not start duplicate batches.
