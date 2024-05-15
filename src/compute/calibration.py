# This module define a calibration class. 
# This class hosts functions, methods and attributes related to Colbert calibrations

import numpy as np

class Calibration():

    def __init__(self,SLM):
        """
        This builds an instance of a Calibration object without loading a file.
        Input:
            SLM: an SLM object

        """
        self.SLM=SLM # SLM Hosts all parameters related to the SLM currently in use
        self.wavelengthToPixels=None
        self.phaseToGrayscale=None


        