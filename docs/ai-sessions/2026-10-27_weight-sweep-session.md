# Coarse-to-fine rendezvous weight testing

## Request and scope
Create a separate test program sweeping each of the three weights from 0.001 to 1,000,000 by powers of ten, then refine around the selected orders using quarter steps. Keep a constant, substantially separated target/chaser pair. Do not change existing production code except to accept weights as a `main` argument.

## Implementation
- Added `weight_sweep.py`, using existing `rendezvous` and `trajectory` functions directly without trial plots or interactive prompts.
- Coarse stage tests the full Cartesian product: 10 values per weight, 1,000 combinations. Refined stage takes each winning coarse weight times `[0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]`, retaining the overall 0.001–1,000,000 bounds. For 100 this is exactly 25,50,75,100,250,500,750,1000. Skip tuples already evaluated.
- Fixed Earth-relative initial states: chaser `[7000000,-500000,300000,0,7400,500]`, target `[7000000,0,0,0,7546,0]`. Default duration 3600 seconds, two burns, epoch 2026-10-27 12:00:00 UTC. Fetch starting body states once and propagate bodies once per sweep.
- Rank successful sampled-surface-clear trials using a weight-independent dimensionless score: `(final_distance / 100 m)^2 + (final_speed / 0.1 m/s)^2 + total_delta_v / 500 m/s`. Scales are configurable; this is an explicit preference, not a proof of universally ideal weights or enforced constraints.
- Save configuration and initial ephemeris to JSON, incremental results to CSV, and summary/best tuple to JSON in a fresh timestamped `outputs/weight_sweep_*` directory (or a new `--output` directory). Record errors per trial. Ctrl+C preserves completed trials and creates a partial summary.
- CSV includes weights, stage, status, final/minimum sampled separation, time of minimum, final relative speed, total delta-v, fixed comparison score, sampled minimum altitude, original costs, burn parameters and runtime.
- Changed only weight intake in existing production code: `Multiple_Gravitational_Objects.main(weights)` and three required CLI weights. Adjusted its existing test to supply weights. No changes to the gravity model, optimizer, cost function or body simulator.
- Added `tests/test_weight_sweep.py`.

## Usage
```powershell
python weight_sweep.py --dry-run
python weight_sweep.py --max-runs 3
python weight_sweep.py
python weight_sweep.py --position-scale 1000 --velocity-scale 1 --fuel-scale 500
python Multiple_Gravitational_Objects.py 0.0001 100 0.002
```

The full sweep is potentially very expensive: 1,000 coarse optimizations plus up to 512 refined candidates before deduplication. `--max-runs` produces partial results; it is not a reduced-grid estimate of the full optimum. The default optimizer settings and seed remain unchanged.

## Validation
- Sixteen unit/integration tests passed with `python -B -m unittest discover -s tests -v`.
- Tested exact grids and boundary clipping, fixed ranking, failure/interrupt preservation, no duplicate tuples, coarse-to-refined sequencing, one-time ephemeris acquisition, dry-run behavior and a real trial using a one-generation optimizer in the test only.
- CLI help and dry-run tested. Full production sweep was not executed.

## Limitations
- Existing invalid-burn penalty is 1e12; valid raw objectives can exceed it at high weights. Invalid returned burns are recorded/excluded; the original optimizer is not changed.
- Surface intersections are screened at stored samples, not continuously. This is not collision-event detection or a feasibility guarantee between samples.
- Only the best valid coarse tuple is refined. Uniformly scaled weights are theoretically redundant, but all requested coarse tuples are still evaluated.
- Delta-v is a proxy for fuel, not propellant mass. Results depend on comparison references, scenario and the existing optimizer/burn-direction model.
