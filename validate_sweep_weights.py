"""Out-of-sample checks of saved sweep weights; does not modify the optimizer.

python -B -u validate_sweep_weights.py
"""

import argparse
from collections import Counter
import csv
from datetime import datetime
import json
from pathlib import Path
import time

import numpy as np

import weight_sweep as sweep


SOURCE = Path('outputs/weight_sweep_20261027_200627_547397')


def candidates(rows):
    """Freeze four distinct sweep-derived choices before any validation runs."""
    valid = [r for r in rows if r['status'] == 'ok']
    choices = [
        ('best_overall', min(valid, key=lambda r: r['comparison_score'])),
        ('best_coarse', min((r for r in valid if r['stage'] == 'coarse'),
                            key=lambda r: r['comparison_score'])),
        ('best_position', min(valid, key=lambda r: r['final_separation_m'])),
        ('best_velocity', min(valid, key=lambda r: r['final_relative_speed_m_s'])),
    ]
    return [dict(name=name, weights=[r[k] for k in
                 ('w_position', 'w_velocity', 'w_delta_v')], source_result=r)
            for name, r in choices]


def scenarios(metadata):
    target = np.array(metadata['target_earth_relative_si'], dtype=float)
    result = [dict(name='original_control',
                   chaser=metadata['chaser_earth_relative_si'], target=target.tolist())]
    for name, offset in [
        ('near_along_track_100m', [0, -100, 0, 0, 0, 0]),
        ('along_track_1km', [0, -1000, 0, 0, 0, 0]),
        ('along_track_10km_velocity_error', [0, -10000, 0, 0, -5, 0]),
        ('radial_10km_velocity_error', [10000, 0, 0, 0, -5, 0]),
        ('cross_track_10km', [0, 0, 10000, 0, 0, 10]),
        ('mixed_100km', [20000, -100000, 30000, 10, -20, 30]),
    ]:
        result.append(dict(name=name, chaser=(target + offset).tolist(), target=target.tolist()))
    # Change the target orbit too, not only the chaser's displacement.
    mu = sweep.system.MU[1]
    for name, radius, inclination in [('higher_orbit_8000km', 8e6, 0),
                                      ('inclined_target_20deg', 7e6, np.deg2rad(20))]:
        speed = np.sqrt(mu / radius)
        state = np.array([radius, 0, 0, 0, speed*np.cos(inclination), speed*np.sin(inclination)])
        result.append(dict(name=name, chaser=(state + [0, -10000, 2000, 0, -5, 2]).tolist(),
                           target=state.tolist()))
    return result


def rendezvous_pass(row):
    # Explicit evaluation criteria, not new constraints or official mission requirements.
    return (row['status'] == 'ok' and row['final_separation_m'] <= 100
            and row['final_relative_speed_m_s'] <= 0.1)


def coast_metrics(chaser, target, bodies, metadata):
    history, _, _ = sweep.model.trajectory(
        chaser, target, (0, metadata['duration_s']), np.empty((0, 2)),
        (1, 1, 1), bodies, samples_per_segment=metadata['samples_per_segment'] * 3)
    times, states, target_sol, _, _ = history
    target_states = target_sol.sol(times).T
    if (times[-1] != metadata['duration_s'] or not target_sol.success
            or not np.all(np.isfinite(states)) or not np.all(np.isfinite(target_states))):
        raise ValueError('Invalid coast trajectory')
    distances = np.linalg.norm(states[:, :3] - target_states[:, :3], axis=1)
    altitude = min(sweep.sampled_surface_altitude(states, times, bodies),
                   sweep.sampled_surface_altitude(target_states, times, bodies))
    return dict(status='ok' if altitude > 0 else 'surface_intersection',
                final_separation_m=float(distances[-1]),
                final_relative_speed_m_s=float(np.linalg.norm(states[-1, 3:] - target_states[-1, 3:])),
                minimum_sampled_separation_m=float(distances.min()),
                minimum_time_s=float(times[np.argmin(distances)]), total_delta_v_m_s=0,
                minimum_sampled_surface_altitude_m=altitude)


