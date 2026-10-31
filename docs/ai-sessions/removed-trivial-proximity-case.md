# Exclusion of the 100 m initial-offset validation case

- User explicitly requested removing this case from the report and test data because it already meets the success criterion without burns.
- Archived all original current-validation artifacts, plus the report source before filtering, in `outputs/weight_validation_fixed_sun_20261029_144240/original_validation_including_100m_20261031_001251.zip`. Archive integrity/readability checked.
- Filtered the active configuration, results CSV/JSON and regenerated summary to remove the case's four powered rows and one coast control. Preserved every retained numeric trial/control record exactly; checked equality against the archive. Added exclusion provenance to the configuration. No new optimization or weight tuning.
- Updated future scenario generation and its regression check, plus launcher expected counts, to eight initial-state cases / 32 powered attempts / eight controls.
- Updated report counts, success tables, narrative, accuracy checks, figures and Appendix C. Original selection case remains excluded from new-state aggregate counts: overall weights pass 2/7; initial-search, position and velocity selections pass 0/7. Source sweep still has 1312 combinations and unchanged selected weights.
- Regenerated the retained-set numerical replays and all plots. The 32 retained classifications are unchanged, with both passing sequences also passing the final tighter check. Successful-trajectory figure now has only the 1 km and 10 km cases.
- All 28 unit tests passed. Raw historical runs outside this current-validation dataset remain historical evidence; no historical transcript was rewritten to pretend the excluded case was never run.
- Report compiled in `out`, visually checked, and synchronized to root. No commit or push performed.
