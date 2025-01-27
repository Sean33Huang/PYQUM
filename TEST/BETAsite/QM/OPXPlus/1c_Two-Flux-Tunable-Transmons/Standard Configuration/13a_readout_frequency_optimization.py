"""
        READOUT OPTIMISATION: FREQUENCY
This sequence involves measuring the state of the resonator in two scenarios: first, after thermalization
(with the qubit in the |g> state) and then after applying a pi pulse to the qubit (transitioning the qubit to the
|e> state). This is done while varying the readout frequency.
The average I & Q quadratures for the qubit states |g> and |e>, along with their variances, are extracted to
determine the Signal-to-Noise Ratio (SNR). The readout frequency that yields the highest SNR is selected as the
optimal choice.

Prerequisites:
    - Having found the resonance frequency of the resonator coupled to the qubit under study (resonator_spectroscopy).
    - Having calibrated qubit pi pulse (x180) by running qubit, spectroscopy, rabi_chevron, power_rabi and updated the config.
    - Set the desired flux bias

Next steps before going to the next node:
    - Update the readout frequency (resonator_IF_q) in the configuration.
"""

from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import *
from qm import SimulationConfig
from configuration import *
import matplotlib.pyplot as plt
from qualang_tools.loops import from_array
from qualang_tools.results import fetching_tool, progress_counter
from macros import multiplexed_readout, qua_declaration
import warnings

warnings.filterwarnings("ignore")

###################
# The QUA program #
###################
n_avg = 20000

# The frequency sweep around the resonators' frequency "resonator_IF_q"
dfs = np.arange(-2e6, 2e6, 0.05e6)
# The readout amplitude sweep (as a pre-factor of the readout amplitude)
da = 0.01
amplitudes = np.arange(0, 1.9 + da / 2, da)  # The amplitude vector +da/2 to add a_max to the scan

mode = "a"
if mode=="a": var = amplitudes
else: var = dfs

with program() as ro_freq_opt:
    Ig, Ig_st, Qg, Qg_st, n, n_st = qua_declaration(nb_of_qubits=2)
    Ie, Ie_st, Qe, Qe_st, _, _ = qua_declaration(nb_of_qubits=2)
    df = declare(int)  # QUA variable for the readout frequency
    a = declare(fixed)  # QUA variable for the readout amplitude

    with for_(n, 0, n < n_avg, n + 1):

        if mode=="a": df = 0
        else: a = 0.5
        
        # with for_(*from_array(df, dfs)):
        with for_(*from_array(a, amplitudes)):
            
            # Update the frequency of the two resonator elements
            update_frequency("rr1", df + resonator_IF_q1)
            update_frequency("rr2", df + resonator_IF_q2)

            # Reset both qubits to ground
            wait(thermalization_time * u.ns)
            # Measure the ground IQ blobs
            multiplexed_readout(Ig, Ig_st, Qg, Qg_st, resonators=[1, 2], weights="rotated_", amplitude=a)

            align()
            # Reset both qubits to ground
            wait(thermalization_time * u.ns)
            # Measure the excited IQ blobs
            play("x180", "q1_xy")
            play("x180", "q2_xy")
            align()
            multiplexed_readout(Ie, Ie_st, Qe, Qe_st, resonators=[1, 2], weights="rotated_", amplitude=a)
        # Save the averaging iteration to get the progress bar
        save(n, n_st)
    
    with stream_processing():
        n_st.save("iteration")
        for i in range(2):
            # mean values
            Ig_st[i].buffer(len(var)).average().save(f"Ig{i+1}_avg")
            Qg_st[i].buffer(len(var)).average().save(f"Qg{i+1}_avg")
            Ie_st[i].buffer(len(var)).average().save(f"Ie{i+1}_avg")
            Qe_st[i].buffer(len(var)).average().save(f"Qe{i+1}_avg")
            # variances to get the SNR
            (
                ((Ig_st[i].buffer(len(var)) * Ig_st[i].buffer(len(var))).average())
                - (Ig_st[i].buffer(len(var)).average() * Ig_st[i].buffer(len(var)).average())
            ).save(f"Ig{i+1}_var")
            (
                ((Qg_st[i].buffer(len(var)) * Qg_st[i].buffer(len(var))).average())
                - (Qg_st[i].buffer(len(var)).average() * Qg_st[i].buffer(len(var)).average())
            ).save(f"Qg{i+1}_var")
            (
                ((Ie_st[i].buffer(len(var)) * Ie_st[i].buffer(len(var))).average())
                - (Ie_st[i].buffer(len(var)).average() * Ie_st[i].buffer(len(var)).average())
            ).save(f"Ie{i+1}_var")
            (
                ((Qe_st[i].buffer(len(var)) * Qe_st[i].buffer(len(var))).average())
                - (Qe_st[i].buffer(len(var)).average() * Qe_st[i].buffer(len(var)).average())
            ).save(f"Qe{i+1}_var")

#####################################
#  Open Communication with the QOP  #
#####################################
qmm = QuantumMachinesManager(host=qop_ip, port=qop_port, cluster_name=cluster_name, octave=octave_config)

###########################
# Run or Simulate Program #
###########################

simulate = False

if simulate:
    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=10_000)  # In clock cycles = 4ns
    job = qmm.simulate(config, ro_freq_opt, simulation_config)
    job.get_simulated_samples().con1.plot()

