# Architecture and Coherence Characteristics of Superconducting Transmon Qubits

## 1. Physical Architecture and Fabrication
The multi-qubit processor features a 2D planar array of fixed-frequency and tunable transmon qubits fabricated on a high-resistivity silicon substrate (>10 kΩ·cm). Each superconducting transmon qubit comprises a planar interdigitated capacitor shunted by two sub-micron Al/AlOx/Al Josephson junctions configured in an asymmetric DC-SQUID loop.

The charging energy $E_C$ is engineered to approximately 210 MHz, while the Josephson coupling energy $E_J$ is maintained at approximately 15.5 GHz, yielding an $E_J/E_C$ ratio of ~74. This ratio places the circuit firmly in the transmon regime, exponentially suppressing charge-noise dispersion to less than 1.8 kHz while preserving sufficient negative anharmonicity ($\alpha \approx -230\text{ MHz}$) to prevent unintended leakage into higher excitation states during microwave drive pulses.

## 2. Cryogenic Environment and Thermal Stages
The processor is housed within an Oxford Instruments Proteox dilution refrigerator operating with a closed-cycle helium-3/helium-4 dilution loop. To maintain quantum coherence and suppress thermal photon excitations:
- **Room Temperature Stage (300 K)**: Microwave signal synthesis, pulse shaping, arbitrary waveform generators (AWGs), and FPGA readout logic.
- **50 K Thermal Flange**: First-stage attenuation and high-frequency thermal heat sinking.
- **4 K Flange**: Equipped with low-noise HEMT (High Electron Mobility Transistor) cryogenic amplifiers providing +38 dB gain across 4.0–8.0 GHz with a noise temperature of 2.1 K.
- **Still Stage (800 mK)**: Vaporization of the helium-3 phase.
- **Cold Plate (100 mK)**: Additional 20 dB microwave attenuators to thermalize coaxial drive lines.
- **Mixing Chamber Base Stage (15 mK)**: Base operating temperature of 14.8 mK. The sample package is shielded against stray electromagnetic fields using nested Cryoperm-10 magnetic shields and an inner superconducting aluminum canister coated with a carbon-black epoxy absorbing layer.

## 3. Coherence Benchmarks
Across the calibrated 16-qubit lattice:
- **Longitudinal Relaxation Time ($T_1$)**: Average $T_1$ is measured at $124.5\,\mu\text{s} \pm 11.2\,\mu\text{s}$, with peak individual qubit $T_1$ exceeding $148\,\mu\text{s}$.
- **Transverse Pure Dephasing Time ($T_2^*$)**: Ramsey fringe measurements indicate an average $T_2^*$ of $94.8\,\mu\text{s}$.
- **Hahn Echo Dephasing Time ($T_{2,\text{echo}}$)**: Dynamic decoupling using single Hahn echo pulses extends dephasing times to $136.2\,\mu\text{s}$.
- **Readout Resonator Frequencies**: Individual quarter-wavelength coplanar waveguide (CPW) readout resonators are multiplexed onto a common feedline, spanning frequencies between 6.450 GHz and 7.120 GHz with internal quality factors $Q_{int} \approx 1.8 \times 10^6$.
