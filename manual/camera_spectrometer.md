# Camera and spectrometer
Colbert can be used with many different spectrometers and detectors to ensure maximal flexibility when calibrating or acquiring data. This page describes how these are handled, calibrated and used.


## Software implementation
Devices are managed in the intruments.py where you can add or removed devices by adding an entry in the `devices` dict. Spectrometers are no exception.

Monochromators are first instantiated by providing hardware parameters and the communication port to be used. The hardware parameters include those from calibrations as well as useful information about the gratings mounted inside the spectrometer such as it blaze angle. Here is a typical parameter dict to be passed to a monochromator such as the SP2300.
```
  gratings_params_pixis ={ 
            '1':{
                'focal_length_mm':300,
                'f':np.float64(300000000.0),
                'delta':np.float64(0.5),
                'gamma':np.float64(0.1),
                'n0':np.float64(480.14285714285717), # Central pixel
                'offset_adjust':0,
                'd_grating':833.3333333333334,
                'x_pixel':26000,
                'curvature':np.float64(0.0),
                'blaze':np.float64(300),
                },
            '2':{
                'focal_length_mm':300,
                'f':np.float64(300000000.0),
                'delta':np.float64(0.5),
                'gamma':np.float64(0.1),
                'n0':np.float64(480.14285714285717), # Central pixel
                'offset_adjust':0,
                'd_grating':833.3333333333334,
                'x_pixel':26000,
                'curvature':np.float64(0.0),
                'blaze':np.float64(750),
                },
            '3':{
                'focal_length_mm':300,
                'f':np.float64(300000000.0),
                'delta': np.float64(0.05),
                'gamma':np.float64(0.01),
                'n0':np.float64(478.2), # Central pixel
                'offset_adjust':0,
                'd_grating': 3333.333333333333,
                'x_pixel':26000,
                'curvature':np.float64(0.0),
                'blaze':np.float64(2000),
                },
            }
```
The top level key refers to the monochromator's gratings. Be careful to use the same keys as those obtained from the calls to the spectrograph's  `get_grating_indices()` method. All parameters from the lower levels except `focal_length_mm` and `blaze` are obtained from fitting as described in the [calibration section](#calibration).

Cameras are also initiated in the same way with dictionnaries specific to each device. All cameras need to be connected to a spectrometer by calling the `attach_monochromator()` method of the camera. This will import the parameters of the monochromator inside the camera and turn it into a spectrograph. Cameras will then generated wavelength arrays with calls to their `get_wavelength()` method in addition to recorded light intensities. The `get_wavelength()` calls the monochromator calibration dict and associates it with the camera and grating combinasion currently in use.

## Calibration

Calibrations are done following a standard procedure using the Jupyter notebook found in `/src/compute/example_spectrometer calibration_notebook.ipynb`. If it is the first time you are calibrating the spectrometer or are unsure how to use the notebook, refer to [our introductory tutorial](calibrations/spectrograph_calibration.mb).
