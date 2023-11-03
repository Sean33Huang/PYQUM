"""
This file contains useful QUA macros meant to simplify and ease QUA programs.
All the macros below have been written and tested with the basic configuration. If you modify this configuration
(elements, operations, integration weights...) these macros will need to be modified accordingly.
"""

from qm.qua import *
from qualang_tools.addons.variables import assign_variables_to_element
from qualang_tools.results import fetching_tool, progress_counter
from qualang_tools.plot import interrupt_on_close
from configuration import *

import matplotlib.pyplot as plt
from scipy import signal
from scipy.optimize import curve_fit

##############
# QUA macros #
##############


def cz_gate(type="square"):
    if type == "square":
        wait(5)  # for flux pulse to relax back completely
        set_dc_offset("q2_z", "single", 0.14519591) # 10cc: 0.1452099
        wait(48 // 4, "q2_z")
        align()
        set_dc_offset("q2_z", "single", idle_q2)
        wait(5)  # for flux pulse to relax back completely
    elif type == "ft_gaussian":
        play("cz_1_2"*amp((0.150-max_frequency_point2)/(cz_point_1_2_q2-idle_q2)), "q2_z", duration=80//4)
    elif type == "gaussian":
        play("cz_1_2"*amp(1.4), "q2_z", duration=32//4)


def multiRO_measurement( iqdata_stream, resonators:list, freq_IF:list=None, sequential=False, amp_modify=1.0, weights=""):
    """
        RO pulse
    """
    (I, I_st, Q, Q_st) = iqdata_stream
    if type(resonators) is not list:
        resonators = [resonators]
        
    ro_channel_num = len(resonators)


    for idx, res in enumerate(resonators):
        if isinstance(freq_IF ,list):
            update_frequency(res, freq_IF[idx])

        measure(
            "readout" * amp(amp_modify),
            f"{res}",
            None,
            dual_demod.full(weights + "cos", "out1", weights + "sin", "out2", I[idx]),
            dual_demod.full(weights + "minus_sin", "out1", weights + "cos", "out2", Q[idx]),
        )

        if I_st is not None:
            save(I[idx], I_st[idx])
        if Q_st is not None:
            save(Q[idx], Q_st[idx])

        if sequential and idx < ro_channel_num -1:
            align(f"{res}", f"{resonators[idx+1]}")

def multiRO_pre_save( iqdata_stream, resonators:list, buffer_shape:tuple ):
    """
    Save RO pulse signal on FPGA
    """
    (I, I_st, Q, Q_st) = iqdata_stream
    if type(resonators) is not list:
        resonators = [resonators]
        
    ro_channel_num = len(resonators)
    for idx_res, res in enumerate(resonators):
        I_st[idx_res].buffer(*buffer_shape).average().save(f"{res}_I")
        Q_st[idx_res].buffer(*buffer_shape).average().save(f"{res}_Q")  
        # I_st[idx_res].average().save(f"{res}_I")
        # Q_st[idx_res].average().save(f"{res}_Q")    

def multiRO_declare( resonators:list ):
    """
    Macro to declare the necessary QUA variables

    :param resonators: name of the element for resonator
    :return: I, I_st, Q, Q_st
    """
    if type(resonators) is not list:
        resonators = [resonators]

    ro_channel_num = len(resonators)

    I = [declare(fixed) for _ in range(ro_channel_num)]
    Q = [declare(fixed) for _ in range(ro_channel_num)]
    I_st = [declare_stream() for _ in range(ro_channel_num)]
    Q_st = [declare_stream() for _ in range(ro_channel_num)]
    # Workaround to manually assign the results variables to the readout elements
    for idx, ele_name in enumerate(resonators):
        assign_variables_to_element( ele_name, I[idx], Q[idx])
    return I, I_st, Q, Q_st


def reset_qubit(method: str, qubit: str, resonator: str, **kwargs):
    """
    Macro to reset the qubit state.

    If method is 'cooldown', then the variable cooldown_time (in clock cycles) must be provided as a python integer > 4.

    **Example**: reset_qubit('cooldown', cooldown_times=500)

    If method is 'active', then 3 parameters are available as listed below.

    **Example**: reset_qubit('active', threshold=-0.003, max_tries=3)

    :param method: Method the reset the qubit state. Can be either 'cooldown' or 'active'.
    :param qubit: The qubit element. Must be defined in the config.
    :param resonator: The resonator element. Must be defined in the config.
    :key cooldown_time: qubit relaxation time in clock cycle, needed if method is 'cooldown'. Must be an integer > 4.
    :key threshold: threshold to discriminate between the ground and excited state, needed if method is 'active'.
    :key max_tries: python integer for the maximum number of tries used to perform active reset,
        needed if method is 'active'. Must be an integer > 0 and default value is 1.
    :key Ig: A QUA variable for the information in the `I` quadrature used for active reset. If not given, a new
        variable will be created. Must be of type `Fixed`.
    :return:
    """
    if method == "cooldown":
        # Check cooldown_time
        cooldown_time = kwargs.get("cooldown_time", None)
        if (cooldown_time is None) or (cooldown_time < 4):
            raise Exception("'cooldown_time' must be an integer > 4 clock cycles")
        # Reset qubit state
        wait(cooldown_time, qubit)
    elif method == "active":
        # Check threshold
        threshold = kwargs.get("threshold", None)
        if threshold is None:
            raise Exception("'threshold' must be specified for active reset.")
        # Check max_tries
        max_tries = kwargs.get("max_tries", 1)
        if (max_tries is None) or (not float(max_tries).is_integer()) or (max_tries < 1):
            raise Exception("'max_tries' must be an integer > 0.")
        # Check Ig
        Ig = kwargs.get("Ig", None)
        # Reset qubit state
        return active_reset(threshold, qubit, resonator, max_tries=max_tries, Ig=Ig)


# Macro for performing active reset until successful for a given number of tries.
def active_reset(threshold: float, qubit: str, resonator: str, max_tries=1, Ig=None):
    """Macro for performing active reset until successful for a given number of tries.

    :param threshold: threshold for the 'I' quadrature discriminating between ground and excited state.
    :param qubit: The qubit element. Must be defined in the config.
    :param resonator: The resonator element. Must be defined in the config.
    :param max_tries: python integer for the maximum number of tries used to perform active reset. Must >= 1.
    :param Ig: A QUA variable for the information in the `I` quadrature. Should be of type `Fixed`. If not given, a new
        variable will be created
    :return: A QUA variable for the information in the `I` quadrature and the number of tries after success.
    """
    if Ig is None:
        Ig = declare(fixed)
    if (max_tries < 1) or (not float(max_tries).is_integer()):
        raise Exception("max_count must be an integer >= 1.")
    # Initialize Ig to be > threshold
    assign(Ig, threshold + 2**-28)
    # Number of tries for active reset
    counter = declare(int)
    # Reset the number of tries
    assign(counter, 0)

    # Perform active feedback
    align(qubit, resonator)
    # Use a while loop and counter for other protocols and tests
    with while_((Ig > threshold) & (counter < max_tries)):
        # Measure the resonator
        measure(
            "readout",
            resonator,
            None,
            dual_demod.full("rotated_cos", "out1", "rotated_sin", "out2", Ig),
        )
        # Play a pi pulse to get back to the ground state
        play("x180", qubit, condition=(Ig > threshold))
        # Increment the number of tries
        assign(counter, counter + 1)
    return Ig, counter


# Exponential decay
def expdecay(x, a, t):
    """Exponential decay defined as 1 + a * np.exp(-x / t).

    :param x: numpy array for the time vector in ns
    :param a: float for the exponential amplitude
    :param t: float for the exponential decay time in ns
    :return: numpy array for the exponential decay
    """
    return 1 + a * np.exp(-x / t)


# Theoretical IIR and FIR taps based on exponential decay coefficients
def exponential_correction(A, tau, Ts=1e-9):
    """Derive FIR and IIR filter taps based on a the exponential coefficients A and tau from 1 + a * np.exp(-x / t).

    :param A: amplitude of the exponential decay
    :param tau: decay time of the exponential decay
    :param Ts: sampling period. Default is 1e-9
    :return: FIR and IIR taps
    """
    tau = tau * Ts
    k1 = Ts + 2 * tau * (A + 1)
    k2 = Ts - 2 * tau * (A + 1)
    c1 = Ts + 2 * tau
    c2 = Ts - 2 * tau
    feedback_tap = k2 / k1
    feedforward_taps = np.array([c1, c2]) / k1
    return feedforward_taps, feedback_tap


# FIR and IIR taps calculation
def filter_calc(exponential):
    """Derive FIR and IIR filter taps based on a list of exponential coefficients.

    :param exponential: exponential coefficients defined as [(A1, tau1), (A2, tau2)]
    :return: FIR and IIR taps as [fir], [iir]
    """
    # Initialization based on the number of exponential coefficients
    b = np.zeros((2, len(exponential)))
    feedback_taps = np.zeros(len(exponential))
    # Derive feedback tap for each set of exponential coefficients
    for i, (A, tau) in enumerate(exponential):
        b[:, i], feedback_taps[i] = exponential_correction(A, tau)
    # Derive feddback tap for each set of exponential coefficients
    feedforward_taps = b[:, 0]
    for i in range(len(exponential) - 1):
        feedforward_taps = np.convolve(feedforward_taps, b[:, i + 1])
    # feedforward taps are bounded to +/- 2
    if np.abs(max(feedforward_taps)) >= 2:
        feedforward_taps = 2 * feedforward_taps / max(feedforward_taps)

    return feedforward_taps, feedback_taps


# Plotting

# Fitting:

# Fitting to cosine resonator frequency response
def cosine_func(x, amplitude, frequency, phase, offset):
    return amplitude * np.cos(2 * np.pi * frequency * x + phase) + offset

def fit_plotting(x_range, y_range, q_id, stage):
    if stage=="6b":
        minima = np.zeros(len(x_range)) # Array for the flux minima
        # Frequency range for the 3 resonators
        frequencies = [(y_range + resonator_IF[i]) for i in q_id]
        # Amplitude for the 3 resonators
        R = [R1, R2, R3]
        plt.figure()
        for rr in q_id:
            print(f"Resonator rr{rr+1}")
            # Find the resonator frequency vs flux minima
            for i in range(len(x_range)):
                minima[i] = frequencies[q_id.index(rr)][np.argmin(R[rr].T[i])]

            # Cosine fit
            initial_guess = [1, 0.5, 0, 0]  # Initial guess for the parameters
            fit_params, _ = curve_fit(cosine_func, x_range, minima, p0=initial_guess)

            # Get the fitted values
            amplitude_fit, frequency_fit, phase_fit, offset_fit = fit_params
            print("fitting parameters", fit_params)

            # Generate the fitted curve using the fitted parameters
            fitted_curve = cosine_func(x_range, amplitude_fit, frequency_fit, phase_fit, offset_fit)
            plt.subplot(3, 1, rr + 1)
            plt.pcolor(x_range, frequencies[rr] / u.MHz, R1)
            plt.plot(x_range, minima / u.MHz, "x-", color="red", label="Flux minima")
            plt.plot(x_range, fitted_curve / u.MHz, label="Fitted Cosine", color="orange")
            plt.xlabel("Flux bias [V]")
            plt.ylabel("Readout IF [MHz]")
            plt.title(f"Resonator rr{rr+1}")
            plt.legend()
            plt.tight_layout()
            plt.show()

            print(
                f"DC flux value corresponding to the maximum frequency point for resonator {rr}: {x_range[np.argmax(fitted_curve)]}"
            )
    

