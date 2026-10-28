"""Coarse-to-fine weight testing without changing the rendezvous algorithm.

    python weight_sweep.py --dry-run
    python weight_sweep.py --max-runs 3
    python weight_sweep.py
    python weight_sweep.py --resume outputs/weight_sweep_DIRECTORY

The default sweep runs 1,000 coarse combinations, then refines around the
best successful coarse combination. Each trial invokes the existing optimizer
with its existing settings/seed. This can take a very long time. Results are
flushed to CSV after every trial, and partial results survive Ctrl+C.

Raw weighted costs are NOT comparable across different weight tuples. Ranking
instead uses fixed, configurable position/velocity/delta-v reference scales.
These references express preferences, not enforced mission constraints.
"""

import argparse
import csv
from datetime import datetime
import itertools
import json
from pathlib import Path
import shutil
import time

import numpy as np

import celestial_body_simulator as system
import Multiple_Gravitational_Objects as model


COARSE_VALUES = tuple(10.0**exponent for exponent in range(-3, 7))
# Earth-relative states, J2000 ecliptic-aligned, in metres and metres/second.
# Initial separation ~583 km; both relative position and velocity differ.
CHASER_STATE = np.array([7_000_000, -500_000, 300_000, 0, 7400, 500], dtype=float)
TARGET_STATE = np.array([7_000_000, 0, 0, 0, 7546, 0], dtype=float)
DEFAULT_REFERENCES = (100.0, 0.1, 500.0)
FIELDS = (
    "stage", "w_position", "w_velocity", "w_delta_v", "status", "message",
    "final_separation_m", "minimum_sampled_separation_m", "minimum_time_s",
    "final_relative_speed_m_s", "total_delta_v_m_s", "comparison_score",
    "minimum_sampled_surface_altitude_m", "optimizer_score", "trajectory_score",
    "burns_json", "elapsed_s",
)


def refinement_values(centre):
    """For 100 return 25,50,75,100,250,500,750,1000; enforce sweep bounds."""
    candidates = (centre * factor for factor in (0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10))
    return tuple(value for value in candidates if COARSE_VALUES[0] <= value <= COARSE_VALUES[-1])


def comparison_score(separation, relative_speed, delta_v, references):
    """Dimensionless evaluation held constant across every optimizer trial."""
    position_scale, velocity_scale, fuel_scale = references
    return (separation / position_scale)**2 + (relative_speed / velocity_scale)**2 + delta_v / fuel_scale


def validate_burns(burns, duration):
    """Reject invalid outputs, including penalty-plateau optimizer results."""
    if not np.all(np.isfinite(burns)):
        raise ValueError("Optimizer returned nonfinite burns.")
    times = burns[:, 1]
    if (np.any(times < 60) or np.any(times > duration - 60)
            or np.any(np.diff(times) <= 0) or np.any(np.abs(burns[:, 0]) > 500)):
        raise ValueError("Optimizer returned out-of-bounds or unordered burns.")


def sampled_surface_altitude(states, times, body_solution):
    """Screen sampled spacecraft paths for penetration of any body surface.

    This is not continuous collision detection: crossings between samples may
    be missed. It does not alter the dynamics or the existing optimizer.
    """
    bodies = body_solution.sol(times).reshape(len(system.BODY_NAMES), 6, -1)
    displacement = states[:, :3].T[None, :, :] - bodies[:, :3]
    altitudes = np.linalg.norm(displacement, axis=1) - system.BODY_RADII[:, None]
    return float(altitudes.min())