else:
    # Open the quantum machine
    qm = qmm.open_qm(config)
    # Send the QUA program to the OPX, which compiles and executes it
    job = qm.execute(ro_freq_opt)
    # Get results from QUA program
    data_list = [
        "Ig1_avg",
        "Qg1_avg",
        "Ie1_avg",
        "Qe1_avg",
        "Ig1_var",
        "Qg1_var",
        "Ie1_var",
        "Qe1_var",
        "Ig2_avg",
        "Qg2_avg",
        "Ie2_avg",
        "Qe2_avg",
        "Ig2_var",
        "Qg2_var",
        "Ie2_var",
        "Qe2_var",
        "iteration",
    ]
    results = fetching_tool(job, data_list=data_list, mode="live")
    (
        Ig1_avg,
        Qg1_avg,
        Ie1_avg,
        Qe1_avg,
        Ig1_var,
        Qg1_var,
        Ie1_var,
        Qe1_var,
        Ig2_avg,
        Qg2_avg,
        Ie2_avg,
        Qe2_avg,
        Ig2_var,
        Qg2_var,
        Ie2_var,
        Qe2_var,
        iteration,
    ) = results.fetch_all()
    # Progress bar
    progress_counter(iteration, n_avg, start_time=results.get_start_time())
    # Derive the SNR
    Z1 = (Ie1_avg - Ig1_avg) + 1j * (Qe1_avg - Qg1_avg)
    Q1Zg = Ig1_avg +1j*Qg1_avg
    Q1Ze = Ie1_avg +1j*Qe1_avg

    A1g = np.abs(Q1Zg)
    A1e = np.abs(Q1Ze)
    P1g = np.angle(Q1Zg)
    P1e = np.angle(Q1Ze)

    var1 = (Ig1_var + Qg1_var + Ie1_var + Qe1_var) / 4
    SNR1 = ((np.abs(Z1)) ** 2) / (2 * var1)
    Z2 = (Ie2_avg - Ig2_avg) + 1j * (Qe2_avg - Qg2_avg)

    Q2Zg = Ig2_avg +1j*Qg2_avg
    Q2Ze = Ie2_avg +1j*Qe2_avg

    A2g = np.abs(Q2Zg)
    A2e = np.abs(Q2Ze)
    P2g = np.angle(Q2Zg)
    P2e = np.angle(Q2Ze)

    var2 = (Ig2_var + Qg2_var + Ie2_var + Qe2_var) / 4
    SNR2 = ((np.abs(Z2)) ** 2) / (2 * var2)
    
    if mode=="a": var = amplitudes
    else: var = dfs / u.MHz
    
    # Plot results
    plt.suptitle("Readout frequency optimization")
    plt.subplot(321)
    plt.cla()
    plt.plot(var, SNR1, ".-")
    plt.title(f"Qubit 1 around {resonator_IF_q1 / u.MHz} MHz")
    plt.xlabel("Readout frequency detuning [MHz]")
    plt.ylabel("SNR")
    plt.grid("on")
    plt.subplot(322)
    plt.cla()
    plt.plot(var, SNR2, ".-")
    plt.title(f"Qubit 2 around {resonator_IF_q2 / u.MHz} MHz")
    plt.xlabel("Readout frequency detuning [MHz]")
    plt.grid("on")
    plt.pause(0.1)
    print(f"The optimal readout frequency is {var[np.argmax(SNR1)] + resonator_IF_q1} Hz (SNR={max(SNR1)})")
    print(f"The optimal readout frequency is {var[np.argmax(SNR2)] + resonator_IF_q2} Hz (SNR={max(SNR2)})")
    
    plt.subplot(323)
    plt.cla()
    plt.plot(var, A1g, ".-")
    plt.plot(var, A1e, ".-")
    plt.title(f"Qubit 1 around {resonator_IF_q1 / u.MHz} MHz")
    plt.xlabel("Readout frequency detuning [MHz]")
    plt.ylabel("SNR")
    plt.grid("on")    

    plt.subplot(324)
    plt.cla()
    plt.plot(var, A2g, ".-")
    plt.plot(var, A2e, ".-")
    plt.title(f"Qubit 2 around {resonator_IF_q2 / u.MHz} MHz")
    plt.xlabel("Readout frequency detuning [MHz]")
    plt.ylabel("SNR")
    plt.grid("on")  

    plt.subplot(325)
    plt.cla()
    plt.plot(var, P1g, ".-")
    plt.plot(var, P1e, ".-")
    plt.title(f"Qubit 1 around {resonator_IF_q1 / u.MHz} MHz")
    plt.xlabel("Readout frequency detuning [MHz]")
    plt.ylabel("SNR")
    plt.grid("on")    

    plt.subplot(326)
    plt.cla()
    plt.plot(var, P2g, ".-")
    plt.plot(var, P2e, ".-")
    plt.title(f"Qubit 2 around {resonator_IF_q2 / u.MHz} MHz")
    plt.xlabel("Readout frequency detuning [MHz]")
    plt.ylabel("SNR")
    plt.grid("on")  

    plt.show()

    # Close the quantum machines at the end in order to put all flux biases to 0 so that the fridge doesn't heat-up
    qm.close()
