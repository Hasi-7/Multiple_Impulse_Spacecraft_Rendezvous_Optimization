import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import differential_evolution

import celestial_body_simulator as system
import Multiple_Gravitational_Objects as rendezvous
from test_celestial_body_simulator import initial_states


class RendezvousPlottingTests(unittest.TestCase):
    def setUp(self):
        self.initial = initial_states()
        self.bodies = system.simulate_system(self.initial, 600, samples=50)
        self.chaser = self.initial[1] + [7_000_000, 0, 1000, 0, 7500, 20]
        self.target = self.initial[1] + [7_001_000, 0, 2000, 0, 7500, 15]
        self.burns = np.array([[1.0, 300.0]])
        self.weights = (1 / 100_000**2, 1 / 100**2, 1 / 1000)

    def tearDown(self):
        plt.close("all")

    def history(self):
        return rendezvous.trajectory(
            self.chaser, self.target, (0, 600), self.burns,
            self.weights, self.bodies, samples_per_segment=30,
        )

    def test_trajectory_score_and_3d_plot_frames(self):
        history, trajectory_score, _ = self.history()
        times, states, target, burn_times, burn_states = history
        score = rendezvous.score(self.burns.ravel(), self.chaser, target,
                                 (0, 600), self.weights, self.bodies)
        self.assertAlmostEqual(score, trajectory_score, places=7)
        fig = rendezvous.plot_rendezvous(history, self.bodies)
        separation_ax, sun_ax, earth_ax = fig.axes
        expected = np.linalg.norm(states[:, :3] - target.sol(times)[:3].T, axis=1)
        np.testing.assert_allclose(separation_ax.lines[0].get_ydata(), expected / 1000)
        # A nonzero initial z difference must contribute to the distance.
        self.assertAlmostEqual(expected[0], np.sqrt(2) * 1000)
        for ax, reference, scale in ((sun_ax, 0, system.AU), (earth_ax, 6, 1000)):
            plotted = np.array(ax.lines[1].get_data_3d()).T
            origin = self.bodies.sol(times)[reference:reference + 3].T
            np.testing.assert_allclose(plotted, (states[:, :3] - origin) / scale)
            widths = [np.diff(limits)[0] for limits in
                      (ax.get_xlim(), ax.get_ylim(), ax.get_zlim())]
            np.testing.assert_allclose(widths, widths[0])
        # Render the complete canvas, not just the plotting function.
        fig.canvas.draw()

    def test_physical_body_radii_are_used_in_each_view(self):
        history, _, _ = self.history()
        with patch.object(system, "plot_body_surface", wraps=system.plot_body_surface) as surface:
            body_fig = system.plot_system(self.bodies, system.DEFAULT_EPOCH)
            calls = surface.call_args_list
            for index, radius in enumerate(system.BODY_RADII):
                self.assertAlmostEqual(calls[2 * index].args[2], radius / system.AU)
                self.assertAlmostEqual(calls[2 * index + 1].args[2], radius / system.AU)
            self.assertEqual(calls[-2].args[2], system.BODY_RADII[1] / 1000)
            self.assertEqual(calls[-1].args[2], system.BODY_RADII[2] / 1000)
            body_fig.canvas.draw()
        with patch.object(system, "plot_body_surface", wraps=system.plot_body_surface) as surface:
            rendezvous.plot_rendezvous(history, self.bodies)
            self.assertEqual(surface.call_count, 5)
            for index, radius in enumerate(system.BODY_RADII):
                self.assertAlmostEqual(surface.call_args_list[index].args[2], radius / system.AU)
            self.assertEqual(surface.call_args_list[-1].args[2], system.BODY_RADII[1] / 1000)

    def test_optimizer_passes_body_solution_to_score(self):
        def short_optimization(*args, **kwargs):
            return differential_evolution(*args, **kwargs, maxiter=1, popsize=5, polish=False)

        with patch.object(rendezvous, "differential_evolution", side_effect=short_optimization):
            parameters, score = rendezvous.rendezvous(
                self.chaser, self.target, 1, self.weights, (0, 600), self.bodies,
            )
        self.assertEqual(parameters.shape, (2,))
        self.assertTrue(np.isfinite(score))

    def test_main_accepts_six_component_states_and_displays_both_figures(self):
        inputs = ["7000000 0 1000 0 7500 20", "7001000 0 2000 0 7500 15", "1", "600"]
        with patch("builtins.input", side_effect=inputs), \
             patch.object(system, "get_initial_states", return_value=self.initial), \
             patch.object(rendezvous, "rendezvous", return_value=(self.burns.ravel(), 0.0)), \
             patch("builtins.print") as output, \
             patch.object(plt, "show") as show:
            _, _, history = rendezvous.main(self.weights)
        self.assertEqual(history[1].shape[1], 6)
        self.assertEqual(len(plt.get_fignums()), 2)
        times, states, target, _, _ = history
        separation = np.linalg.norm(states[:, :3] - target.sol(times)[:3].T, axis=1)
        minimum_index = np.argmin(separation)
        output.assert_any_call(f"Final separation: {separation[-1]:.3f} m")
        output.assert_any_call(
            f"Minimum sampled separation: {separation[minimum_index]:.3f} m "
            f"at {times[minimum_index]:.3f} s"
        )
        show.assert_called_once()


if __name__ == "__main__":
    unittest.main()
