# Measurements

Some details about the measurement tab in the software. 

## Measurement type

There are four measurement types: 0Q, 1Q-Rephasing, 1Q-Non rephasing and 2Q. The beam time ordering is different for all four types. The LO beam will come to the sample at t_LO before the last interaction. t_LO could be negative so LO beam will be the last. 

## Phase cycling

For every t_scanned measurement, 16 single shots is taken with different phases for the four beams. By summing them with the use of the operation vector we obtain the desired FWM contribution only where the phasor contains the four beam phases.    

        self.cep = {
            'A':  np.array([0, 0, 0, 0, np.pi, np.pi, np.pi, np.pi, 0, 0, 0, 0, np.pi, np.pi, np.pi, np.pi]),
            'B':  np.array([0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi]),
            'C':  np.array([0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi]),
            'LO': np.array([0, np.pi, np.pi, 0, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, 0, np.pi, np.pi, 0])
        }

        operations = np.array([1, -1, -1, 1, -1, 1, 1, -1, 1, -1, -1, 1, -1, 1, 1, -1])