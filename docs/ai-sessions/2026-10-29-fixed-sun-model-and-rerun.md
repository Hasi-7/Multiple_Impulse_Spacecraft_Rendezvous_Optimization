# Physically fixed Sun and separate experiment restart

- User requested simplifying the model by physically fixing the Sun. Updated `celestial_body_simulator.py` to keep all Sun derivatives zero; reject initial states where the Sun is not at rest at the origin. Retained 24-state storage, gravity from the Sun, mutual gravity of the moving bodies, Earth-relative burns, and search settings.
- Updated only relevant assumptions and computational-method prose in `report_outline.tex`, with body-model metadata and validation report text identifying the new approximation. No claims of preserved total momentum; tests check a fixed Sun, Earth acceleration and stationary-source energy consistency.
- Expanded sweep model fingerprints to include the body simulator as well as spacecraft code; validation uses the same fingerprint. Added a regression test for changes to the body model.
- Stopped the specifically verified Python sweep PID 22748. Preserved 75 readable completed trials under `outputs/weight_sweep_earth_relative_20261029_140808`; marked its status superseded. No old output rows were deleted or merged into new data.
- All 28 unit tests passed. `git diff --check` passed. Existing report compilation errors outside edited prose remain unchanged.
- Launched fresh visible terminal PID 7828 with tag `20261029_142048`, titled `Spacecraft rendezvous - fixed Sun sweep and validation`. Uses saved initial planetary states but recomputes their trajectories under the new dynamics.
- New sweep: `outputs/weight_sweep_fixed_sun_20261029_142048`. Automatic validation destination: `outputs/weight_validation_fixed_sun_20261029_142048`. Status: `outputs/corrected_experiments_20261029_142048.status.json`.
- Production is running, not complete. No commit or push performed. Leave the new terminal running and verify saved counts/report before reporting experiment completion.
