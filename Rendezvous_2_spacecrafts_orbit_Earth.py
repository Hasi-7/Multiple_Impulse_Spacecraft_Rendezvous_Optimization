from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution
import numpy as np
import matplotlib.pyplot as plt
mu = 3.986 * 10**14
earth_radius = 6.371e6
theta = np.linspace(0, 2*np.pi, 300)
starting_distance_x = 7_000_000
starting_distance_y = 0
    

def two_body_ode(t, state):
    # unpack state
    x = state[0]
    y = state[1]
    vx = state[2]
    vy = state[3]
    

    # compute distance from Earth
    r = (x**2 + y**2)**0.5

    # compute acceleration from gravity
    ax = -mu * (x / r**3)
    ay = -mu * (y / r**3)

    # return derivatives
    return [vx, vy, ax, ay]

def burn_size(v, delta):
    unit_v = v/np.linalg.norm(v)
    return delta * unit_v

def apply_burn(state, delta_v):
    # state = [x, y, vx, vy]
    # delta_v = [dvx, dvy]
    # return the updated state
    return [state[0], state[1], state[2] + delta_v[0], state[3] + delta_v[1]]

def error(c_state, t_state):
    J_r = abs(c_state[0] - t_state[0])**2 + abs(c_state[1] - t_state[1])**2
    J_v = abs(c_state[2] - t_state[2])**2 + abs(c_state[3] - t_state[3])**2
    return J_r, J_v

def fuel_usage(burns):
    return sum(np.linalg.norm(delta_v) for delta_v, _ in burns)

# Switch to List of Tuples

def cost(errors, weights, burns):
    J_r, J_v = errors
    w_r, w_v, w_delta_v = weights

    return (
        w_r * J_r
        + w_v * J_v
        + w_delta_v * fuel_usage(burns)
    )

def period(state):
    r = (state[0]**2 + state[1]**2)**0.5
    v = (state[2]**2 + state[3]**2)**0.5
    a = (-1)*((mu*r)/((r*(v**2)) - (2*mu)))
    return 2*np.pi*(((a**3)/mu)**0.5)

def synodic_period(c_state, t_state):
    T1 = period(c_state)
    T2 = period(t_state)
    return ((T1*T2)/(abs(T2-T1)))

# Assumptions:
# All variables are provided correctly
# Burns are executed in the order that they are stored in the burns array
# Every burn is unique

def score(burns, chaser_state, t_sol, t_span, weights):
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
        

        
        c_sol = solve_ivp(two_body_ode, (previous_time, time), chaser_state, method='DOP853', rtol=1e-6)
        
        c_before_burn_state = c_sol.y[:, -1]
        burn = burn_size(c_before_burn_state[2:4], dv)
        chaser_state = apply_burn(c_before_burn_state, burn)

        previous_time = time

    c_final_sol = solve_ivp(two_body_ode, (previous_time, t_span[1]), chaser_state, method='DOP853', rtol=1e-6)
    
    c_final_state = c_final_sol.y[:, -1]
    t_final_state = t_sol.sol(t_span[1])

    return cost(error(c_final_state, t_final_state), weights, burns)

