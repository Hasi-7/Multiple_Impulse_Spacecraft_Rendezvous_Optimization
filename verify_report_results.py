"""Reproduce report checks and figures without running new optimizations."""
import json
from pathlib import Path
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp

import celestial_body_simulator as system
import Multiple_Gravitational_Objects as model
import Rendezvous_2_spacecrafts_orbit_Earth as planar
import weight_sweep


OUTPUT = Path("outputs/weight_validation_fixed_sun_20261029_144240")


def success(position, speed):
    return bool(position <= 1000 and speed <= 1)


def replay(configuration, trials, rtol, selected=None):
    metadata = configuration["source_configuration"]
    initial = np.asarray(metadata["initial_body_states_si"])
    cases = {s["name"]: s for s in configuration["scenarios"]}

    def precise(*args, **kwargs):
        kwargs.update(rtol=rtol, atol=1e-8)
        return solve_ivp(*args, **kwargs)

    rows = []
    with patch.object(system, "solve_ivp", side_effect=precise), \
         patch.object(model, "solve_ivp", side_effect=precise):
        bodies = system.simulate_system(initial, metadata["duration_s"])
        for row in trials:
            key = (row["scenario"], row["candidate"])
            if selected is not None and key not in selected:
                continue
            case = cases[row["scenario"]]
            history, _, _ = model.trajectory(
                np.asarray(case["chaser"]) + initial[1],
                np.asarray(case["target"]) + initial[1],
                (0, metadata["duration_s"]), np.asarray(json.loads(row["burns_json"])),
                (row["w_position"], row["w_velocity"], row["w_delta_v"]), bodies,
                samples_per_segment=metadata["samples_per_segment"],
            )
            times, states, target, _, _ = history
            terminal = target.sol(times[-1])
            position = float(np.linalg.norm(states[-1, :3] - terminal[:3]))
            speed = float(np.linalg.norm(states[-1, 3:] - terminal[3:]))
            altitude = min(weight_sweep.sampled_surface_altitude(states, times, bodies),
                           weight_sweep.sampled_surface_altitude(target.sol(times).T, times, bodies))
            rows.append(dict(scenario=key[0], candidate=key[1], rtol=rtol,
                             final_separation_m=position, final_relative_speed_m_s=speed,
                             minimum_sampled_surface_altitude_m=altitude,
                             project_pass=success(position, speed) and altitude > 0))
    return rows


def main():
    config = json.loads((OUTPUT / "configuration.json").read_text())
    assert config["source_configuration"]["model_sha256"] == weight_sweep.model_fingerprint()
    saved = json.loads((OUTPUT / "results.json").read_text())
    assert len(saved["trials"]) == 32 and len(saved["coasts"]) == 8
    radius = 7e6
    speed = np.sqrt(planar.mu / radius)
    period = 2 * np.pi * np.sqrt(radius**3 / planar.mu)
    times = np.linspace(0, period, 1000)
    circular = solve_ivp(planar.two_body_ode, (0, period), [radius, 0, 0, speed],
                         method="DOP853", rtol=1e-6, t_eval=times)
    analytical = radius * np.array([np.cos(times * speed / radius), np.sin(times * speed / radius)])
    position_errors = np.linalg.norm(circular.y[:2] - analytical, axis=0)
    energy = np.sum(circular.y[2:]**2, axis=0) / 2 - planar.mu / np.linalg.norm(circular.y[:2], axis=0)
    momentum = circular.y[0] * circular.y[3] - circular.y[1] * circular.y[2]
    tight = replay(config, saved["trials"], 1e-10)
    passing_keys = {(r["scenario"], r["candidate"]) for r in saved["trials"]
                    if success(r["final_separation_m"], r["final_relative_speed_m_s"])}
    tighter = replay(config, saved["trials"], 1e-12, passing_keys)
    results = dict(
        description="Independent fixed-schedule replays; no reoptimization or replacement of saved production results",
        circular_orbit=dict(radius_m=radius, period_s=float(period), rtol=1e-6, atol=1e-6,
                            maximum_position_error_m=float(position_errors.max()),
                            final_position_error_m=float(position_errors[-1]),
                            maximum_relative_energy_drift=float(np.max(np.abs((energy-energy[0])/energy[0]))),
                            maximum_relative_angular_momentum_drift=float(np.max(np.abs((momentum-momentum[0])/momentum[0])))),
        replay_atol=1e-8, tight_replays=tight, tighter_replays_of_production_passes=tighter,
    )
    (OUTPUT / "report_checks.json").write_text(json.dumps(results, indent=2) + "\n")
    cases = config["scenarios"][1:]
    selected = [next(r for r in saved["trials"] if r["scenario"] == s["name"] and r["candidate"] == "best_overall") for s in cases]
    labels = ["1 km\nalong-track", "10 km\nalong-track", "10 km\nradial", "10 km\ncross-track", "Mixed\n100 km", "Higher\norbit", "Inclined\ntarget"]
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)
    for ax, metric, threshold, ylabel in zip(axes,
            ("final_separation_m", "final_relative_speed_m_s"), (1000, 1),
            ("Final separation (m)", "Final relative speed (m/s)")):
        ax.plot(range(len(cases)), [saved["coasts"][s["name"]][metric] for s in cases], "o--", color="#7c8793", label="No burns")
        ax.plot(range(len(cases)), [r[metric] for r in selected], "s-", color="#176b87", label="Overall-winning weights")
        ax.axhline(threshold, color="#a74335", ls=":", label="Project threshold")
        ax.set(yscale="log", ylabel=ylabel)
        ax.grid(axis="y", alpha=.2)
    axes[0].legend(loc="upper left", fontsize=9)
    axes[1].set_xticks(range(len(cases)), labels)
    fig.tight_layout()
    fig.savefig(OUTPUT / "report_validation.png", dpi=200)
    plt.close(fig)
    metadata = config["source_configuration"]
    initial = np.asarray(metadata["initial_body_states_si"])
    bodies = system.simulate_system(initial, metadata["duration_s"])
    case = next(s for s in cases if s["name"] == "along_track_1km")
    row = next(r for r in selected if r["scenario"] == case["name"])
    history, _, _ = model.trajectory(
        np.asarray(case["chaser"]) + initial[1], np.asarray(case["target"]) + initial[1],
        (0, metadata["duration_s"]), np.asarray(json.loads(row["burns_json"])),
        (row["w_position"], row["w_velocity"], row["w_delta_v"]), bodies,
    )
    times, states, target, burn_times, _ = history
    difference = states - target.sol(times).T
    fig, axes = plt.subplots(2, 1, figsize=(8, 5.5), sharex=True)
    for ax, values, ylabel, threshold in zip(axes,
            (np.linalg.norm(difference[:, :3], axis=1), np.linalg.norm(difference[:, 3:], axis=1)),
            ("Separation (m)", "Relative speed (m/s)"), (1000, 1)):
        ax.plot(times / 60, values, color="#176b87")
        ax.axhline(threshold, color="#a74335", ls=":", label="Project threshold")
        for number, burn_time in enumerate(burn_times):
            ax.axvline(burn_time / 60, color="#7c8793", ls="--", alpha=.7,
                       label="Burn times" if number == 0 else None)
        ax.set(ylabel=ylabel)
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=9)
    axes[1].set_xlabel("Time (minutes)")
    fig.tight_layout()
    fig.savefig(OUTPUT / "report_success_history.png", dpi=200)
    plt.close(fig)
    print(json.dumps(results["circular_orbit"], indent=2))
    for row in tighter:
        print("Tighter replay:", row)


if __name__ == "__main__":
    main()
