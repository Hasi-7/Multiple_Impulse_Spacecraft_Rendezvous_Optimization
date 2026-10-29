from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution
import numpy as np
import matplotlib.pyplot as plt
import celestial_body_simulator as system

MAX_BURN_DELTA_V = 1000.0  # Absolute magnitude of each signed burn, in m/s.

# System is defined with Sun at the origin, Earth, Moon and Jupiter as the significantly relevant gravitational bodies
    
def n_body_ode(t, state, body_solution):

    # Starting 3D State
    x = state[0]
    y = state[1]
    z = state[2]
    vx = state[3]
    vy = state[4]
    vz = state[5]

    body_state_at_t = body_solution.sol(t)
    spacecraft_position = np.asarray(state[:3])

    # Acceleration due to net gravity of system

    acceleration = np.zeros(3)

    for i in range(len(system.BODY_NAMES)):
        body_position = body_state_at_t[6*i : 6*i + 3]
        relative_position = spacecraft_position - body_position
        distance = np.linalg.norm(relative_position)
        acceleration += -system.MU[i] * (relative_position/ distance**3)

    ax, ay, az = acceleration

    return [vx, vy, vz, ax, ay, az]

def burn_size(v, delta):
    unit_v = v/np.linalg.norm(v)
    return delta * unit_v

def earth_relative_burn(state, delta, time, body_solution):
    """Resolve a signed burn along the spacecraft's Earth-relative velocity."""
    if delta == 0:
        return np.zeros(3)
    earth_index = system.BODY_NAMES.index("Earth")
    velocity_start = 6 * earth_index + 3
    earth_velocity = body_solution.sol(time)[velocity_start:velocity_start + 3]
    relative_velocity = np.asarray(state[3:6]) - earth_velocity
    return burn_size(relative_velocity, delta)

def apply_burn(state, delta_v):
    # state = [x, y, z, vx, vy, vz]
    # delta_v = [dvx, dvy, dvz]
    # return the updated state
    return [state[0], state[1], state[2], state[3] + delta_v[0], state[4] + delta_v[1], state[5] + delta_v[2]]

def error(c_state, t_state):
    J_r = abs(c_state[0] - t_state[0])**2 + abs(c_state[1] - t_state[1])**2 + abs(c_state[2] - t_state[2])**2
    J_v = abs(c_state[3] - t_state[3])**2 + abs(c_state[4] - t_state[4])**2 + abs(c_state[5] - t_state[5])**2
    return J_r, J_v

def fuel_usage(burns):
    return sum(np.linalg.norm(delta_v) for delta_v, _ in burns)

def cost(errors, weights, burns):
    J_r, J_v = errors
    w_r, w_v, w_delta_v = weights

    return (
        w_r * J_r
        + w_v * J_v
        + w_delta_v * fuel_usage(burns)
    )

# Assumptions:
# All variables are provided correctly
# Burns are executed in the order that they are stored in the burns array
# Every burn is unique

def score(burns, chaser_state, t_sol, t_span, weights, body_solution):
    burns = np.asarray(burns).reshape(-1, 2)

    burn_times = burns[:, 1]
    if (
        np.any(burn_times < t_span[0])
        or np.any(burn_times > t_span[1])
        or np.any(np.diff(burn_times) <= 0)
    ):
        return np.inf


    previous_time = t_span[0]
    c_sol = 0
    for dv, time in burns:
        c_sol = solve_ivp(n_body_ode, (previous_time, time), chaser_state, args=(body_solution,), method='DOP853', rtol=1e-6)
        
        c_before_burn_state = c_sol.y[:, -1]
        burn = earth_relative_burn(c_before_burn_state, dv, time, body_solution)
        chaser_state = apply_burn(c_before_burn_state, burn)

        previous_time = time

    c_final_sol = solve_ivp(n_body_ode, (previous_time, t_span[1]), chaser_state, args=(body_solution,), method='DOP853', rtol=1e-6)
    
    c_final_state = c_final_sol.y[:, -1]
    t_final_state = t_sol.sol(t_span[1])

    return cost(error(c_final_state, t_final_state), weights, burns)

