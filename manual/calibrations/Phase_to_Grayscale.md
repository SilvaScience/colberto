### SLM Calibration 

There are two steps needed to complete the phase to grayscale SLM Calibration. This is a basic calibration required of any SLM, to determine of the phase change imparted by each greyscale value setting.

## Measurement for Calibration

In order to create this phase to grayscale conversion, we followed the measurement outlined by Nelson, et al., which can be found [here](https://pubs.aip.org/aip/rsi/article/82/8/081301/354291/Invited-Article-The-coherent-optical-laser-beam). 

The optical setup for this calibration procedure is depicted in Fig. 7(a). It involves vertically splitting the SLM into two regions, where one side remains at a graysclae value of zero whilte the grayscale value of the other side will be varied. A cylindrical lens focuses the two first-order diffractions from a phase mask onto the plane of the SLM surface. The reflections from the SLM are recombined at the phase mask and reflected by a beamsplitter to a spectrometer.

To perform this measurement, go to the utilities tab of the main interface, and click the **Measure Spectrum - Phase2Gray Calibration** button. This will display a pattern on the SLM, where one half is set to a grayscale value of zero and the other hald of the SLM scans through the grayscale values (0-255). A spectrum is recorded after each pattern is displayed.  

## Analysis for Calibration 

This calibration is not performed regularly, so the analysis of the measurement is not currently integrated in the GUI. 

To generate the phase2gray normalization coefficients file locate `/samples/compute/Phase2Grey_Anlaysis`.

The Data_Files folder has the spectral data acquired from the measurement described above. These are the files we will analyze using `Unwrap_Phase.py`. 

The code does the following:
1. Loads the data
2. Plots the data in two ways: wavelength vs intensity for each grayscale value & grayscale vs intensity for each wavelength
3. For a single wavelength:
  - plots intensity vs grayscale
  - intensity vs grayscale (with peaks & troughs designated on the plot)
  - Wrapped phase obtained through ArcCos (raw & smoothed phase)
  - Unwrapped phase fit a fifth order polynomial
4. The plots above display the phase unwrapping method followed for one wavelength. The next art of the code has a loop that will complete phase unwrapping for all wavelengths. The plots feature can be turned on or off usinghte do_plots input (True or False)
5. Finally, an csv file with the wavelengths and corresponding coefficients for a fifth-order polynomial is saved