def run_trial(weights, chaser, target, bodies, duration, num_burns, samples, references):
    """Use existing public functions; do not prompt or generate trial plots."""
    parameters, optimizer_score = model.rendezvous(
        chaser.copy(), target.copy(), num_burns, weights, (0, duration), bodies,
    )
    burns = np.asarray(parameters).reshape(num_burns, 2)
    validate_burns(burns, duration)
    history, trajectory_score, _ = model.trajectory(
        chaser.copy(), target.copy(), (0, duration), burns, weights, bodies,
        samples_per_segment=samples,
    )
    times, states, target_solution, _, _ = history
    if (times[-1] != duration or not target_solution.success
            or not np.all(np.isfinite(states))):
        raise ValueError("Trajectory did not produce a finite full-duration result.")
    target_states = target_solution.sol(times).T
    if not np.all(np.isfinite(target_states)):
        raise ValueError("Target trajectory contains nonfinite values.")
    separation = np.linalg.norm(states[:, :3] - target_states[:, :3], axis=1)
    minimum_index = int(np.argmin(separation))
    relative_speed = float(np.linalg.norm(states[-1, 3:] - target_states[-1, 3:]))
    fuel = float(model.fuel_usage(burns))
    altitude = min(sampled_surface_altitude(states, times, bodies),
                   sampled_surface_altitude(target_states, times, bodies))
    if not np.all(np.isfinite([optimizer_score, trajectory_score, relative_speed, fuel, altitude])):
        raise ValueError("Trial produced nonfinite metrics.")
    ranking_score = comparison_score(float(separation[-1]), relative_speed, fuel, references)
    if not np.isfinite(ranking_score):
        raise ValueError("Comparison score is nonfinite.")
    return {
        "status": "ok" if altitude > 0 else "surface_intersection",
        "message": "" if altitude > 0 else "Sampled path touches or enters a body; excluded from ranking.",
        "final_separation_m": float(separation[-1]),
        "minimum_sampled_separation_m": float(separation[minimum_index]),
        "minimum_time_s": float(times[minimum_index]),
        "final_relative_speed_m_s": relative_speed,
        "total_delta_v_m_s": fuel,
        "comparison_score": ranking_score,
        "minimum_sampled_surface_altitude_m": altitude,
        "optimizer_score": float(optimizer_score),
        "trajectory_score": float(trajectory_score),
        "burns_json": json.dumps(burns.tolist()),
    }


def select_best(rows):
    valid = [row for row in rows if row["status"] == "ok"]
    return min(valid, key=lambda row: row["comparison_score"]) if valid else None


def load_checkpoint(directory):
    """Read and validate saved trials before opening the results for append."""
    metadata = json.loads((directory / "configuration.json").read_text(encoding="utf-8"))
    initial = np.asarray(metadata["initial_body_states_si"], dtype=float)
    if initial.shape != (len(system.BODY_NAMES), 6) or not np.all(np.isfinite(initial)):
        raise ValueError("Saved body states are invalid.")
    for key in ("chaser_earth_relative_si", "target_earth_relative_si"):
        state = np.asarray(metadata[key], dtype=float)
        if state.shape != (6,) or not np.all(np.isfinite(state)):
            raise ValueError(f"Invalid saved state: {key}")
    if tuple(metadata["coarse_values"]) != COARSE_VALUES:
        raise ValueError("Saved coarse grid differs from the current grid; refusing to mix runs.")
    references = np.asarray(metadata["comparison_references_m_m_s_m_s"], dtype=float)
    if references.shape != (3,) or not np.all(np.isfinite(references)) or np.any(references <= 0):
        raise ValueError("Invalid saved comparison scales.")
    if (not np.isfinite(metadata["duration_s"]) or metadata["duration_s"] <= 120
            or not isinstance(metadata["number_of_burns"], int) or metadata["number_of_burns"] < 1
            or not isinstance(metadata["samples_per_segment"], int) or metadata["samples_per_segment"] < 2):
        raise ValueError("Invalid saved duration, burn count or sample count.")
    rows = []
    seen = set()
    text_fields = {"stage", "status", "message", "burns_json"}
    with (directory / "results.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Saved CSV header differs from the current results format.")
        for number, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Incomplete CSV row {number}; no saved data was modified.")
            for key, value in row.items():
                if key not in text_fields and value != "":
                    row[key] = float(value)
                    if not np.isfinite(row[key]):
                        raise ValueError(f"Nonfinite value in saved CSV row {number}.")
            weights = tuple(row[key] for key in ("w_position", "w_velocity", "w_delta_v"))
            if (any(not isinstance(value, float) or value <= 0 for value in weights)
                    or weights in seen or row["stage"] not in ("coarse", "refined")
                    or row["status"] not in ("ok", "error", "surface_intersection")):
                raise ValueError(f"Invalid or duplicate saved trial at CSV row {number}.")
            if row["status"] == "ok" and not isinstance(row["comparison_score"], float):
                raise ValueError(f"Missing comparison score at CSV row {number}.")
            seen.add(weights)
            rows.append(row)
    # A truncated last line must never be concatenated with a new trial.
    with (directory / "results.csv").open("rb") as stream:
        stream.seek(-1, 2)
        if stream.read(1) != b"\n":
            raise ValueError("Saved CSV has no final newline; refusing to append to a partial file.")
    return metadata, rows


