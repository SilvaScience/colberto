# Camera and spectrometer

Colbert can be used with two cameras (Stresing and Pixis) plugged to one spoectrometer. Everything is managed in the intruments.py where you can add or removed devices. The spectrometer is the main device where the cameras could be attached, meaning that all camera parameters are child of the parent spectrometer. Those parameters are all saved and managed through Data Handling. 

On the main panel, on the top right, you can find a sliding menu where there is a list of the connected cameras. Selecting another camera reset completely Data Handling beacause the number of parameter is changing between cameras and also the length of the sensor may be different. For those reasons, it is easier to reset. All the other calibrations that were not associated with the camera will be loaded back. However, the connection between the beam explorer and Data Handling seems to be lost. 

## Calibration

Calibrations are done following a standard procedure using the Jupyter notebook found in `/src/compute/example_spectrometer calibration_notebook.ipynb`. If it is the first time you are calibrating the spectrometer or are unsure how to use the notebook, refer to [our introductory tutorial](calibrations/spectrograph_calibration.mb).
