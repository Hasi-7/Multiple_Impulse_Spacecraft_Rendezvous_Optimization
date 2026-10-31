"""Build Appendix C from the saved validation records without altering results."""
import json
import math
from pathlib import Path


DIRECTORY = Path("outputs/weight_validation_fixed_sun_20261029_144240")
LABELS = {
    "original_control": "Original weight-selection case",
    "along_track_1km": "1 km along-track offset",
    "along_track_10km_velocity_error": "10 km along-track offset with velocity error",
    "radial_10km_velocity_error": "10 km radial offset with velocity error",
    "cross_track_10km": "10 km cross-track offset",
    "mixed_100km": "Mixed position and velocity offset",
    "higher_orbit_8000km": "Higher target orbit",
    "inclined_target_20deg": "Target orbit inclined by 20 degrees",
}
WEIGHTS = {"best_overall": "Overall", "best_coarse": "First 1000",
           "best_position": "Position", "best_velocity": "Velocity"}


def number(value, places=3):
    assert math.isfinite(value)
    return f"{value:.{places}f}"


def exact_display(value):
    return f"{value:.6f}".rstrip("0").rstrip(".") if value else "0"


def scientific(value):
    text = f"{value:.6g}"
    if "e" in text:
        mantissa, exponent = text.split("e")
        return "$" + mantissa + r"\times10^{" + str(int(exponent)) + "}$"
    return text


def table(columns, header, rows):
    return [r"\begin{center}", r"\begin{tabular}{" + columns + "}", r"\toprule",
            " & ".join(header) + r"\\", r"\midrule",
            *(" & ".join(row) + r"\\" for row in rows),
            r"\bottomrule", r"\end{tabular}", r"\end{center}"]


def passed(row):
    return (row["status"] == "ok" and row["final_separation_m"] <= 1000
            and row["final_relative_speed_m_s"] <= 1)


