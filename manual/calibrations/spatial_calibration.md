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