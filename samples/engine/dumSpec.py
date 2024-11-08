import numpy as np
from time import sleep

class dumSpec1000:
    def __init__(self,intTime=10e-3):
        self.intTime=intTime
        self.pixnum=1024
    
    def set_integration_time(self,t):
        self.intTime=t
    
    def get_integration_time(self):
        return self.intTime

    def get_spectrum(self):
        sleep(self.get_integration_time())
        wave=np.linspace(500,750,1024)
        signal=np.exp(-(wave-625)**2/100)+np.random.rand(*wave.shape)/np.sqrt(self.intTime/0.01)
        return  wave.tolist(), signal.tolist()

if __name__ == "__main__":  # pragma: no cover
    from matplotlib import pyplot as plt
    spec=dumSpec1000()
    spec.set_integration_time(0.01)
    print(spec.intTime)
    plt.figure()
    for i in range(5):
        wave,signal=spec.get_spectrum()
        plt.plot(wave,signal)
        print(i)
    plt.show()