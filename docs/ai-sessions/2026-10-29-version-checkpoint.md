# Current-version save checkpoint

- User explicitly requested committing and pushing the current version.
- Snapshot includes fixed-Sun dynamics, Earth-relative burns, infinite invalid-time penalties, shared 3D +/-1000 m/s bound, sweep/validation reproducibility guards, all 28 passing code tests, report prose and syntax fixes, compiled PDFs in the repository root and `out`, launch script and continuation notes.
- Preserved interrupted experiments: 75 moving-Sun/Earth-relative trials and 128 fixed-Sun +/-500 m/s trials.
- Active run: `outputs/weight_sweep_fixed_sun_20261029_144240`; terminal PID 31880, Python PID 31888. At staging, its CSV contained only the header (zero completed trials); configuration and stage/status/log files are saved. This is an in-progress checkpoint, not a completed experiment.
- All three staged CSVs were checked for complete records and final newlines. Source/code/document whitespace checks passed; generated LaTeX build logs are saved as generated.
- Root and `out/report_outline.pdf` compiled successfully to seven pages. VS Code's local compiler path was corrected outside the repository; that personal editor setting is not part of Git.
- Section 4 and Section 5 follow-up is recorded in `context/current-task.md`. User will write Discussion and Conclusion. Do not restart an already-running experiment.
- Experiment output files may change after this checkpoint as the existing process continues; those later measurements will require a subsequent save.
