# Colberto documentation {#mainpage}
This page includes the documentation of the Colberto controll software. Let's hope that it grows rapidly, such that new people can quickly join the developper team. 

# General Structure 
The general structure is based on the layout presented in [pyqt-framework](https://wiki.silvascience.org/en/home/software/pyqt-framework). A minimal working framework is available in [github](https://github.com/SilvaScience/colberto) and will constantly grow. 

# Contributing

Before you start contributing, make sure you read through [our contribution guide](contributing.md)

# Data Handling 
General considerations for DataHandling:
We decided to use .hdf5 files for data storage. These files are hierarchical files that contain structures that can include groups, attributes and datasets. In the following, it is discussed how to assign them to the requirements of Colbert measurements. 
DataHandling will have three main tasks: (1) It has to provide a large buffer of hardware parameters that have to be able to be accessed fast and at all times from both the measurement routines and the ParameterPlot. (2) It needs to store the experimental data and be able to handle large data. (3) It needs to store and provide access to all calibration data. 
	Three kinds of data storage is thus required.
- 	Spectra with according hardware parameters. All actual measurements require spectra. 
- 	Global calibrations. Contains a data structure that can be filled either by loading calibrations or by filling them from MeasurementClasses. Should autosave after each calibration. 
- 	 Saved parameters. 

**Spectra**: For easy access, spectra with parameters should be saved as one data frame. Groups for several measurement conditions can be created, where each group should contain a dataset that looks like:  
|         | Meas1 | Meas2 | ... |
| ------- | --- | --- | ---|
| Parameter1 |  |     |    |
| Parameter2 |  |     |    |
| Spec idx1  |  |     |    |
| Spec idx1  |  |     |    |
| ...        |  |     |	   |

The corresponding x-axis should be stored as an attribute. Also, the type of measurement can be stored as attribute. 

**Calibrations**: Since we want to be able to load them independently, we should store them independent .hdf5 files. Each individual calibration should be a separate group with its own data and attributes. 

**Parameters**: Should be saved as one big .hdf5 file that contains one dataset. Different attributes can be 

- Communication: As MeasurementClasses will perform calibrations based on the different classes, pass DataHandling as argument to MeasurementClass, such that it can access its spectra. 