def trajectory(c_state, t_state, t_span, burns, weights, body_solution, samples_per_segment=1000):
    target_times = np.linspace(t_span[0], t_span[1], samples_per_segment * (len(burns) + 1))
    target_sol = solve_ivp(
        n_body_ode,
        t_span,
        t_state,
        args=(body_solution,),
        t_eval=target_times,
        dense_output=True,
        method='DOP853',
        rtol=1e-6
    )

    chaser_times = []
    chaser_states = []
    burn_times = []
    burn_states = []
    previous_time = t_span[0]
    current_state = c_state
    t_sol = target_sol
    target_loc_burn_n = []


    for dv, burn_time in burns:
        segment_times = np.linspace(previous_time, burn_time, samples_per_segment)
        segment_sol = solve_ivp(
            n_body_ode,
            (previous_time, burn_time),
            current_state,
            args=(body_solution,),
            t_eval=segment_times,
            method='DOP853',
            rtol=1e-6
        )

        target_loc_burn_n.append(t_sol.sol(segment_times))

        start_index = 0 if not chaser_times else 1
        chaser_times.extend(segment_sol.t[start_index:])
        chaser_states.extend(segment_sol.y[:, start_index:].T)

        state_before_burn = segment_sol.y[:, -1]
        burn_times.append(burn_time)
        burn_states.append(state_before_burn.copy())
        current_state = apply_burn(
            state_before_burn,
            earth_relative_burn(state_before_burn, dv, burn_time, body_solution)
        )
        previous_time = burn_time

    final_times = np.linspace(previous_time, t_span[1], samples_per_segment)
    final_sol = solve_ivp(
        n_body_ode,
        (previous_time, t_span[1]),
        current_state,
        args=(body_solution,),
        t_eval=final_times,
        method='DOP853',
        rtol=1e-6
    )
    chaser_times.extend(final_sol.t[1:])
    chaser_states.extend(final_sol.y[:, 1:].T)

    target_loc_burn_n.append(t_sol.sol(np.linspace(previous_time, t_span[1], 5000)))
    t_final_state = t_sol.sol(t_span[1])

    return (
        np.asarray(chaser_times),
        np.asarray(chaser_states),
        target_sol,
        np.asarray(burn_times),
        np.asarray(burn_states)
    ), cost(error(chaser_states[len(chaser_states)-1], t_final_state), weights, burns), target_loc_burn_n

def rendezvous(c_state0, t_state0, num_burns, weights, t_span, body_solution):
    bounds = [(-MAX_BURN_DELTA_V, MAX_BURN_DELTA_V), (t_span[0] + 60, t_span[1] - 60)] * num_burns
    t_eval = np.linspace(t_span[0], t_span[1], 5000)
    t_sol = solve_ivp(n_body_ode, t_span, t_state0, args=(body_solution,), t_eval=t_eval, dense_output=True, method='DOP853', rtol=1e-6)
    result = differential_evolution(
        score, 
        bounds=bounds,
        args=(c_state0, t_sol, t_span, weights, body_solution),
        rng=np.random.default_rng(42))

    return result.x, result.fun


