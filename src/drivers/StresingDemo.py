"""
Created on Fri Feb 07 15:26:53 2025

@author: Simon Daneau
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

"""
"""TO DOS:
- Connect the camera with the PC. Try the different functionalities and choose the relevant one.
- Define these functions in the worker.
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time

class StresingDemo(QtCore.QThread):

    name = 'Stresing Demo'

    def __init__(self):
        super(StresingDemo, self).__init__()

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['ac_time']['val'] = 500
        self.parameter_display_dict['ac_time']['unit'] = ' ms'
        self.parameter_display_dict['ac_time']['max'] = 10000
        self.parameter_display_dict['ac_time']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # initialize Worker
        self.worker = StresingWorker()
        self.worker.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        self.worker.start()

        # preallocate arrays
        self.spectrum = np.ndarray([])

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'ac_time':
            self.parameter_dict['ac_time'] = value
            self.worker.set_int_time(value)
            self.int_time = value
            self.new_spectrum = False

    def update_spectrum(self, spectrum):
        self.spectrum = spectrum

class StresingWorker(QtCore.QThread):
    """ This is a DemoWorker for the Stresing Camera.
    It continously acquires spectra and emits them to the Interface.
    It interrupts data acquisition if an ac_time change is requested. Its important because most
    hardware can only handle one command at a time, acquiring or changing settings.  """
    # These are signals that allow to send data from a child thread to the parent hierarchy.
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)

    def __init__(self):
        super(StresingWorker, self).__init__() # Elevates this thread to be independent.

        # definition of some parameters
        self.spec_length = 1024
        self.spectrum = np.zeros(self.spec_length)
        self.int_time = 0

    def run(self):
        """" Continuous tasks of the Worker are defined here.
        If loops check for requested changes in settings prior each acquisition. """
        while not self.terminate: #infinite loop
            if not self.change_int_time:
                self.spectrum = self.getIntensities()
                if not self.change_int_time:
                    self.sendSpectrum.emit(self.spectrum)
            else:
                self.change_int_time = False
                self.int_time = self.updated_int_time
                # Here needs to go a command that changes the int time at the spectrometer.
                #print(time.strftime('%H:%M:%S') + ' PL Spectrum acquired')
        return

    def getIntensities(self):
        # create random spectrum. Some varying random signal helps to check functionality.
        t1 = time.time()
        wls = np.linspace(177.2218, 884.00732139, 2048)
        sigma = 40
        mu = 2
        xc = 620.
        spec = (0.8+0.2*np.random.rand(1))*(np.random.randint(0, 50, 2048) + self.int_time*2000. / (sigma * np.sqrt(2. * np.pi)) * np.exp(
            - (wls - mu - xc) ** 2. / (2. * sigma ** 2.)) - 50),
        flatspec = np.array(spec)
        time.sleep(self.int_time/1000)
        if time.time()-t1 >0.1:
            time.sleep(0.1)
        return flatspec.reshape(-1)

    def set_int_time(self, int_time):
        self.int_time = int_time
