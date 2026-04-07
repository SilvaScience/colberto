# Measurements

Some details about the measurement tab in the software. 

## Measurement type

The measurement code is located in the `MDCSClasses.py` in the  `BoxcarGeometry` class. Other geometries could be implemented in a new class. 

There are four measurement types: 0Q, 1Q-Rephasing, 1Q-Non rephasing and 2Q. The beam time ordering is different for all four types. The LO beam will come to the sample at t_LO before the last interaction. t_LO could be negative so LO beam will be the last. Note that the conjugate beam to the LO is the A beam. The folowing explain the timing between pulses for the different types starting at time t = 0:

    - 0Q:               A(0),       C(t_secondary),     LO(t_scanned-t_LO),                 B(t_scanned)
    - 1Q rephasing:     A(0),       C(t_scanned),       LO(t_scanned+t_secondary-t_LO),     B(t_scanned+t_secondary)
    - 1Q non rephasing: C(0),       A(t_scanned),       LO(t_scanned+t_secondary-t_LO),     B(t_scanned+t_secondary)
    - 2Q:               C(0),       B(t_secondary),     LO(t_scanned+t_secondary-t_LO),     A(t_scanned+t_secondary)

Before the first measurment, the LO spectrum must be acquire by cliking on `Get LO` button. This is for the quick Fourier transform after the measurment. Then the measurement can be perform by cliking on `Acquire`

When the measurement is initiated, the code is running over two loops, the t_secondary and t_scanned values. For every t_secondary, timming vectors are created. They depends on the meaasurement type. Then, for every t_scanned the phase cycling is performed (see the next section for details). For each cycling steps, a acquisition is done and stored in a list. The 16 measurements are summed together following the `operations` vector written below at the end of the phase cycling procedure. For every t_scanned, the outcome intensity of the phase cycling is saved.

## Phase cycling

For every t_scanned measurement, 16 single shots is taken with different phases for the four beams. By summing them with the use of the operation vector we obtain the desired FWM contribution only where the phasor contains the four beam phases.    

        self.cep = {
            'A':  np.array([0, 0, 0, 0, np.pi, np.pi, np.pi, np.pi, 0, 0, 0, 0, np.pi, np.pi, np.pi, np.pi]),
            'B':  np.array([0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi]),
            'C':  np.array([0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi]),
            'LO': np.array([0, np.pi, np.pi, 0, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, 0, np.pi, np.pi, 0])
        }

        operations = np.array([1, -1, -1, 1, -1, 1, 1, -1, 1, -1, -1, 1, -1, 1, 1, -1])