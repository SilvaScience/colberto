# Spatial calibrations

Two spatial calibrations are required before temporal calibration can occur in Colberto

## Vertical calibration

The vertical location of beams on the SLM is measured by gradually turning on a phase grating from the top to the bottom of the SLM and measuring the amount of diffracted light using the spectrometer. This gives a characteristic S-curve for each beam incident on the SLM.

This measurement is performed when pressing the `vertical_calibration_runButton` using the `VerticalBeamCalibrationMeasurement` class in the `CalibrationClasses` module.
It requires knowing the SLM's height and width (provided by the SLM driver) and the period of the phase grating (provided in GUI).
It also requires the increment of rows to use in the measurement. This is used to trade-off between measurement time and resolution.
If a demo SLM is provided, it returns a fake calibration curve.
The calibration curve is saved in the `calibration` dictionnary when the measurement is complete.

The result of the calibration is plotted in live in the `self.VerticalCalibPlot` instantiation of a `VerticalCalibPlot`.

Once the measurement is performed, the user inputs the boundaries of each beams delimiting each S-curve in the `beam_vertical_delimiters_table`. Every time the cell is modified, the location of the boundary is updated on `VerticalCalibPlot`. The validity of each input is checked before updating the cell value.

The grating period and beam vertical location for each complete row is saved in the `DataHandling.beams` dictionnary when pressing the `assign_beams_vertical_delimiters_button` button. These parameters cannot be changed in any other way.

It also creates a new beam called `ALL` which vertically spans the whole SLM.

## Spectral calibration

The spectral calibration of the SLM is performed by sweeping a vertical grating stripe across the SLM and measuring the peak of the spectrum at each step.

This measurement is performed by pressing the `measure_spectral_calibration` button after specifying the width of the stripe in `column_width_spin_box` and the increment by which to step its location in `column_increment_spin_box`. The measurements are updated in the `spectral_calib_plot_layout` where a `SpectralCalibDataPlot` is instantiated. The measurements are also stored in DataHandling under `calibration['spectral_calibration_raw_data']`.

As the data is acquired the maximum for every strip position is plotted in `spectral_calib_fit_plot_layout` where a `SpectralCalibFitPlot` is instantiated.Processed data is stored in DataHandling under `calibration['spectral_calibration_processed_data']`.

The range of wavelengths to be considered by the spectral calibration can be adjusted in the `shortest_fitting_wave_spin_box` and `longest_fitting_wave_spin_box` and instantly updates the analysis. This will also restrain the beam on the SLM, always turning off the columns outside this range.

Clicking the `fit_spectral_calibration_button` performs a polynomial fit, plots the fit on top of the data and the residual in `spectral_calib_fit_residual_plot_layout`. The latter is jointly initiated with the `SpectralCalibFitPlot`. 

Clicking on `assign_spectral_calibration_button` updates the `pixelToWavelength` attribute of all beams in DataHandling with the most recent fit. If no beams are found, a new beam named `ALL` vertically spanning the whole SLM is created.

