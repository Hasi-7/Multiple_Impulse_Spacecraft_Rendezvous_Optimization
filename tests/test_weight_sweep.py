import csv
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.optimize import differential_evolution

import weight_sweep as sweep
from test_celestial_body_simulator import initial_states


class WeightSweepTests(unittest.TestCase):
    def test_coarse_grid_and_quarter_steps(self):
        self.assertEqual(sweep.COARSE_VALUES, (0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000, 1000000))
        self.assertEqual(len(list(itertools.product(sweep.COARSE_VALUES, repeat=3))), 1000)
        self.assertEqual(sweep.refinement_values(100), (25, 50, 75, 100, 250, 500, 750, 1000))
        for centre in (0.001, 1_000_000):
            values = sweep.refinement_values(centre)
            self.assertIn(centre, values)
            self.assertTrue(all(0.001 <= value <= 1_000_000 for value in values))

    def test_fixed_comparison_and_invalid_trials(self):
        self.assertEqual(sweep.comparison_score(100, 0.1, 500, (100, 0.1, 500)), 3)
        rows = [dict(status="surface_intersection", comparison_score=0),
                dict(status="error"), dict(status="ok", comparison_score=10),
                dict(status="ok", comparison_score=5)]
        self.assertIs(sweep.select_best(rows), rows[-1])
        self.assertIsNone(sweep.select_best(rows[:2]))
        for burns in (np.array([[1, 400], [2, 300]]), np.array([[501, 300]]),
                      np.array([[np.nan, 300]])):
            with self.assertRaises(ValueError):
                sweep.validate_burns(burns, 600)

    def test_dry_run_makes_no_network_or_optimizer_calls(self):
        with patch("builtins.print"), patch.object(sweep.system, "get_initial_states") as get, \
             patch.object(sweep.model, "rendezvous") as optimize:
            self.assertIsNone(sweep.run_sweep(sweep.parse_args(["--dry-run"])))
        get.assert_not_called()
        optimize.assert_not_called()

    def test_actual_trial_with_short_optimizer(self):
        initial = initial_states()
        bodies = sweep.system.simulate_system(initial, 600, samples=20)

        def short_optimizer(*args, **kwargs):
            return differential_evolution(*args, **kwargs, maxiter=1, popsize=5, polish=False)

        with patch.object(sweep.model, "differential_evolution", side_effect=short_optimizer):
            row = sweep.run_trial((0.001, 0.001, 0.001), sweep.CHASER_STATE + initial[1],
                                  sweep.TARGET_STATE + initial[1], bodies, 600, 1, 30,
                                  sweep.DEFAULT_REFERENCES)
        self.assertIn(row["status"], ("ok", "surface_intersection"))
        self.assertGreaterEqual(row["final_separation_m"], 0)
        self.assertGreaterEqual(row["final_relative_speed_m_s"], 0)
        self.assertGreaterEqual(row["total_delta_v_m_s"], 0)
        self.assertTrue(np.isfinite(row["comparison_score"]))
        self.assertEqual(len(json.loads(row["burns_json"])), 1)

    def test_coarse_then_refinement_and_deduplication(self):
        tested = []

        def trial(weights, *args):
            tested.append(weights)
            return dict(status="ok", comparison_score=sum(abs(value - 100) for value in weights),
                        final_separation_m=1.0, final_relative_speed_m_s=1.0, total_delta_v_m_s=1.0)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sweep"
            args = sweep.parse_args(["--output", str(output)])
            with patch("builtins.print"), patch.object(sweep, "COARSE_VALUES", (10.0, 100.0, 1000.0)), \
                 patch.object(sweep.system, "get_initial_states", return_value=initial_states()) as get, \
                 patch.object(sweep.system, "simulate_system") as propagate, \
                 patch.object(sweep, "run_trial", side_effect=trial):
                summary = sweep.run_sweep(args)
            get.assert_called_once()
            propagate.assert_called_once()
            self.assertEqual(summary["completed_stages"], ["coarse", "refined"])
            self.assertEqual(len(tested), len(set(tested)))
            self.assertEqual(tested[:27], list(itertools.product((10, 100, 1000), repeat=3)))
            self.assertIn((25, 50, 750), tested)
            self.assertEqual(summary["best"]["w_position"], 100)
            self.assertTrue((output / "configuration.json").exists())
            self.assertTrue((output / "summary.json").exists())
            with (output / "results.csv").open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), len(tested))

    def test_failed_trial_is_saved_and_limit_prevents_refinement(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sweep"
            args = sweep.parse_args(["--output", str(output), "--max-runs", "1"])
            with patch("builtins.print"), \
                 patch.object(sweep.system, "get_initial_states", return_value=initial_states()), \
                 patch.object(sweep.system, "simulate_system"), \
                 patch.object(sweep, "run_trial", side_effect=ValueError("Invalid burn sequence")):
                summary = sweep.run_sweep(args)
            self.assertEqual(summary["stop_reason"], "max_runs")
            self.assertEqual(summary["completed_stages"], [])
            self.assertEqual(summary["trials_completed"], 1)
            self.assertIsNone(summary["best"])
            with (output / "results.csv").open(newline="", encoding="utf-8") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["status"], "error")
            self.assertIn("Invalid burn sequence", row["message"])

    def test_interrupt_preserves_completed_trials(self):
        row = dict(status="ok", comparison_score=1.0, final_separation_m=10.0,
                   final_relative_speed_m_s=1.0, total_delta_v_m_s=100.0)
        with tempfile.TemporaryDirectory() as directory:
            args = sweep.parse_args(["--output", str(Path(directory) / "sweep")])
            with patch("builtins.print"), \
                 patch.object(sweep.system, "get_initial_states", return_value=initial_states()), \
                 patch.object(sweep.system, "simulate_system"), \
                 patch.object(sweep, "run_trial", side_effect=[row, KeyboardInterrupt()]):
                summary = sweep.run_sweep(args)
            self.assertEqual(summary["stop_reason"], "interrupted")
            self.assertEqual(summary["trials_completed"], 1)

    def test_resume_appends_next_trial_without_refetching_or_changing_configuration(self):
        trial = dict(status="ok", comparison_score=1.0, final_separation_m=10.0,
                     final_relative_speed_m_s=1.0, total_delta_v_m_s=100.0)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sweep"
            with patch("builtins.print"), \
                 patch.object(sweep.system, "get_initial_states", return_value=initial_states()), \
                 patch.object(sweep.system, "simulate_system"), \
                 patch.object(sweep, "run_trial", return_value=trial):
                sweep.run_sweep(sweep.parse_args(["--output", str(output), "--max-runs", "1"]))
            prefix = (output / "results.csv").read_bytes()
            configuration = (output / "configuration.json").read_bytes()
            summary_before = (output / "summary.json").read_bytes()
            with patch("builtins.print"), \
                 patch.object(sweep.system, "get_initial_states") as get, \
                 patch.object(sweep.system, "simulate_system") as simulate, \
                 patch.object(sweep, "run_trial", return_value=trial) as run:
                summary = sweep.run_sweep(sweep.parse_args([
                    "--resume", str(output), "--max-runs", "2",
                ]))
            get.assert_not_called()
            np.testing.assert_array_equal(simulate.call_args.args[0], initial_states())
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], (0.001, 0.001, 0.01))
            self.assertEqual(summary["trials_completed"], 2)
            self.assertTrue((output / "results.csv").read_bytes().startswith(prefix))
            self.assertEqual((output / "configuration.json").read_bytes(), configuration)
            backups = list(output.glob("summary_before_resume_*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), summary_before)

    def test_resume_refinement_keeps_original_coarse_centre(self):
        def trial(weights, *args):
            score = (10 + sum(abs(value - 100) for value in weights)
                     if all(value in sweep.COARSE_VALUES for value in weights) else 1.0)
            return dict(status="ok", comparison_score=score, final_separation_m=1.0,
                        final_relative_speed_m_s=1.0, total_delta_v_m_s=1.0)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sweep"
            with patch("builtins.print"), patch.object(sweep, "COARSE_VALUES", (10.0, 100.0, 1000.0)), \
                 patch.object(sweep.system, "get_initial_states", return_value=initial_states()), \
                 patch.object(sweep.system, "simulate_system"), \
                 patch.object(sweep, "run_trial", side_effect=trial) as run:
                sweep.run_sweep(sweep.parse_args(["--output", str(output), "--max-runs", "28"]))
                self.assertEqual(run.call_args.args[0], (25, 25, 25))
                run.reset_mock()
                summary = sweep.run_sweep(sweep.parse_args(["--resume", str(output), "--max-runs", "29"]))
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0], (25, 25, 50))
            self.assertEqual(summary["trials_completed"], 29)

    def test_resume_rejects_truncated_csv_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sweep"
            with patch("builtins.print"), \
                 patch.object(sweep.system, "get_initial_states", return_value=initial_states()), \
                 patch.object(sweep.system, "simulate_system"), \
                 patch.object(sweep, "run_trial", side_effect=ValueError("test")):
                sweep.run_sweep(sweep.parse_args(["--output", str(output), "--max-runs", "1"]))
            results = output / "results.csv"
            results.write_bytes(results.read_bytes().rstrip(b"\r\n"))
            before = results.read_bytes()
            with self.assertRaisesRegex(ValueError, "no final newline"):
                sweep.load_checkpoint(output)
            self.assertEqual(results.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