def trajectory(c_state, t_state, t_span, burns, weights, samples_per_segment=1000):
    target_times = np.linspace(t_span[0], t_span[1], samples_per_segment * (len(burns) + 1))
    target_sol = solve_ivp(
        two_body_ode,
        t_span,
        t_state,
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
    t_sol = 0
    target_loc_burn_n = []


    for dv, burn_time in burns:
        segment_times = np.linspace(previous_time, burn_time, samples_per_segment)
        segment_sol = solve_ivp(
            two_body_ode,
            (previous_time, burn_time),
            current_state,
            t_eval=segment_times,
            method='DOP853',
            rtol=1e-6
        )

        t_sol = solve_ivp(two_body_ode, t_span, t_state, t_eval=target_times, dense_output=True, method='DOP853', rtol=1e-6)
        target_loc_burn_n.append(t_sol.sol(segment_times))

        start_index = 0 if not chaser_times else 1
        chaser_times.extend(segment_sol.t[start_index:])
        chaser_states.extend(segment_sol.y[:, start_index:].T)

        state_before_burn = segment_sol.y[:, -1]
        burn_times.append(burn_time)
        burn_states.append(state_before_burn.copy())
        current_state = apply_burn(
            state_before_burn,
            burn_size(state_before_burn[2:4], dv)
        )
        previous_time = burn_time

    final_times = np.linspace(previous_time, t_span[1], samples_per_segment)
    final_sol = solve_ivp(
        two_body_ode,
        (previous_time, t_span[1]),
        current_state,
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

def rendezvous(c_state0, t_state0, num_burns, weights, t_span):
    bounds = [(-500, 500), (t_span[0] + 60, t_span[1] - 60)] * num_burns
    t_eval = np.linspace(t_span[0], t_span[1], 5000)
    t_sol = solve_ivp(two_body_ode, t_span, t_state0, t_eval=t_eval, dense_output=True, method='DOP853', rtol=1e-6)
    result = differential_evolution(
        score, 
        bounds=bounds,
        args=(c_state0, t_sol, t_span, weights),
        rng=np.random.default_rng(42))

    return result.x, result.fun



# set margin of error of 50 meters from target to define rendezvous complete
# def rendezvous(c_state0, t_state0, t_span, t_eval):
#     J_r, J_v = error(c_state0, t_state0)
#     burns = []
#     c_sol = []
#     t_sol = solve_ivp(two_body_ode, t_span, t_state0, t_eval=t_eval, dense_output=True, method='DOP853', rtol=1e-6)

#     # First determine the relative phase angle of the target and chaser (In radians)
#     while(J_r > 2500 and J_v == 0):

#         theta_c = np.arctan2(c_state0[1], c_state0[0])
#         theta_t = np.arctan2(t_state0[1], t_state0[0])
#         phase_error = (theta_t - theta_c + np.pi) % (2 * np.pi) - np.pi

#         angular_momentum = c_state0[0] * c_state0[3] - c_state0[1] * c_state0[2]
#         orbit_direction = 0
#         if angular_momentum > 0:
#             orbit_direction = 1
#         else:
#             orbit_direction = -1

#         burn_direction = 0
#         if phase_error > 0:
#             burn_direction = -1 * orbit_direction
#         else:
#             burn_direction = 1 * orbit_direction

# Old Main Function        
# speeds = [(mu/starting_distance_x)**0.5]
# t_start = 0
# t_end = 20 * 60 * 60
# t_burn = 2 * 60 * 60
# t_marker = 2 * 60 * 60
# t_eval_burn = np.linspace(t_start, t_burn, 5000)
# t_eval_end = np.linspace(t_burn, t_end, 5000)
# t_eval = np.linspace(t_start, t_end, 5000)
# t_span = (t_start, t_end)
# # burn = [50, 100]

# target_state0 = [starting_distance_x, starting_distance_y, 0, speeds[0]]
# chaser_state0 = [starting_distance_x, -500_000, 500, speeds[0]]

# target_sol = solve_ivp(two_body_ode, t_span, target_state0, t_eval=t_eval, dense_output=True, method='DOP853', rtol=1e-6)
# chaser_sol = solve_ivp(two_body_ode, (t_start, t_burn), chaser_state0, t_eval=t_eval_burn, dense_output=True, method='DOP853', rtol=1e-6)

# target_marker_state = target_sol.sol(t_burn)
# chaser_before_burn_state = chaser_sol.y[:, -1]

# burn = burn_size(chaser_before_burn_state[2:4], 1000)

# chaser_after_burn_state = apply_burn(chaser_before_burn_state, burn)

# chaser_sol2 = solve_ivp(two_body_ode, (t_burn, t_end), chaser_after_burn_state, t_eval=t_eval_end, dense_output=True, method='DOP853', rtol=1e-6)

# target_before = target_sol.sol(t_eval_burn)
# target_after = target_sol.sol(t_eval_end)

# dx_before = chaser_sol.y[0] - target_before[0]
# dy_before = chaser_sol.y[1] - target_before[1]
# distance_before = np.sqrt(dx_before**2 + dy_before**2)

# dx_after = chaser_sol2.y[0] - target_after[0]
# dy_after = chaser_sol2.y[1] - target_after[1]
# distance_after = np.sqrt(dx_after**2 + dy_after**2)
# distance_all = np.concatenate((distance_before, distance_after))
# min_index = np.argmin(distance_all)

def main():
    def read_state(spacecraft_name):
        while True:
            raw_state = input(
                f"Enter the {spacecraft_name} initial state x y vx vy in SI units: "
            )
            try:
                state = [float(value) for value in raw_state.replace(",", " ").split()]
            except ValueError:
                print("Enter four numeric values separated by spaces or commas.")
                continue

            if len(state) == 4:
                return state
            print("The state must contain exactly four values: x y vx vy.")

    print("Positions are Earth-centered in metres; velocities are in metres per second.")
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
            if final_time > 120:
                break
        except ValueError:
            pass
        print("Mission duration must be greater than 120 seconds.")

    # while True:
    #     try:
    #         n = float(input("Enter number of periods as an integer: "))
    #         if n > 0:
    #             break
    #     except ValueError:
    #         pass
    #     print("The number of periods must be a positive integer.")

    # period = synodic_period(chaser_state, target_state)
    # final_time = period * n
    print(f"Final Time: {final_time:.2f}")
    # print(f"Synodic Period: {period:.2f}")

    t_span = (0, final_time)
    weights = (1 / 100_00**2, 1 / 10**2, 1 / 1000)
    best_parameters, optimizer_score = rendezvous(
        chaser_state,
        target_state,
        num_burns,
        weights,
        t_span
    )
    best_burns = np.asarray(best_parameters).reshape(num_burns, 2)
    history, trajectory_score, _ = trajectory(
        chaser_state,
        target_state,
        t_span,
        best_burns,
        weights
    )

    chaser_times, chaser_states, target_sol, burn_times, burn_states = history
    target_at_chaser_times = target_sol.sol(chaser_times)
    separation = np.linalg.norm(chaser_states[:, :2] - target_at_chaser_times[:2].T, axis=1)
    target_at_burns = target_sol.sol(burn_times)
    burn_separations = np.linalg.norm(burn_states[:, :2] - target_at_burns[:2].T, axis=1)

    print(f"Optimizer score: {optimizer_score:.6f}")
    print(f"Trajectory score: {trajectory_score:.6f}")
    print("Best burns (delta-v in m/s, time in s):")
    for burn_number, (delta_v, burn_time) in enumerate(best_burns, 1):
        print(f"  Burn {burn_number}: delta-v={delta_v:.3f}, time={burn_time:.3f}")
    print(f"Final separation: {separation[-1]:.3f} m")

    plt.figure(figsize=(9, 5))
    plt.plot(chaser_times / 3600, separation / 1000, label="Chaser-target distance")
    plt.scatter(burn_times / 3600, burn_separations / 1000, color="red", zorder=3, label="Burns")
    for burn_number, (burn_time, burn_distance) in enumerate(zip(burn_times, burn_separations), 1):
        plt.axvline(burn_time / 3600, color="red", linestyle="--", linewidth=0.8, alpha=0.5)
        plt.annotate(f"Burn {burn_number}", (burn_time / 3600, burn_distance / 1000), xytext=(5, 7), textcoords="offset points")
    plt.xlabel("Time (hours)")
    plt.ylabel("Distance (km)")
    plt.title("Best Rendezvous: Separation Over Time")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.figure(figsize=(8, 8))
    plt.plot(target_sol.y[0] / 1000, target_sol.y[1] / 1000, label="Target")
    phase_boundaries = np.concatenate(([chaser_times[0]], burn_times, [chaser_times[-1]]))
    phase_colors = plt.get_cmap("plasma")(np.linspace(0.15, 0.85, len(phase_boundaries) - 1))
    for phase_index, (phase_start, phase_end) in enumerate(zip(phase_boundaries[:-1], phase_boundaries[1:])):
        phase_mask = (chaser_times >= phase_start) & (chaser_times <= phase_end)
        phase_label = "Chaser before burn 1" if phase_index == 0 else f"Chaser after burn {phase_index}"
        plt.plot(
            chaser_states[phase_mask, 0] / 1000,
            chaser_states[phase_mask, 1] / 1000,
            color=phase_colors[phase_index],
            label=phase_label
        )
    plt.scatter(burn_states[:, 0] / 1000, burn_states[:, 1] / 1000, color="red", zorder=3, label="Burns")
    plt.scatter(
        chaser_states[0, 0] / 1000,
        chaser_states[0, 1] / 1000,
        color=phase_colors[0],
        edgecolor="black",
        marker="o",
        s=80,
        zorder=5,
        label="Chaser start"
    )
    plt.scatter(
        target_sol.y[0, 0] / 1000,
        target_sol.y[1, 0] / 1000,
        color="tab:blue",
        edgecolor="black",
        marker="o",
        s=80,
        zorder=5,
        label="Target start"
    )
    plt.scatter(target_sol.y[0, -1] / 1000, target_sol.y[1, -1] / 1000, color="tab:blue", marker="s", s=70, zorder=4, label="Target at end time")
    plt.scatter(chaser_states[-1, 0] / 1000, chaser_states[-1, 1] / 1000, color="tab:orange", marker="s", s=70, zorder=4, label="Chaser at end time")
    for burn_number, burn_state in enumerate(burn_states, 1):
        plt.annotate(f"Burn {burn_number}", (burn_state[0] / 1000, burn_state[1] / 1000), xytext=(6, 6), textcoords="offset points")
    plt.fill(earth_radius * np.cos(theta) / 1000, earth_radius * np.sin(theta) / 1000, color="steelblue", alpha=0.35, label="Earth")
    plt.axis("equal")
    plt.xlabel("x position (km)")
    plt.ylabel("y position (km)")
    plt.title("Best Rendezvous Trajectory")
    plt.grid(True)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.show()

    return best_burns, optimizer_score, history


if __name__ == "__main__":
    main()

    
    

# Defining coordinates instead of x and y but as velocity and position relative to earth
# 3 steps for rendezvous
# 1. Kick your orbit
# 2. Wait until close
# 3. Rendezvous Maneuver
