import unittest
from types import SimpleNamespace
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import numpy as np

import Multiple_Gravitational_Objects as model
import Rendezvous_2_spacecrafts_orbit_Earth as planar


class EarthRelativeBurnTests(unittest.TestCase):
    def test_invalid_times_are_worse_than_any_finite_valid_cost(self):
        for burns in ([[1, 400], [2, 300]], [[1, -1]], [[1, 601]], [[1, 300], [2, 300]]):
            with self.subTest(burns=burns):
                with patch.object(model, "solve_ivp") as propagate:
                    self.assertEqual(model.score(burns, None, None, (0, 600), None, None), np.inf)
                    propagate.assert_not_called()
                with patch.object(planar, "solve_ivp") as propagate:
                    self.assertEqual(planar.score(burns, None, None, (0, 600), None), np.inf)
                    propagate.assert_not_called()

    def test_search_and_reconstruction_use_earth_velocity_at_burn_time(self):
        # Isolate the impulse with force-free propagation. Earth's prescribed
        # velocity changes direction relative to the chaser before the burn.
        # A common velocity offset must not affect the resulting delta-v.
        for boost in (np.zeros(3), np.array([50000., -20000., 10000.])):
            for magnitude in (100., -100., 0.):
                with self.subTest(boost=boost, magnitude=magnitude):
                    def body_state(time):
                        state = np.zeros(24)
                        state[9:12] = np.array([29700. + time, 1000., 200.]) + boost
                        return state

                    bodies = SimpleNamespace(sol=body_state)
                    initial = np.array([7e6, 0., 1000., 30000., 8500., 200.])
                    initial[3:] += boost
                    burns = np.array([[magnitude, 300.]])
                    weights = (1e-8, 1e-2, 1e-3)

                    def force_free(time, state, body_solution):
                        return np.concatenate((state[3:6], np.zeros(3)))

                    with patch.object(model, "n_body_ode", side_effect=force_free):
                        history, plotted_score, _ = model.trajectory(
                            initial, initial, (0., 600.), burns, weights,
                            bodies, samples_per_segment=5,
                        )
                        search_score = model.score(
                            burns.ravel(), initial, history[2], (0., 600.),
                            weights, bodies,
                        )

                    expected_delta = np.array([0., magnitude, 0.])
                    expected = initial.copy()
                    expected[:3] += initial[3:] * 600. + expected_delta * 300.
                    expected[3:] += expected_delta
                    np.testing.assert_allclose(history[1][-1], expected, rtol=0, atol=1e-5)
                    # Analytic terminal error: |dv|*300 m and |dv| m/s.
                    expected_score = (weights[0] * (magnitude * 300.)**2
                                      + weights[1] * magnitude**2
                                      + weights[2] * abs(magnitude))
                    self.assertAlmostEqual(search_score, expected_score, places=6)
                    self.assertAlmostEqual(plotted_score, expected_score, places=6)


if __name__ == "__main__":
    unittest.main()