def plot_rendezvous(history, body_solution):
    """Plot 3D separation and spacecraft tracks in two translating frames.

    Each spacecraft position is offset by the reference body's position at
    that same time. Axes remain aligned with the J2000 ecliptic frame.
    """
    chaser_times, chaser_states, target_sol, burn_times, burn_states = history
    target_at_chaser = target_sol.sol(chaser_times)
    separation = np.linalg.norm(chaser_states[:, :3] - target_at_chaser[:3].T, axis=1)
    target_at_burns = target_sol.sol(burn_times)
    burn_separations = np.linalg.norm(burn_states[:, :3] - target_at_burns[:3].T, axis=1)

    fig = plt.figure(figsize=(19, 6))
    distance_ax = fig.add_subplot(131)
    distance_ax.plot(chaser_times / 3600, separation / 1000, label="Chaser-target distance")
    distance_ax.scatter(burn_times / 3600, burn_separations / 1000, color="red", label="Burns")
    for number, (time, distance) in enumerate(zip(burn_times, burn_separations), 1):
        distance_ax.axvline(time / 3600, color="red", linestyle="--", linewidth=0.8, alpha=0.5)
        distance_ax.annotate(f"Burn {number}", (time / 3600, distance / 1000),
                             xytext=(5, 7), textcoords="offset points")
    distance_ax.set(xlabel="Time (hours)", ylabel="3D separation (km)",
                    title="Rendezvous separation over time")
    distance_ax.grid(True)
    distance_ax.legend()

    sun_ax = fig.add_subplot(132, projection="3d")
    earth_ax = fig.add_subplot(133, projection="3d")
    for ax, reference_index, scale, unit, title in (
        (sun_ax, 0, system.AU, "AU", "Sun-centered system and spacecraft"),
        (earth_ax, 1, 1000.0, "km", "Earth-centered rendezvous close-up"),
    ):
        start = 6 * reference_index
        # The target, chaser and burns have different sampling grids.
        chaser_reference = body_solution.sol(chaser_times)[start:start + 3].T
        target_reference = body_solution.sol(target_sol.t)[start:start + 3]
        burn_reference = body_solution.sol(burn_times)[start:start + 3].T
        chaser_xyz = (chaser_states[:, :3] - chaser_reference) / scale
        target_xyz = (target_sol.y[:3] - target_reference).T / scale
        burn_xyz = (burn_states[:, :3] - burn_reference) / scale

        ax.plot(*target_xyz.T, color="tab:blue", label="Target")
        ax.plot(*chaser_xyz.T, color="tab:orange", label="Chaser")
        for name, xyz, color in (("Target", target_xyz, "tab:blue"),
                                 ("Chaser", chaser_xyz, "tab:orange")):
            ax.scatter(*xyz[0], color=color, marker="o", label=f"{name} initial")
            ax.scatter(*xyz[-1], color=color, marker="s", label=f"{name} final")
        ax.scatter(*burn_xyz.T, color="red", marker="x", label="Burns")
        for number, xyz in enumerate(burn_xyz, 1):
            ax.text(*xyz, f" Burn {number}", color="red")

        if reference_index == 0:
            # Show the complete four-body context, even when spacecraft
            # separation is too small to resolve at the Jupiter/AU scale.
            body_states = body_solution.sol(chaser_times).reshape(len(system.BODY_NAMES), 6, -1)
            surface_bounds = []
            for index, (name, color) in enumerate(zip(system.BODY_NAMES, system.COLORS)):
                xyz = (body_states[index, :3] - body_states[0, :3]) / scale
                radius = system.BODY_RADII[index] / scale
                system.plot_body_surface(ax, xyz[:, -1], radius, color)
                surface_bounds.extend((xyz[:, -1] - radius, xyz[:, -1] + radius))
                ax.plot(*xyz, color=color, label=name)
                ax.scatter(*xyz[:, 0], color=color, marker="o")
                ax.scatter(*xyz[:, -1], color=color, marker="s")
            points = np.concatenate((chaser_xyz, target_xyz, surface_bounds,
                                     ((body_states[:, :3] - body_states[0, :3]) / scale)
                                     .transpose(0, 2, 1).reshape(-1, 3)))
        else:
            # Earth's surface is centered on the current Earth, not the
            # fixed integration origin. Omit distant bodies for readability.
            radius_km = system.BODY_RADII[1] / scale
            system.plot_body_surface(ax, np.zeros(3), radius_km, "steelblue", alpha=0.2)
            ax.scatter(0, 0, 0, color="steelblue", label="Earth")
            points = np.concatenate((chaser_xyz, target_xyz,
                                     [[-radius_km] * 3, [radius_km] * 3]))

        system.set_equal_3d_limits(ax, points)
        ax.set(xlabel=f"x ({unit})", ylabel=f"y ({unit})", zlabel=f"z ({unit})", title=title)
        ax.legend(fontsize="small")
    fig.suptitle("Best rendezvous — true-scale body surfaces; spacecraft and event markers not to scale")
    fig.tight_layout()
    return fig


