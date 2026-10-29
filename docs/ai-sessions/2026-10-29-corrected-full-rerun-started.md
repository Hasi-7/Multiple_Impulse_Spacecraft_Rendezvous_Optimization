# Corrected-model full rerun started

- User authorized rerunning all experiments and requested another terminal with visible progress.
- 3D score already contained the user's positive-infinity penalty edit. Preserved it, applied the same penalty in the planar script, and updated report wording.
- Added saved-ephemeris input and model fingerprint metadata/guards to the sweep; corrected validation report text and added a source-model fingerprint guard.
- Added tests for infinite invalid-time penalties, saved-state reuse without network access, and rejecting a resume from a different model. All 27 tests passed, including in the visible terminal.
- Launcher: `context/run-corrected-experiments.ps1`. Terminal PID 32716; title `Spacecraft rendezvous - corrected sweep and validation` confirmed on the Windows Terminal process. Python child runs the full sweep with no run cap.
- Run tag: `20261029_140808`. Status: `outputs/corrected_experiments_20261029_140808.status.json`. Transcript: corresponding `.log`. Per-trial results are flushed to sweep `results.csv`.
- Sweep destination: `outputs/weight_sweep_earth_relative_20261029_140808`. Uses the previous run's saved body starting states, 3600 s, two burns, existing search defaults and seed 42, all 1000 coarse tuples followed by refinement around the new winner.
- Automatically starts `validate_sweep_weights.py --source outputs/weight_sweep_earth_relative_20261029_140808 --output outputs/weight_validation_earth_relative_20261029_140808` only after sweep completion. That batch performs four candidate roles x nine states = 36 powered optimizations plus nine coasts.
- Previous outputs preserved; new data are a separate experiment. No commit or push performed. Do not label production complete until final saved report and counts are verified. Do not launch duplicate batches.
