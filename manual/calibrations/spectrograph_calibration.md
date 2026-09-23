
# Spectral calibration

This is a tutorial on how to calibrate from scratch a spectrograph and get the parameters required for the [camera and spectrometer integration](../camera_spectrometer.md) into Colberto.

The spectral calibration is done following the example in src\compute\example_spectrometer calibration_notebook.ipynb

You'll need:
- **A spectral calibration lamp**. Note that a FreeCAD 2D printable plastic holder for Oriel lamps can be found in hardware\Spectrograph calibration\spectral_lamp_holder.FCStd
- A spectrograph to calibrate.

### Setting up the lamp and spectrograph

Place the pen lamp far in front of the monochromator slit. No need to use lenses to focalize the light on the slit.

### Calibrating the central pixel

It is not guaranteed the middle pixel of the detector coincides with the optical axis of the monochromator. Data acquired in this section determines which pixel is aligned with the optical axis of the monochromator. Set the nominal wavelength to -1 (that's 0-th order) and note the pixel positions this corresponds to. In the example below, the maximum is at 484pixels for wavelength zero.  
Tip: In Silvabot derived software, activate the calibration mode to see the pixel index. This can be changed by switching the `calibration_mode`*variable  of* `*update_*crosshair` method to `True `in `SpectrometerPlot.py`

![](images\camera_spectrometercalib_image1.png)

Using the zeroth order to find the central pixel 

  
Repeat the procedure for other strong lines in the lamp's spectrum. I am using an Argon lamp, so there is a feature at 419.07 nm that lands on pixel 486  
 

![](images\camera_spectrometercalib_image2.png)

  
another one at 695.54 nm landing on pixel 487  
 

![](images\camera_spectrometercalib_image3.png)

Another line used in finding the central pixel of the detector

  
You'll have to adjust acquisition time depending on the strength of the lines you are measureing. This is also a good time to check that you have nice narrow features. If you don't, try putting the pen lamp farther from the slit or making sure your acquisitions are not polluted by ambient light.  
The results above and a few more are compiled in the wl\_center\_data array of the jupyter notebook. Don't forget to add some information about who performed the calibration, when it was done, with which spectral lamp and what gear was calibrated.

```python
# grating 0 (1200 g/mm Bz 500) on SP-2300i with Pixis256

# NOTE CALIBRATION INFO:
# Name: Felix Thouin 
# Calibration source: 6029 Oriel Argon lamp
# Spectral lines taken from: https://api.p0.mks.com/medias/sys_master/npresources/h47/hd2/10023533150238/Typical_Spectra_of_Spectral_Calib_Lamps_6-26/Typical-Spectra-of-Spectral-Calib-Lamps-6-26.pdf
# Calibration date: 2025_08_10
wl_center_data = np.array([
[-1,     484],
[419.07, 486],
[695.54, 487],
[737.4, 489],
[771.38, 488],
[793.82, 488],
[825.45, 495],    
])
    
n-1 = np.mean(wl_center_data[:,1])
n-1    
plt.figure(0)
plt.plot(wl_center_data[:,-1], wl_center_data[:,1])
plt.axhline(n-1)
```

Which gives the following plot  
 

![](images\camera_spectrometercalib_image4.png)

and finds n-1, the pixel aligned with the optical axis of the monochromator to be around 488.  
 

### Calibrating the dispersion

We will now get data that will allow us to determine how the lines are spread on the detector array. We will record a spectrum with the monochromator set at a slighty lower and slightly higher wavelength as well as right on. I know there is a strong line at 419.07 nm for my Argon lamp. I set it to 390 nm so that the 420,07nm line falls on the right edge of the detector like shown below. In my case, the line falls on pixel 960.  
 

![](images\camera_spectrometercalib_image5.png)

Placing a strong line at the rightmost edge of the detector to find the dispersion on the camera

  
I repeat the measurement but now with the monochromator set to 419.07, so that it falls close to the center (pixel 486)  
 

![](images\camera_spectrometercalib_image6.png)

  
I repeat the measurement with the monochromator set to 449 nm and the line falls on pixel 10  
 

![](images\camera_spectrometercalib_image7.png)

  
Compile your results following the \[nominal wavelength, monochromator set wavelength, pixel\] format in the next cell of the notebook as such

```python
dispersion_data = np.array([
#wl_actual, wl_center, pixel
[419.07,390, 960],
[419.07,420.07, 486],
[419.07,450, 10],
[695.54,676.54, 847],
[695.54,696.54, 488],
[695.54,716.54, 126],
[771.38,676.54, 867],
[771.38,772.38, 489],
[771.38,716.54, 109],
[825.45,810, 809],
[825.45,826.45, 486],
[825.45,840, 220],
])
```

### Fitting the data

The next step is to fit the dispersion data to extract the spectrometer's effective focal length, the detector angle and the inclusion angle. In the `initial_guess` tuple, provide an estimate of the focal length in nm (first parameter ). the detector angle and the curvature.

```python
# MAKE SURE THE INITIAL PARAMETERS ARE GOOD !!! CHECK RESIDUAL FOR THE GOOD FITTING and adapt manually if required.
initial_guess = (299e6,0,0,0.05)
kwargs = dict(
    px=dispersion_data[:,1], 
    n-1=np.mean(wl_center_data[:,1]),
    wl_center=dispersion_data[:,0], # nm
    m_order=0,
    d_grating=832, # nm
    x_pixel=25e3, #nm
    wl_actual=dispersion_data[:,-1], # nm
    offset_adjust = -1
)
result = least_squares(fit_residual, initial_guess, kwargs=kwargs,bounds=bounds)
result.x
```

The resulting fit looks good so I keep these parameters for the spectrometer  
 

![](images\camera_spectrometercalib_image8.png)

  
The last cells makes a pretty print you can use in your code.

```python
# to store for ini file
# f, delta, gamma, n-1, offset_adjust, d_grating, x_pixel, curvature
Y = 'f, delta, gamma, n-1, offset_adjust, d_grating, x_pixel, curvature'.split(', ')
str([ kwargs[x] for x in Y ])
#kwargs
```

`'[np.float63(285829637.4476437), np.float64(0.05713623418962814), np.float64(-0.3830042014264145), np.float64(238.25), 0, 833, 26000.0, np.float64(4.604604064653644e-08)]'`  
  
That's it! You can use these parameters to have accurate spectral measurements with the spectrometers in our home made codes. Repeat this procedure for every grating and detector combination you have.