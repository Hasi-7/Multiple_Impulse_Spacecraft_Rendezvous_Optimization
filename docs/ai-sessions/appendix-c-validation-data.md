# Full validation-data appendix

- User requested creating the actual Appendix C referred to in Section 5 and populating it with the relevant data.
- Changed the literal Appendix C reference to a numbered LaTeX cross-reference and added an input for the generated appendix after Appendix B. Verified the main source exactly matches a pre-edit snapshot except for those two requested changes.
- `build_validation_appendix.py` reads the saved completed fixed-Sun +/-1000 configuration and results. It checks nine cases, four candidates, 36 unique powered records and nine controls; validates weights against the selected candidates, burn count/order/bounds, and total delta-v consistency. No optimization, physics, or raw-record changes.
- Appendix C includes shared settings, four weight tuples, saved initial body states, all spacecraft initial states, terminal metrics, closest approach/time, sampled surface clearance/status, two signed burns/times per attempt, objective/reconstructed costs, common comparison score and saved elapsed time. Nine no-burn controls are included. The unsafe original coast is explicitly labelled; numerical rechecks and their unmeasured runtimes remain distinct.
- Values are rounded for readability and the full-precision JSON location is provided. One page per initial-state case keeps the tables together. Generated source is in the existing validation output directory.
- Compiled to `out/report_outline.pdf`, synchronized root PDF, checked appendix layout and cross-reference C, and verified no LaTeX box or unresolved-reference warnings. Final PDF has 25 pages. Existing trailing spaces in user prose were left intact.
- No commit or push performed.
