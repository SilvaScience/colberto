# Measurements

Some details about the measurement tab in the software. 

## Measurement type

The measurement code is located in `MDCSClasses.py`, in the `BoxcarGeometry` class. Other geometries could be implemented in a new class. The local oscillator spectrum is acquired separately by the `AcquireLO` class in the same module.

There are five entries in the measurement type box: 0Q, 1Q-Rephasing, 1Q-Non rephasing, 2Q and LO scan. The beam time ordering is different for each type. The LO beam will come to the sample at t_LO before the last interaction. t_LO could be negative so the LO beam will be the last. Note that the conjugate beam to the LO is the A beam. The following explains the timing between pulses for the different types starting at time t = 0:

    - 0Q:               A(0),       C(t_secondary),     LO(t_scanned-t_LO),                 B(t_scanned)
    - 1Q rephasing:     A(0),       C(t_scanned),       LO(t_scanned+t_secondary-t_LO),     B(t_scanned+t_secondary)
    - 1Q non rephasing: C(0),       A(t_scanned),       LO(t_scanned+t_secondary-t_LO),     B(t_scanned+t_secondary)
    - 2Q:               C(0),       B(t_secondary),     LO(t_scanned+t_secondary-t_LO),     A(t_scanned+t_secondary)
    - LO scan:          A(0),       B(0),               C(0),                               LO(t_scanned)

The group delays built from this table are all multiplied by -1 before being applied, so that a positive delay in the interface means the pulse arrives later.

Before the first measurement, the LO spectrum must be acquired by clicking on the `Get LO` button. This is for the quick Fourier transform after the measurement. Then the measurement can be performed by clicking on `Acquire`.

Two checkboxes sit next to the measurement type box: demo mode, which replays saved data instead of touching the hardware, and phase cycling, which can be turned off to take a single shot per delay step instead of the 16 of the cycling procedure.

When the measurement is initiated, the code runs over two loops, the t_secondary and t_scanned values. For every t_secondary, timing vectors are created. They depend on the measurement type. Then, for every t_scanned the phase cycling is performed (see the next section for details). For each cycling step, the phase of each beam is set with `set_currentPhase` in relative mode with coefficients `[CEP, group delay]` in fs, the gratings of all beams are summed into one image sent to the SLM, and an acquisition is done and stored in a list. The 16 measurements are summed together following the `operations` vector written below at the end of the phase cycling procedure. For every t_scanned, the outcome intensity of the phase cycling is saved.

## Phase cycling

For every t_scanned measurement, 16 single shots are taken with different phases for the four beams. By summing them with the use of the operation vector we obtain the desired FWM contribution only, where the phasor contains the four beam phases. When the phase cycling checkbox is unchecked, `operations` reduces to `np.array([1])` and a single spectrum is taken.

        self.cep = {
            'A':  np.array([0, 0, 0, 0, np.pi, np.pi, np.pi, np.pi, 0, 0, 0, 0, np.pi, np.pi, np.pi, np.pi]),
            'B':  np.array([0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi]),
            'C':  np.array([0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi]),
            'LO': np.array([0, np.pi, np.pi, 0, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, 0, np.pi, np.pi, 0])
        }

        operations = np.array([1, -1, -1, 1, -1, 1, 1, -1, 1, -1, -1, 1, -1, 1, 1, -1])
