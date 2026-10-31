import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

import validate_sweep_weights as validation
import weight_sweep as sweep


class ValidationTests(unittest.TestCase):
    def test_scenarios_are_distinct_and_include_changed_targets(self):
        metadata = dict(chaser_earth_relative_si=sweep.CHASER_STATE.tolist(),
                        target_earth_relative_si=sweep.TARGET_STATE.tolist())
        cases = validation.scenarios(metadata)
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({c['name'] for c in cases}), 8)
        self.assertEqual(cases[0]['chaser'], metadata['chaser_earth_relative_si'])
        self.assertEqual(cases[1]['chaser'][1], -1000)
        self.assertNotIn('near_along_track_100m', {c['name'] for c in cases})
        self.assertEqual(cases[-2]['target'][0], 8e6)
        self.assertGreater(cases[-1]['target'][5], 0)
        for case in cases:
            self.assertTrue(np.isfinite(case['chaser']).all())
            self.assertEqual(len(case['target']), 6)

    def test_selection_is_based_only_on_saved_metrics(self):
        rows = [dict(status='ok', stage=stage, comparison_score=score,
                     final_separation_m=position, final_relative_speed_m_s=speed,
                     w_position=weight, w_velocity=2, w_delta_v=3)
                for stage, score, position, speed, weight in
                [('refined', 1, 4, 4, 1), ('coarse', 2, 3, 3, 2),
                 ('refined', 4, 1, 2, 3), ('refined', 5, 2, 1, 4)]]
        rows.append(dict(status='error'))
        chosen = validation.candidates(rows)
        self.assertEqual([c['weights'][0] for c in chosen], [1, 2, 3, 4])

    def test_success_requires_both_terminal_metrics_and_safe_status(self):
        self.assertTrue(validation.rendezvous_pass(dict(status='ok', final_separation_m=100,
                                                       final_relative_speed_m_s=0.1)))
        self.assertFalse(validation.rendezvous_pass(dict(status='ok', final_separation_m=1,
                                                        final_relative_speed_m_s=2)))
        self.assertFalse(validation.rendezvous_pass(dict(status='ok', final_separation_m=101,
                                                        final_relative_speed_m_s=0)))
        self.assertFalse(validation.rendezvous_pass(dict(status='surface_intersection',
                                                        final_separation_m=0, final_relative_speed_m_s=0)))
        self.assertFalse(validation.rendezvous_pass(dict(status='error')))

    def test_report_handles_failed_trials_and_excludes_original_from_summary(self):
        metadata, rows = sweep.load_checkpoint(validation.SOURCE)
        choices = validation.candidates(rows)
        cases = validation.scenarios(metadata)
        config = dict(source_configuration=metadata, source_directory=str(validation.SOURCE),
                      source_trial_count=len(rows), source_statuses={}, candidates=choices, scenarios=cases)
        failed = dict(scenario='original_control', candidate='best_overall', status='error', message='test failure')
        with tempfile.TemporaryDirectory() as directory:
            validation.write_report(Path(directory), config, [failed], {}, False)
            report = (Path(directory) / 'summary.txt').read_text(encoding='utf-8')
        self.assertIn('test failure', report)
        self.assertIn('Complete: False', report)
        self.assertIn('best_overall: 0 tried', report)
        self.assertIn('Sun-frame', report)


if __name__ == '__main__':
    unittest.main()