def main():
    config = json.loads((DIRECTORY / "configuration.json").read_text())
    saved = json.loads((DIRECTORY / "results.json").read_text())
    meta = config["source_configuration"]
    assert len(config["scenarios"]) == 8 and len(config["candidates"]) == 4
    assert len(saved["trials"]) == 32 and len(saved["coasts"]) == 8
    assert "Complete: True" in (DIRECTORY / "summary.txt").read_text()
    by_key = {(r["scenario"], r["candidate"]): r for r in saved["trials"]}
    assert len(by_key) == 32
    lines = [
        r"\clearpage", r"\section{Full Validation Data}", r"\label{app:validation_data}",
        "This appendix records the eight retained initial-state cases, four selected weight tuples,",
        "32 optimized burn sequences and eight no-burn controls used in Section 5.",
        "An initial proximity case that already met the success criterion without burns",
        "is excluded from the reported dataset. The unfiltered experiment records are archived separately.",
        "These are the original validation results, using relative and absolute solver",
        r"tolerances of $10^{-6}$. The tighter-tolerance checks are reported separately",
        "in Section 4 and Appendix A. Values are rounded for display; the full-precision",
        "records are saved in the configuration and results JSON files under",
        r"\path{outputs/weight_validation_fixed_sun_20261029_144240/}.",
        r"\subsection{Shared settings and selected weights}",
        "Every case uses the fixed-Sun model with Earth, Moon and Jupiter moving under",
        "gravity. The initial body states correspond to 27 October 2026 at 12:00:00 UTC.",
        "The mission lasts 3600 s, with two burns bounded between",
        r"$-1000$ and $1000\ \mathrm{m\,s^{-1}}$ each. Burn times lie between 60 and",
        "3540 s and must be strictly increasing. The optimizer seed is 42, with the",
        "full differential-evolution settings described in Section 3. Powered trajectories",
        "use 1000 samples per interval; no-burn controls use 3000 output samples.",
    ]
    lines += table("lrrr", ["Selection", r"$\omega_r$", r"$\omega_v$", r"$\omega_{\Delta v}$"],
                   [[WEIGHTS[c["name"]], *(exact_display(v) for v in c["weights"])]
                    for c in config["candidates"]])
    lines += [
        "In the case tables, a project pass requires both a final separation no greater",
        r"than 1000 m and a relative speed no greater than $1\ \mathrm{m\,s^{-1}}$.",
        "It also requires a trajectory that passes the sampled surface check.",
        "The clearance is the minimum sampled altitude of either spacecraft above",
        "any of the four modelled body surfaces. A positive clearance does not rule",
        "out a surface crossing between samples. The closest-approach time refers",
        "to the minimum sampled chaser--target separation, not to surface clearance.",
        "The score $S$ uses the fixed comparison scales from Section 5; the objective",
        "$J$ uses the selected weights and should not be compared directly between",
        "different weight tuples. Elapsed times are the recorded powered-trial times",
        "and are not timing measurements of the tighter-tolerance accuracy checks.",
        r"\par\noindent\begin{minipage}{\linewidth}",
        r"\subsection{Initial gravitational-body states}",
        "The following positions and velocities initialize the body propagation,",
        "with the Sun fixed at the origin. Displayed components are rounded to six",
        "decimal places. Positions are in metres and velocities in metres per second.",
        "The same saved values are used for every validation case.",
    ]
    names = ["Sun", "Earth", "Moon", "Jupiter"]
    initial = meta["initial_body_states_si"]
    body_rows = []
    for name, row in zip(names, initial):
        body_rows += [[name + " position", *(exact_display(v) for v in row[:3])],
                      [name + " velocity", *(exact_display(v) for v in row[3:])]]
    lines += table("lrrr", ["Body / quantity", "$x$ or $v_x$", "$y$ or $v_y$", "$z$ or $v_z$"], body_rows)
    lines += [r"\end{minipage}"]
    rows_written = 0
    for case in config["scenarios"]:
        name = case["name"]
        rows = [by_key[(name, c["name"])] for c in config["candidates"]]
        coast = saved["coasts"][name]
        labelled = [("No burns", coast)] + [(WEIGHTS[r["candidate"]], r) for r in rows]
        lines += [r"\clearpage", r"\subsection{" + LABELS[name] + "}",
                  "The initial spacecraft states are relative to Earth, in the order",
                  r"$[x,y,z,v_x,v_y,v_z]$, with positions in metres and velocities in",
                  r"$\mathrm{m\,s^{-1}}$:", r"\begin{align*}"]
        for index, key in enumerate(("chaser", "target")):
            symbol = "c" if key == "chaser" else "t"
            lines.append(r"\mathbf s_{" + symbol + r",0}&=["
                         + r",\,".join(exact_display(v) for v in case[key]) + "]"
                         + (r"\\" if index == 0 else "."))
        lines += [r"\end{align*}"]
        if coast["status"] != "ok":
            lines += ["The no-burn control enters a modelled body surface. Its terminal",
                      "measurements describe continued point-mass motion after that",
                      "intersection and are not a physically flyable coast result."]
        lines += [r"\par\noindent\textbf{Terminal results and total velocity change.}"]
        lines += table("lrrrl", ["Selection", "$e_r$ (m)", "$e_v$ (m/s)",
                                 r"Total $\Delta v$ (m/s)", "Project pass"],
                       [[label, number(r["final_separation_m"]), number(r["final_relative_speed_m_s"]),
                         number(r["total_delta_v_m_s"]), "Yes" if passed(r) else "No"]
                        for label, r in labelled])
        lines += [r"\par\noindent\textbf{Closest approach and sampled surface clearance.}"]
        lines += table("lrrrl", ["Selection", "Min. separation (m)", "Time (s)", "Clearance (km)", "Surface check"],
                       [[label, number(r["minimum_sampled_separation_m"]), number(r["minimum_time_s"]),
                         number(r["minimum_sampled_surface_altitude_m"] / 1000),
                         "Clear" if r["status"] == "ok" else "Intersection"] for label, r in labelled])
        lines += [r"\par\noindent\textbf{Selected burns.} Signed magnitudes are in m/s and times are in seconds."]
        burn_rows = []
        for r in rows:
            candidate = next(c for c in config["candidates"] if c["name"] == r["candidate"])
            assert [r[k] for k in ("w_position", "w_velocity", "w_delta_v")] == candidate["weights"]
            burns = json.loads(r["burns_json"])
            assert len(burns) == 2 and 60 <= burns[0][1] < burns[1][1] <= 3540
            assert all(abs(b[0]) <= 1000 for b in burns)
            assert math.isclose(sum(abs(b[0]) for b in burns), r["total_delta_v_m_s"], abs_tol=1e-6)
            burn_rows.append([WEIGHTS[r["candidate"]], *(number(v) for burn in burns for v in burn)])
        lines += table("lrrrr", ["Selection", "$d_1$", "$t_1$", "$d_2$", "$t_2$"], burn_rows)
        lines += [r"\par\noindent\textbf{Recorded costs and computation times.}"]
        lines += table("lrrrr", ["Selection", "Optimizer $J$", "Reconstructed $J$", "Score $S$", "Elapsed (s)"],
                       [[WEIGHTS[r["candidate"]], scientific(r["optimizer_score"]),
                         scientific(r["trajectory_score"]), scientific(r["comparison_score"]),
                         number(r["elapsed_s"])] for r in rows])
        rows_written += len(rows)
    assert rows_written == 32
    output = DIRECTORY / "appendix_validation_data.tex"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {output}: eight cases, 32 verified burn sequences, eight controls.")


if __name__ == "__main__":
    main()
