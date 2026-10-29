# Computational method sections and Earth-relative burns

## Goal and changes
- Replace only the Computational Method outline in `report_outline.tex` with prose matching the existing first-person explanation, based on the two current rendezvous scripts and their body-simulator dependency.
- Describe propagation, initial-state conversion, burn representation, costs, differential evolution settings, and plotting.
- At the user's explicit request, update `Multiple_Gravitational_Objects.py` so both scoring and trajectory reconstruction resolve burns along spacecraft velocity minus Earth's velocity at the burn time.
- Add `tests/test_earth_relative_burns.py` and record the modelling decision in `docs/decisions/decisions.md`.

## Validation
- `python -m unittest discover -s tests -v`: 24 tests passed.
- New analytic force-free test checks positive, negative, and zero burns, time-dependent Earth velocity, and invariance to a common velocity offset. Both scoring and trajectory reconstruction match expected terminal errors.
- `git diff --check`: passed.
- Computational Method section compiled in a temporary standalone document, rendered to three pages, and visually inspected. References to earlier report equations remain unresolved in this isolated preview.

## Existing issues and next actions
- Full-report compilation already failed before these edits because of a trailing line break after the title declaration. Earlier sections also contain equation syntax that was outside the requested edit; no changes were made there.
- Previous 3D optimization results used the old burn directions. They were preserved and have not been rerun.
- No full production optimization or network ephemeris fetch was needed for this change.