def positive_float(value):
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("Must be positive and finite.")
    return value


def positive_int(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError("Must be a positive integer.")
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--epoch", default=system.DEFAULT_EPOCH)
    parser.add_argument("--duration", type=positive_float, default=3600.0, help="Seconds, greater than 120 (default: 3600)")
    parser.add_argument("--burns", type=positive_int, default=2)
    parser.add_argument("--samples", type=positive_int, default=1000, help="Samples per trajectory segment")
    parser.add_argument("--position-scale", type=positive_float, default=DEFAULT_REFERENCES[0], help="Fixed comparison scale in metres")
    parser.add_argument("--velocity-scale", type=positive_float, default=DEFAULT_REFERENCES[1], help="Fixed comparison scale in m/s")
    parser.add_argument("--fuel-scale", type=positive_float, default=DEFAULT_REFERENCES[2], help="Fixed comparison scale in total delta-v m/s")
    parser.add_argument("--max-runs", type=positive_int, help="Cap total saved trials, including previous trials when resuming")
    parser.add_argument("--dry-run", action="store_true", help="Show configuration without network requests or optimization")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--output", type=Path, help="New output directory; existing directories are not overwritten")
    destination.add_argument("--resume", type=Path,
                             help="Append to a saved run; restores its scenario/scales, overriding scenario flags")
    args = parser.parse_args(argv)
    if args.duration <= 120:
        parser.error("--duration must be greater than 120 seconds.")
    if args.samples < 2:
        parser.error("--samples must be at least 2.")
    try:
        system.epoch_to_jd(args.epoch)
    except ValueError:
        parser.error("--epoch must be YYYY-MM-DD HH:MM:SS.")
    return args


def run_sweep(args):
    rows = []
    if args.resume is not None:
        metadata, rows = load_checkpoint(args.resume)
        args.epoch = metadata["epoch_utc"]
        args.duration = metadata["duration_s"]
        args.burns = metadata["number_of_burns"]
        args.samples = metadata["samples_per_segment"]
        args.position_scale, args.velocity_scale, args.fuel_scale = metadata["comparison_references_m_m_s_m_s"]
        chaser_relative = np.asarray(metadata["chaser_earth_relative_si"])
        target_relative = np.asarray(metadata["target_earth_relative_si"])
        print(f"Restoring saved scenario and scales; {len(rows)} completed trials will be skipped.", flush=True)
    else:
        chaser_relative = CHASER_STATE
        target_relative = TARGET_STATE
    references = (args.position_scale, args.velocity_scale, args.fuel_scale)
    if args.resume is None:
        metadata = {
            "epoch_utc": args.epoch,
            "duration_s": args.duration,
            "number_of_burns": args.burns,
            "samples_per_segment": args.samples,
            "max_runs": args.max_runs,
            "chaser_earth_relative_si": CHASER_STATE.tolist(),
            "target_earth_relative_si": TARGET_STATE.tolist(),
            "initial_separation_m": float(np.linalg.norm(CHASER_STATE[:3] - TARGET_STATE[:3])),
            "initial_relative_speed_m_s": float(np.linalg.norm(CHASER_STATE[3:] - TARGET_STATE[3:])),
            "coarse_values": COARSE_VALUES,
            "coarse_combinations": len(COARSE_VALUES)**3,
            "maximum_refined_combinations_before_deduplication": 8**3,
            "comparison_references_m_m_s_m_s": references,
            "ranking": "(final_separation / position_scale)^2 + (final_relative_speed / velocity_scale)^2 + total_delta_v / fuel_scale",
            "optimizer": "Existing rendezvous() settings, including seed 42; unchanged",
            "notes": [
                "Raw optimizer/trajectory costs with different weights are not comparable.",
                "Only the best coarse tuple is refined; this is not a guarantee of globally ideal weights.",
                "Uniform scaling of all weights is theoretically redundant; all requested tuples are still tested.",
                "Minimum separation and surface screening use sampled positions, not continuous extrema/events.",
                "The existing 1e12 invalid-burn penalty can be cheaper than valid high-weight costs; invalid outputs are recorded and excluded.",
                "Total delta-v is a fuel proxy, not propellant mass. No new optimizer constraints are imposed.",
            ],
        }
    print(json.dumps(metadata, indent=2))
    if args.dry_run:
        return None

    output = args.resume or args.output or Path("outputs") / ("weight_sweep_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    if args.resume is None and output.exists():
        raise FileExistsError(f"Output path already exists: {output}")
    if args.resume is not None:
        print("Reusing saved initial ephemeris and propagating bodies once...", flush=True)
        initial = np.asarray(metadata["initial_body_states_si"], dtype=float)
    else:
        print("Fetching one initial ephemeris and propagating bodies once...", flush=True)
        initial = system.get_initial_states(args.epoch)
    bodies = system.simulate_system(initial, args.duration)
    chaser = chaser_relative + initial[1]
    target = target_relative + initial[1]
    if args.resume is None:
        metadata["initial_body_states_si"] = initial.tolist()
        output.mkdir(parents=True, exist_ok=False)
        (output / "configuration.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    elif (output / "summary.json").exists():
        backup = "summary_before_resume_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json"
        shutil.copy2(output / "summary.json", output / backup)

    seen = {tuple(row[key] for key in ("w_position", "w_velocity", "w_delta_v")) for row in rows}
    completed_stages = []
    stop_reason = "completed"
    with (output / "results.csv").open("a" if args.resume is not None else "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if args.resume is None:
            writer.writeheader()
        stream.flush()

        def evaluate(stage, combinations):
            for weights in combinations:
                if weights in seen:
                    continue
                if args.max_runs is not None and len(rows) >= args.max_runs:
                    return False
                seen.add(weights)
                started = time.perf_counter()
                print(f"Trial {len(rows) + 1} [{stage}] weights={weights}", flush=True)
                row = dict(stage=stage, w_position=weights[0], w_velocity=weights[1], w_delta_v=weights[2])
                try:
                    row.update(run_trial(weights, chaser, target, bodies, args.duration,
                                         args.burns, args.samples, references))
                except Exception as exc:
                    # Preserve each failed trial rather than losing the batch.
                    row.update(status="error", message=f"{type(exc).__name__}: {exc}")
                row["elapsed_s"] = time.perf_counter() - started
                writer.writerow(row)
                stream.flush()
                rows.append(row)
                print(f"  {row['status']}; final={row.get('final_separation_m', 'n/a')} m; "
                      f"speed={row.get('final_relative_speed_m_s', 'n/a')} m/s; "
                      f"delta-v={row.get('total_delta_v_m_s', 'n/a')} m/s", flush=True)
            return True

        try:
            if evaluate("coarse", itertools.product(COARSE_VALUES, repeat=3)):
                completed_stages.append("coarse")
                best_coarse = select_best([row for row in rows if row["stage"] == "coarse"])
                if best_coarse is not None:
                    centres = tuple(best_coarse[key] for key in ("w_position", "w_velocity", "w_delta_v"))
                    axes = [refinement_values(value) for value in centres]
                    print(f"Refining around coarse weights {centres}: {axes}", flush=True)
                    if evaluate("refined", itertools.product(*axes)):
                        completed_stages.append("refined")
                    else:
                        stop_reason = "max_runs"
                else:
                    stop_reason = "no_valid_coarse_trials"
            else:
                stop_reason = "max_runs"
        except KeyboardInterrupt:
            stop_reason = "interrupted"
            print("\nInterrupted; saving completed results.")

    summary = {
        "stop_reason": stop_reason,
        "completed_stages": completed_stages,
        "trials_completed": len(rows),
        "valid_trials": sum(row["status"] == "ok" for row in rows),
        "best": select_best(rows),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Results saved to {output}")
    if summary["best"] is not None:
        best = summary["best"]
        print(f"Best tested weights: ({best['w_position']}, {best['w_velocity']}, {best['w_delta_v']})")
        print(f"Final separation: {best['final_separation_m']:.3f} m; "
              f"relative speed: {best['final_relative_speed_m_s']:.6f} m/s; "
              f"total delta-v: {best['total_delta_v_m_s']:.3f} m/s")
    else:
        print("No valid completed trials to rank; inspect results.csv for errors.")
    return summary


if __name__ == "__main__":
    run_sweep(parse_args())
