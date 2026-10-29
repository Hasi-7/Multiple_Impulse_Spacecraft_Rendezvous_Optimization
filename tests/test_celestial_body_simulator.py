import unittest
from unittest.mock import Mock, patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import celestial_body_simulator as simulator


def initial_states():
    states = np.zeros((4, 6))
    states[1] = [simulator.AU, 0, 0, 0, 29_780, 0]
    states[2] = [simulator.AU + 384_400_000, 0, 0, 0, 30_802, 0]
    states[3] = [5.2 * simulator.AU, 0, 0, 0, 13_060, 0]
    return states


class BodySimulatorTests(unittest.TestCase):
    def test_fixed_sun_and_gravity_on_moving_bodies(self):
        states = initial_states()
        derivative = simulator.n_body_ode(0, states.ravel()).reshape(4, 6)
        np.testing.assert_array_equal(derivative[:, :3], states[:, 3:])
        expected = sum(
            simulator.MU[j] * (states[j, :3] - states[1, :3])
            / np.linalg.norm(states[j, :3] - states[1, :3])**3
            for j in (0, 2, 3)
        )
        np.testing.assert_allclose(derivative[1, 3:], expected)
        np.testing.assert_array_equal(derivative[0], np.zeros(6))
        # A fixed external source no longer conserves total system momentum.
        weighted = simulator.MU[:, None] * derivative[:, 3:]
        self.assertGreater(np.linalg.norm(weighted.sum(axis=0)), 0)

    def test_horizons_headerless_csv_and_si_conversion(self):
        response = Mock(text="header\n$$SOE\n2461341., date, 1, 2, 3, 4, 5, 6,\n$$EOE\n")
        with patch.object(simulator.requests, "get", return_value=response) as get:
            states = simulator.get_initial_states()
        np.testing.assert_array_equal(states[0], np.zeros(6))
        np.testing.assert_array_equal(states[1:], np.tile(np.arange(1, 7) * 1000, (3, 1)))
        self.assertEqual(get.call_count, 3)
        self.assertEqual(get.call_args.kwargs["params"]["TIME_TYPE"], "UT")

    def test_horizons_missing_vector(self):
        with patch.object(simulator.requests, "get", return_value=Mock(text="API error")):
            with self.assertRaisesRegex(ValueError, "no state vector"):
                simulator.get_initial_states()

    def test_propagation_and_plot(self):
        states = initial_states()
        solution = simulator.simulate_system(states, 86400, samples=100)
        self.assertEqual(solution.y.shape, (24, 100))
        np.testing.assert_array_equal(solution.y[:, 0], states.ravel())
        self.assertTrue(np.all(np.isfinite(solution.y)))
        np.testing.assert_array_equal(solution.y[:6], np.zeros((6, 100)))
        self.assertGreater(np.linalg.norm(solution.y[6:9, -1] - states[1, :3]), 1e9)
        # The stationary Sun does no work: moving-body kinetic energy plus
        # their mutual and fixed-Sun potential energy should be conserved.
        def energy(state):
            bodies = state.reshape(4, 6)
            kinetic = np.sum(simulator.MU * np.sum(bodies[:, 3:]**2, axis=1)) / 2
            potential = sum(
                simulator.MU[i] * simulator.MU[j]
                / np.linalg.norm(bodies[i, :3] - bodies[j, :3])
                for i in range(4) for j in range(i + 1, 4)
            )
            return kinetic - potential
        self.assertLess(abs(energy(solution.y[:, -1]) / energy(solution.y[:, 0]) - 1), 1e-6)
        fig = simulator.plot_system(solution, simulator.DEFAULT_EPOCH)
        self.assertEqual(len(fig.axes), 3)
        plt.close(fig)

    def test_invalid_inputs(self):
        for duration in (0, -1, np.nan, np.inf):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                simulator.simulate_system(initial_states(), duration)
        with self.assertRaises(ValueError):
            simulator.simulate_system(np.zeros((3, 6)), 100)
        with self.assertRaises(ValueError):
            simulator.simulate_system(initial_states(), 100, samples=1)
        for component in (0, 3):
            states = initial_states()
            states[0, component] = 1
            with self.assertRaisesRegex(ValueError, "fixed Sun"):
                simulator.simulate_system(states, 100)
        with self.assertRaisesRegex(ValueError, "singular"):
            simulator.n_body_ode(0, np.zeros(24))


if __name__ == "__main__":
    unittest.main()