def main(weights):
    def read_state(spacecraft_name):
        while True:
            raw_state = input(
                f"Enter the {spacecraft_name} initial state x y z vx vy vz in SI units: "
            )
            try:
                state = [float(value) for value in raw_state.replace(",", " ").split()]
            except ValueError:
                print("Enter six numeric values separated by spaces or commas.")
                continue

            if len(state) == 6 and np.all(np.isfinite(state)):
                return state
            print("The state must contain exactly six finite values: x y z vx vy vz.")

    print("Positions are Earth-centered in metres; velocities are in metres per second.")
    print("Axes must align with the J2000 ecliptic axes (not Earth-rotating axes).")
    chaser_state = read_state("chaser")
    target_state = read_state("target")

    while True:
        try:
            num_burns = int(input("Enter the number of chaser burns: "))
            if num_burns > 0:
                break
        except ValueError:
            pass
        print("The number of burns must be a positive integer.")

    while True:
        try:
            final_time = float(input("Enter the mission duration in seconds: "))
            if np.isfinite(final_time) and final_time > 120:
                break
        except ValueError:
            pass
        print("Mission duration must be greater than 120 seconds.")

    print(f"Final Time: {final_time:.2f}")

    t_span = (0, final_time)

    initial_states = system.get_initial_states()
    chaser_state = (np.asarray(chaser_state) + initial_states[1])
    target_state = (np.asarray(target_state) + initial_states[1])

    body_solution = system.simulate_system(initial_states, final_time)

    best_parameters, optimizer_score = rendezvous(
        chaser_state,
        target_state,
        num_burns,
        weights,
        t_span,
        body_solution,
    )
    best_burns = np.asarray(best_parameters).reshape(num_burns, 2)
    history, trajectory_score, _ = trajectory(
        chaser_state,
        target_state,
        t_span,
        best_burns,
        weights,
        body_solution,
    )

    chaser_times, chaser_states, target_sol, burn_times, burn_states = history
    target_at_chaser_times = target_sol.sol(chaser_times)
    separation = np.linalg.norm(chaser_states[:, :3] - target_at_chaser_times[:3].T, axis=1)

    print(f"Optimizer score: {optimizer_score:.6f}")
    print(f"Trajectory score: {trajectory_score:.6f}")
    print("Best burns (delta-v in m/s, time in s):")
    for burn_number, (delta_v, burn_time) in enumerate(best_burns, 1):
        print(f"  Burn {burn_number}: delta-v={delta_v:.3f}, time={burn_time:.3f}")
    print(f"Final separation: {separation[-1]:.3f} m")
    minimum_index = np.argmin(separation)
    print(f"Minimum sampled separation: {separation[minimum_index]:.3f} m "
          f"at {chaser_times[minimum_index]:.3f} s")

    system.plot_system(body_solution, system.DEFAULT_EPOCH)
    plot_rendezvous(history, body_solution)
    plt.show()

    return best_burns, optimizer_score, history


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a rendezvous with position, velocity and delta-v weights.")
    parser.add_argument("weights", nargs=3, type=float, metavar="WEIGHT",
                        help="Three positive weights: position velocity delta-v")
    arguments = parser.parse_args()
    if not all(np.isfinite(value) and value > 0 for value in arguments.weights):
        parser.error("Weights must be positive and finite.")
    main(tuple(arguments.weights))

    
    

# Defining coordinates instead of x and y but as velocity and position relative to earth
# 3 steps for rendezvous
# 1. Kick your orbit
# 2. Wait until close
# 3. Rendezvous Maneuver
