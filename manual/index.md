# Colberto documentation {#mainpage}
This page includes the documentation of the Colberto control software. Let's hope that it grows rapidly, such that new people can quickly join the developper team. 

# General Structure 
The general structure is based on the layout presented in [pyqt-framework](https://wiki.silvascience.org/en/home/software/pyqt-framework). A minimal working framework is available in [github](https://github.com/SilvaScience/colberto) and will constantly grow. 

The entry point is `src/main.py`, which builds `MainInterface` from `src/GUI/main_GUI.ui`. It calls `load_instruments()` (`src/drivers/Instruments.py`) to build the device dictionnary, instantiates `DataHandling` and the Beam Explorer, and connects every plot and measurement class. Devices live in `src/drivers`, computation in `src/compute`, measurement and calibration routines in `src/measurements`, plots and panels in `src/GUI`.

## Hardware and drivers

Colberto uses many devices to perform its duty. Below are pages dedicated to these pieces of hardware
- [Spatial light Modulator](slm_meadowlark.md)
- [Cameras, spectrometer and monochromator](camera_spectrometer.md)
- [Optidry 250 cryostat](Optidry250.md)

# Contributing

Before you start contributing, make sure you read through [our contribution guide](contributing.md)

# Data Handling 
General considerations for DataHandling (`src/DataHandling/DataHandling.py`):
We decided to use .hdf5 files for data storage. These files are hierarchical files that contain structures that can include groups, attributes and datasets. In the following, it is discussed how to assign them to the requirements of Colbert measurements. 
DataHandling has three main tasks: (1) It provides a large buffer of hardware parameters that can be accessed fast and at all times from both the measurement routines and the ParameterPlot. (2) It stores the experimental data and handles large data. (3) It stores and provides access to all calibration data. 
	Three kinds of data storage are thus required.
- 	Spectra with according hardware parameters. All actual measurements require spectra. 
- 	Global calibrations, in the `calibration` dictionnary, filled by `add_calibration((name,value))` either by loading calibrations or from MeasurementClasses. 
- 	Current status and calibration of beams on the SLM, in the `beams` dictionnary. See this page about [Beam management in Colberto](beam_management.md).
- 	 Saved parameters. 

**Spectra**: For easy access, spectra with parameters are saved as one data frame. Groups for several measurement conditions can be created, where each group should contain a dataset that looks like:  
|         | Meas1 | Meas2 | ... |
| ------- | --- | --- | ---|
| Parameter1 |  |     |    |
| Parameter2 |  |     |    |
| Spec idx1  |  |     |    |
| Spec idx1  |  |     |    |
| ...        |  |     |	   |

The corresponding x-axis is stored as the `xaxis` attribute of the `spectra` dataset, and the parameter names as the `parameter_keys` attribute of the `parameter` dataset. The type of measurement can also be stored as an attribute through `add_attribute((name,value))`. 

**Buffering**: parameters are kept in `deque` objects of 100 000 entries each. Every time more than 100 spectra have been acquired, `save_buffer()` hands the arrays to a `BufferWorker` running in its own thread, which appends them to a temporary HDF5 file (`C:\TEMP\temp.h5` by default) and clears the in-memory arrays. `save_data(filename, comments)` waits on the worker's completion event before copying that temporary file to a timestamped `.h5`, so a half-written file is never saved. Calibrations are written as attributes of that file, and comments alongside them.

**Backgrounds**: a background belongs to the detector it was taken on. `has_background` says whether a real background was ever measured or loaded; until then `subtract_background` subtracts nothing. Changing detector resizes the buffers and drops the background.

**Beams and calibrations on disk**: `save_calibration` / `load_calibration` in `main.py` serialise the beams (`Beam.beam_to_dict`) and the calibration dictionnary (`DataHandling.calibration_to_dict`) into their own HDF5 file, through the `HDF5Helper` class. Loading restores the beams, the calibrations, reloads the LUT file recorded in `calibration['LUT_FilePath']` and re-applies the spectral calibration.

- Communication: As MeasurementClasses perform calibrations based on the different classes, DataHandling is passed as an argument to MeasurementClass, such that it can access its spectra.

# Calibrations
In order to properly [manage beams](beam_management.md), [spatial](calibrations/spatial_calibration.md) and [temporal](calibrations/temporal_calibration.md) calibrations are required. The grayscale-to-phase response of the SLM is calibrated separately, see [LUT calibration](calibrations/lut_calibration.md).

# Measurements
The multidimensional coherent spectroscopy measurements and their phase cycling are described in [measurements](calibrations/measurement.md).
