"""Plot saved successful validation burns without running optimization."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import numpy as np

import celestial_body_simulator as system
import Multiple_Gravitational_Objects as model
import weight_sweep


DIRECTORY = Path("outputs/weight_validation_fixed_sun_20261029_144240")
CASES = [
    ("along_track_1km", "1 km initial offset"),
    ("along_track_10km_velocity_error", "10 km initial offset\nwith velocity error"),
]


def main():
    config = json.loads((DIRECTORY / "configuration.json").read_text())
    results = json.loads((DIRECTORY / "results.json").read_text())
    meta = config["source_configuration"]
    assert meta["model_sha256"] == weight_sweep.model_fingerprint()
    initial = np.asarray(meta["initial_body_states_si"])
    bodies = system.simulate_system(initial, meta["duration_s"])
    plt.rcParams.update({"font.size": 13, "axes.titlesize": 14,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(len(CASES), 2, figsize=(10.8, 8.2))
    target_color, chaser_color, burn_color = "#176b87", "#bb512d", "#333333"
    verification = []
    for (name, title), (orbit_ax, relative_ax) in zip(CASES, axes):
        case = next(s for s in config["scenarios"] if s["name"] == name)
        row = next(r for r in results["trials"] if r["scenario"] == name
                   and r["candidate"] == "best_overall")
        assert row["status"] == "ok" and row["final_separation_m"] <= 1000
        assert row["final_relative_speed_m_s"] <= 1
        burns = np.asarray(json.loads(row["burns_json"]))
        weights = (row["w_position"], row["w_velocity"], row["w_delta_v"])
        history, _, _ = model.trajectory(
            np.asarray(case["chaser"]) + initial[1],
            np.asarray(case["target"]) + initial[1],
            (0, meta["duration_s"]), burns, weights, bodies,
            samples_per_segment=meta["samples_per_segment"],
        )
        times, states, target, burn_times, burn_states = history
        target_at_times = target.sol(times).T
        target_at_burns = target.sol(burn_times).T
        delta = states[:, :3] - target_at_times[:, :3]
        burn_delta = burn_states[:, :3] - target_at_burns[:, :3]
        separation = float(np.linalg.norm(delta[-1]))
        speed = float(np.linalg.norm(states[-1, 3:] - target_at_times[-1, 3:]))
        np.testing.assert_allclose(separation, row["final_separation_m"], rtol=0, atol=1e-6)
        np.testing.assert_allclose(speed, row["final_relative_speed_m_s"], rtol=0, atol=1e-6)
        earth_xyz = bodies.sol(times)[6:9].T
        earth_at_burns = bodies.sol(burn_times)[6:9].T
        chaser_xy = (states[:, :2] - earth_xyz[:, :2]) / 1000
        target_xy = (target_at_times[:, :2] - earth_xyz[:, :2]) / 1000
        burn_xy = (burn_states[:, :2] - earth_at_burns[:, :2]) / 1000
        orbit_ax.add_patch(Circle((0, 0), system.BODY_RADII[1]/1000,
                                  facecolor="#e5edf0", edgecolor="#9caeb8", linewidth=.9))
        orbit_ax.text(0, 0, "Earth", ha="center", va="center", color="#52636b")
        orbit_ax.plot(*target_xy.T, color=target_color, lw=2.2, label="Target")
        orbit_ax.plot(*chaser_xy.T, color=chaser_color, lw=1.6, ls="--", label="Chaser")
        orbit_ax.scatter(*chaser_xy[0], marker="o", s=65, facecolor="white",
                         edgecolor=chaser_color, linewidth=1.6, zorder=5)
        orbit_ax.scatter(*chaser_xy[-1], marker="s", s=65, color=chaser_color, zorder=5)
        orbit_ax.scatter(*target_xy[-1], marker="x", s=70, color=target_color, zorder=6)
        orbit_ax.scatter(*burn_xy.T, marker="D", s=35, color=burn_color, zorder=7)
        extent = max(system.BODY_RADII[1]/1000, np.abs(chaser_xy).max(), np.abs(target_xy).max()) * 1.12
        orbit_ax.set(xlim=(-extent, extent), ylim=(-extent, extent), aspect="equal",
                     xlabel="Earth-centred x (km)", ylabel="Earth-centred y (km)", title=title)
        relative_ax.plot(*delta[:, :2].T, color=chaser_color, lw=1.7, ls="--")
        relative_ax.scatter(0, 0, marker="x", color=target_color, s=90, linewidth=2, zorder=5)
        relative_ax.scatter(*delta[0, :2], marker="o", s=65, facecolor="white",
                            edgecolor=chaser_color, linewidth=1.6, zorder=6)
        relative_ax.scatter(*delta[-1, :2], marker="s", s=65, color=chaser_color, zorder=6)
        relative_ax.scatter(*burn_delta[:, :2].T, marker="D", s=35, color=burn_color, zorder=7)
        for number, xy in enumerate(burn_delta[:, :2], 1):
            relative_ax.annotate(str(number), xy, xytext=(6, 7), textcoords="offset points", fontsize=11)
        points = np.vstack((delta[:, :2], np.zeros(2)))
        lower, upper = points.min(axis=0), points.max(axis=0)
        middle = (lower + upper) / 2
        half_width = max(np.max(upper - lower) * .66, 20)
        relative_ax.set(xlim=(middle[0]-half_width, middle[0]+half_width),
                        ylim=(middle[1]-half_width, middle[1]+half_width), aspect="equal",
                        xlabel="Chaser minus target: x (m)", ylabel="Chaser minus target: y (m)",
                        title="")
        relative_ax.set_title(
            f"Relative to target\nFinal 3D separation: {separation:.1f} m\nRelative speed: {speed:.3f} m/s",
            fontsize=12,
        )
        for ax in (orbit_ax, relative_ax):
            ax.grid(alpha=.18)
            ax.tick_params(labelsize=11)
        verification.append(dict(scenario=name, candidate="best_overall",
                                 final_separation_m=separation, final_relative_speed_m_s=speed,
                                 description="Original-tolerance x-y projections of saved burns; no optimization"))
    handles = [Line2D([], [], color=target_color, lw=2, label="Target trajectory"),
               Line2D([], [], color=chaser_color, ls="--", lw=2, label="Chaser trajectory"),
               Line2D([], [], color=chaser_color, marker="o", markerfacecolor="white", ls="", label="Chaser start"),
               Line2D([], [], color=chaser_color, marker="s", ls="", label="Chaser end"),
               Line2D([], [], color=target_color, marker="x", ls="", label="Target end / origin"),
               Line2D([], [], color=burn_color, marker="D", ls="", label="Burns 1 and 2")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=12,
               frameon=False, bbox_to_anchor=(.5, .005))
    fig.tight_layout(rect=(0, .065, 1, 1), h_pad=2.3, w_pad=1.6)
    stem = DIRECTORY / "report_successful_trajectories"
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=190, bbox_inches="tight")
    plt.close(fig)
    stem.with_suffix(".json").write_text(json.dumps(verification, indent=2) + "\n")
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
