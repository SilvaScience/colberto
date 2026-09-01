# Temporal Calibrations

Performing Colbert measurements require accurate characterisation of the every pulse. This is done through temporal calibrations namely compression using chirp scan and delay scan

## Chirp scan

Chirp scans can be performed from the Chirp Scan panel in the Chirp Calibration Tab.

1. TO PERFORM CHIRP SCAN, THE STRESING CAMERA MUST BE IN CONTINUOUS MODE. To do so, you change the value of Block_trig and Scan_trig to 4 (on the left on the photo, 0 is for trig mode). Otherwise, you won't measure anything. Also, the No_sample can be reduced to <10 (>2) to avoid measuring many times. Finally, the Scan_timer (integration time) is adjusted to something like 20 000. Unit is in microsecond. Comments:

- Without DOE (only one beam with higher intensity), Scan_timer = 20 000 gives a good chirp scan. 
- Whit DOE (only one of the four beams), Scan_timer = 50 000 seems ok. 

2. The first thing you have to do is take the background by simply block the laser from Colbert, i.e. you do have to block the ambient light in front of the monochromator. By clicking on `Background`, the background will be saved in Data_Handling. 

3. Secondly, you must enter the needed informations in the measurement block, i.e. carrier wavelength, beam name and the GDD interval parameters. YOU ALSO HAVE TO ADD THE SHG BANDPASS FILTER IN FRONT OF THE MONOCHROMATOR.

4. Then you can click on `acquire`. If demo mode is selected, it will take old saved data. Otherwise, the program will perform the chirp scan and show you the result on the top right figure. The background saved data will be subtracted from every scan step.  The last chirp scan raw data is saved in the Datahandling under 'chirp_calibration_raw_data_beam_XXX' where XXXX is the beam's name.

5. Once the measurement is done, you may want to try to fit a polynomial function on the SHG region of interest. To do so, in the fitting block, the user may choose a wavelength bandwidth and an SNR threshold. By clicking on Apply SNR threshold, the bottom left figure will be adjusted and will show the desired region with nonzero signal where the SNR is big enough. 

6. To perform the fit, you have to choose the polynomial order between 1 to 10. Then by clicking on `Fit chirp scan` the program will find the maximum chirp value for each wavelength and do the polynomial fitting. The output bottom right graph will show the data and the fit. The outputs coefficients will be printed in the bottom text box. If the fit isn't right, you can try with a different polynomial order. The last fit data (frequency relative to carrier, key 'omega_shifted_fs', maximal chirp values in key 'max_chirp_values', fitted polynomial coefficients in key 'polynomial_coeffs' and phase derivative coefficients in key 'phase_derivative_coeffs') are all saved in a dict in Datahandling under the key 'temporal_calibration_processed_fit_beam_XXX' where XXXX is the beam's name

7. Once the fit is good, the coefficients seems ok, than you can click on `assign calibration` to assign the coefficients to the selected beam name. 

## Delay scan

Delay scans can be performed from the Delay Scan panel in the Delay Calibration Tab.

1. To perform delay scan, the camera can be in triggering mode. To do so, you change the value of Block_trig and Scan_trig to 0.

2. The first thing you have to do is take the background by simply block the laser from Colbert (facultative), i.e. you do have to block the ambient light in front of the monochromator. By clicking on `Background`, the SLM will be closed and the background will be saved in Data_Handling. 

3. Secondly, you must enter the needed informations in the measurement block, i.e. the reference beam name (usually LO) and the second beam name. Also the delay carrier wavelength must be set to something close to the laser bandwidth (just outside of the spectral band). The group delay parameters are set to clearly see the XFROG trace with enough resolution. Bigger steps in the begening and than smaller steps to define the time zero.  

4. An iris selecting the ONLY the cross correlation SHG is needded for an accurate measure of the beams duration. Then you can click on `Acquire`. If demo mode is selected, it will take old saved data. Otherwise, the program will perform the delay scan and show you the result on the top right figure. The background saved data will be subtracted from every scan step. 

5. Once the measurement is done, you may want to try to fit a gaussian curve on the SHG region of interest. To do so, in the fitting block, the user may choose a wavelength bandwidth and an SNR threshold. By clicking on Apply SNR threshold, the bottom left figure will be adjusted and will show the desired region with nonzero signal where the SNR is big enough. 

6. To perform the fit, you have to click on `Fit delay`. The program will fit the gaussian function on the data. The FWHM will be printed on the figure panel. The program will also saved the XFROG scan with both beams name in the filename.  

7. Once the fit is good, the coefficients seems ok, than you can click on `Apply delay` to assign the coefficients to the second beam name. You can also removed the delay by cliking on `Remove delay`.