def write_report(output, configuration, trials, coasts, complete):
    m = configuration['source_configuration']
    lines = ['WEIGHT SWEEP: INITIAL-STATE GENERALIZATION TEST',
             '=' * 60, f'Run directory: {output}', f'Complete: {complete}',
             f'Source sweep: {configuration["source_directory"]}',
             f'Source trials: {configuration["source_trial_count"]}; statuses: {configuration["source_statuses"]}',
             '', 'METHOD AND SUCCESS CRITERIA',
             f'Epoch: {m["epoch_utc"]} UTC; duration: {m["duration_s"]} s; burns: {m["number_of_burns"]}.',
             'Gravitational model: ' + m.get('gravitational_model', 'Historical moving-Sun four-body model'),
             f'Samples per powered segment: {m["samples_per_segment"]}; coast: 3000 samples.',
             'Same saved body ephemeris, four-body dynamics, optimizer defaults and seed 42.',
             'Each candidate is reoptimized for each initial state. Burn sequences are NOT reused.',
             'Candidates were frozen from the original sweep; no new sweep or validation-state tuning.',
             'Strict rendezvous: final separation <= 100 m AND relative speed <= 0.1 m/s, surface-safe.',
             'Project rendezvous criterion (also labelled loose below): <= 1000 m AND <= 1 m/s, surface-safe.',
             'The strict criterion is a secondary diagnostic. A close flyby alone is not rendezvous.',
             'Comparison score uses the saved fixed scales; raw weighted costs are not cross-comparable.',
             '', 'WEIGHTS (position, velocity, delta-v) AND ORIGINAL SWEEP RESULTS']
    for c in configuration['candidates']:
        r = c['source_result']
        lines.append(f'{c["name"]}: {c["weights"]}; original final={r["final_separation_m"]:.6f} m, '
                     f'speed={r["final_relative_speed_m_s"]:.6f} m/s, dv={r["total_delta_v_m_s"]:.6f} m/s')
    lines += ['', 'INITIAL STATES', 'Earth-relative [x,y,z,vx,vy,vz], SI units, J2000 ecliptic-aligned.']
    for s in configuration['scenarios']:
        lines += [s['name'], f'  chaser: {s["chaser"]}', f'  target: {s["target"]}']
    lines += ['', 'ALL EXPERIMENTS', 'Separation is at mission end unless explicitly marked minimum.']
    for s in configuration['scenarios']:
        name = s['name']
        lines += ['', name]
        if name in coasts:
            r = coasts[name]
            lines.append(f'  COAST: final={r["final_separation_m"]:.6f} m; speed={r["final_relative_speed_m_s"]:.6f} m/s; '
                         f'min={r["minimum_sampled_separation_m"]:.6f} m; '
                         f'min altitude={r["minimum_sampled_surface_altitude_m"]:.3f} m; status={r["status"]}')
        for r in [r for r in trials if r['scenario'] == name]:
            lines.append(f'  {r["candidate"]}: {r["status"]}; strict rendezvous={rendezvous_pass(r)}')
            if 'final_separation_m' not in r:
                lines.append(f'    Error: {r.get("message", "unknown")}')
                continue
            lines += [f'    final={r["final_separation_m"]:.6f} m; speed={r["final_relative_speed_m_s"]:.6f} m/s; '
                      f'delta-v={r["total_delta_v_m_s"]:.6f} m/s; score={r["comparison_score"]:.6f}',
                      f'    minimum separation={r["minimum_sampled_separation_m"]:.6f} m at {r["minimum_time_s"]:.6f} s; '
                      f'minimum surface altitude={r["minimum_sampled_surface_altitude_m"]:.3f} m',
                      f'    burns [signed delta-v m/s, time s]: {r["burns_json"]}',
                      f'    elapsed={r["elapsed_s"]:.3f} s']
            if name in coasts:
                b = coasts[name]
                lines.append(f'    vs coast: final separation change={r["final_separation_m"]-b["final_separation_m"]:+.6f} m; '
                             f'speed change={r["final_relative_speed_m_s"]-b["final_relative_speed_m_s"]:+.6f} m/s '
                             '(negative means improvement)')
    lines += ['', 'SUMMARY (NEW STATES ONLY; ORIGINAL CONTROL EXCLUDED)']
    new = [r for r in trials if r['scenario'] != 'original_control']
    for c in configuration['candidates']:
        rows = [r for r in new if r['candidate'] == c['name']]
        valid = [r for r in rows if r['status'] == 'ok']
        loose = sum(r['final_separation_m'] <= 1000 and r['final_relative_speed_m_s'] <= 1 for r in valid)
        both = sum(r['final_separation_m'] < coasts[r['scenario']]['final_separation_m']
                   and r['final_relative_speed_m_s'] < coasts[r['scenario']]['final_relative_speed_m_s'] for r in valid)
        lines.append(f'{c["name"]}: {len(rows)} tried; {len(valid)} surface-safe; '
                     f'{sum(map(rendezvous_pass, rows))} strict; {loose} loose; {both} improved BOTH final metrics vs coast.')
        if valid:
            lines.append(f'  Final separation range: {min(r["final_separation_m"] for r in valid):.6f} to '
                         f'{max(r["final_separation_m"] for r in valid):.6f} m; speed range: '
                         f'{min(r["final_relative_speed_m_s"] for r in valid):.6f} to '
                         f'{max(r["final_relative_speed_m_s"] for r in valid):.6f} m/s.')
    successes = sum(map(rendezvous_pass, new))
    lines += ['', 'INTERPRETATION',
              f'{successes}/{len(new)} new-state weight/state pairs met strict rendezvous criteria.',
              'Finite, non-colliding output does not by itself mean a good rendezvous.',
              'Near-start cases may already be close: use coast comparison rather than final distance alone.',
              '', 'LIMITATIONS AND MODEL OBSERVATIONS',
              '- Deterministic hand-selected states, one optimizer seed; not Monte Carlo success probabilities.',
              f'- Two signed scalar burns, each bounded at {m.get("burn_magnitude_limit_m_s", 500):g} m/s.',
              ('- Burns follow instantaneous Earth-relative velocity; still not general 3-axis controls.'
               if m.get('burn_direction') == 'instantaneous Earth-relative velocity'
               else '- IMPORTANT: historical burns use full inertial (Sun-frame) velocity, not Earth-relative velocity.'),
              ('- Invalid burn sequences receive positive infinity.'
               if m.get('invalid_burn_penalty') == 'positive infinity'
               else '- Historical invalid-order penalty is 1e12; valid high-weight costs can exceed it.'),
              '- Existing DOP853 rtol=1e-6 and large Sun-frame coordinates are unchanged. No independent',
              '  tighter-tolerance verification was performed; these are model-level results, not flight validation.',
              '- Minimum distances and surface checks are sampled; no continuous collision guarantee.',
              '- No atmosphere, thrust duration, navigation error or collision avoidance constraints.',
              '- Failure cannot isolate weight quality from control restrictions, optimizer convergence or numerics.',
              '- Delta-v is a fuel proxy, not propellant mass.',
              '', 'Reproduce: python -B -u validate_sweep_weights.py --source ' + str(configuration['source_directory']),
              'Machine-readable: configuration.json, results.json, results.csv (flushed each trial).']
    (output / 'summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    metadata, source_rows = sweep.load_checkpoint(args.source)
    current_hash = sweep.model_fingerprint()
    if metadata.get('model_sha256') != current_hash:
        raise ValueError('Source sweep uses a different or unrecorded model; rerun the sweep before validation.')
    configuration = dict(source_directory=str(args.source), source_configuration=metadata,
                         source_trial_count=len(source_rows), source_statuses=dict(Counter(r['status'] for r in source_rows)),
                         candidates=candidates(source_rows), scenarios=scenarios(metadata))
    output = args.output or Path('outputs') / ('weight_validation_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir(parents=True, exist_ok=False)
    (output / 'configuration.json').write_text(json.dumps(configuration, indent=2), encoding='utf-8')
    bodies = sweep.system.simulate_system(np.array(metadata['initial_body_states_si']), metadata['duration_s'])
    earth = np.array(metadata['initial_body_states_si'][1])
    trials, coasts = [], {}
    complete = False
    print(f'Output: {output}', flush=True)
    fields = ('scenario', 'candidate') + sweep.FIELDS[1:]
    try:
        with (output / 'results.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for s in configuration['scenarios']:
                chaser, target = np.array(s['chaser']) + earth, np.array(s['target']) + earth
                coasts[s['name']] = coast_metrics(chaser, target, bodies, metadata)
                for c in configuration['candidates']:
                    print(f'{s["name"]}: {c["name"]} {c["weights"]}', flush=True)
                    started = time.perf_counter()
                    row = dict(scenario=s['name'], candidate=c['name'],
                               **dict(zip(('w_position', 'w_velocity', 'w_delta_v'), c['weights'])))
                    try:
                        row.update(sweep.run_trial(c['weights'], chaser, target, bodies, metadata['duration_s'],
                                                  metadata['number_of_burns'], metadata['samples_per_segment'],
                                                  metadata['comparison_references_m_m_s_m_s']))
                    except Exception as exc:
                        row.update(status='error', message=f'{type(exc).__name__}: {exc}')
                    row['elapsed_s'] = time.perf_counter() - started
                    trials.append(row)
                    writer.writerow(row)
                    stream.flush()
                    print(f'  {row["status"]}: final={row.get("final_separation_m")} m, '
                          f'speed={row.get("final_relative_speed_m_s")} m/s', flush=True)
                    (output / 'results.json').write_text(json.dumps(dict(trials=trials, coasts=coasts), indent=2), encoding='utf-8')
                    write_report(output, configuration, trials, coasts, False)
            complete = True
    finally:
        write_report(output, configuration, trials, coasts, complete)
    print(f'Report saved: {output / "summary.txt"}', flush=True)


if __name__ == '__main__':
    main()
