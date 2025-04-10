import numpy as np
from time import sleep

class dumSpec1000:
    def __init__(self,integration_time=10e-3):
        self.integration_time=integration_time
        self.pixnum=1024
    
    def set_integration_time(self,t):
        self.integration_time=t
    
    def get_integration_time(self):
        return self.integration_time

    def get_wave(self):
        wave=np.linspace(500,750,1024)
        return wave

    def get_spectrum(self):
        sleep(self.get_integration_time())
        wave=self.get_wave()
        signal=np.exp(-(wave-625)**2/100)+np.random.rand(*wave.shape)/np.sqrt(self.integration_time/0.01)
        return  signal

if __name__ == "__main__":  # pragma: no cover
    from matplotlib import pyplot as plt
    spec=dumSpec1000()
    spec.set_integration_time(0.01)
    print(spec.integration_time)
    plt.figure()
    wave=spec.get_wave()
    for i in range(5):
        signal=spec.get_spectrum()
        plt.plot(wave,signal)
        print(i)
    plt.show()