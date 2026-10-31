# Current Task

## Current reported dataset excludes the trivial proximity case
At the user's request, removed the 100 m starting-offset scenario from the
current validation configuration, results CSV/JSON, numerical-check records,
summary, plots, Appendix C, report tables and future scenario generation.
The original complete validation files/report were archived as a ZIP inside
the same validation directory before filtering; exclusion provenance is recorded
in `configuration.json`. All 32 retained trial records and eight coast controls
match their original saved measurements exactly. No optimization was rerun.

Current analysis: original selection case plus seven new cases, four candidates,
32 retained powered attempts and eight no-burn controls. Overall weights pass
2/7 new cases; initial-search, position and velocity selections each pass 0/7.
Numerical checks now cover 32 retained schedules and both passing schedules
at the tighter setting. All 28 unit tests passed after updating the scenario test.
The 1,312-trial source weight sweep and its selected weights are unchanged.
The historical completion/count statements below describe the unfiltered batch.

## Successful-trajectory visuals added
Section 5 now includes an Earth-centred orbit view and target-relative close-up
for each of the three passing overall-weight cases (100 m, 1 km, 10 km). Saved
burn sequences are reused at original tolerances, with final 3D metrics verified
against the recorded results to absolute tolerance 1e-6. No optimization rerun.
`plot_successful_trajectories.py` generates vector PDF, PNG and verification JSON
in the existing validation output directory. Views are x-y projections with
start/end/burn markers; the 100 m case is labelled as passing without burns too.
Both report PDFs are compiled and synchronized; figure layout checked. New
visuals/report changes are not committed or pushed.

## Appendix C added
The user's Section 5 reference now uses `Appendix~\ref{app:validation_data}`.
Appendix C is generated from the saved validation configuration/results by
`build_validation_appendix.py` and included from the existing validation directory's
`appendix_validation_data.tex`. It contains shared settings/weights/body states,
all nine spacecraft starting-state pairs, all 36 burn schedules, terminal and
closest-approach measurements, surface checks, costs and recorded trial runtimes,
plus nine no-burn controls. Original results are distinguished from accuracy replays.
The root and `out` PDFs are synchronized, compiled and checked: 25 pages.
Only the requested reference and appendix inclusion changed in the existing report;
all other current user edits were preserved. These new changes are not pushed.

## Completion verified and report Sections 4/5 written
Verified saved completion of the fixed-Sun +/-1000 m/s experiment: 1,312 sweep
trials (all ok), 36 powered validation trials (all ok), nine coast controls,
and `Complete: True`. No Python experiment process remained, so no duplicate
batch was launched when the user asked to run the follow-up tests.

Sections 4 and 5 are now written in `report_outline.tex`; Discussion and Conclusion
were preserved exactly. Both root and `out/report_outline.pdf` contain the checked
13-page report. Implementation checks have been expanded and moved to Appendix B,
with a short cross-reference in Section 4; numerical checks stay in the main text.
`verify_report_results.py` reproduces the new numerical checks
and two figures. Evidence is in the validation directory's `report_checks.json`.
All 28 unit tests passed. All 36 fixed burn schedules were replayed at rtol=1e-10;
the five production passes were also checked at rtol=1e-12, and all still passed.
The 1 km overall case changes from 16.0 m production separation to 74.6 m on the
tighter recheck; the report explicitly separates production and recheck values.
Overall weights pass 3/8 new cases, including one case that already passes coast.
Do not call these empirical counts a general success probability.
No commit or push was performed for these new completed results/report sections.

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
Historical launch details below; both stages are now complete. Check live state
before starting any further process.

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
