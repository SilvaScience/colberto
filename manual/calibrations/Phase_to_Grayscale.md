### SLM Calibration 

There are two steps needed to complete the phase to grayscale SLM Calibration. 
The phase to grayscale calibration is necessary before one can utilize the full capabilities of the SLM. The SLM displays phase patterns in terms of grayscale values (0-255), but for COLBERT we are interested in the phase properties, so we need to determine the conversion between them. 

## Measurement for Calibration

In order to create this conversion, we followed the measurement outlined by Nelson, et al., which can be found [here](https://pubs.aip.org/aip/rsi/article/82/8/081301/354291/Invited-Article-The-coherent-optical-laser-beam)

The SLM Calibration is located in the utilities tab of the main interface.
To calibrate the SLM for various wavelengths, one needs to create a Phase to Grayscale LUT file. 
This is done in two steps:
1. Measure_LUT_PhasetoGreyscale: Displays a pattern on the SLM where half of the SLM is set to a grayscale value of zero, and the other half of the SLM scans through the grayscale values (0-255). The spectrum of the beam is taken after each pattern. 
2. Generate_LUT_PhasetoGreyscale: Analyzes the measured spectrum to determine the phase shift from the reference (where both sides of the SLM are at a greyscale value of zero). This is done by taking a Fourier transform of the spectrum and calculating the phase difference using the real and imaginary components. 


# Phase to Grayscale Calibration for each Wavelength

 

## Vertical calibration

The vertical location of beams on the SLM is measured by gradually turning on a phase grating from the top to the bottom of the SLM and measuring the amount of diffracted light using the spectrometer. This gives a characteristic S-curve for each beam incident on the SLM.

This measurement is performed when pressing the `vertical_calibration_runButton` using the `VerticalBeamCalibrationMeasurement`
