# Temporal Calibrations

Performing Colbert measurements require accurate characterisation of the every pulse. This is done through temporal calibrations namely compression using chirp scan and XXXXXX

## Chirp scan
Chirp scans can be performed from the Chirp Scan panel in the Temporal Calibration Tab.

These are implemented by the ChirpAcquireBackground, 

TO PERFORM CHIRP SCAN, THE STRESING CAMERA MUST BE IN CONTINUOUS MODE. To do so, you change the value of Block_trig and Scan_trig to 4 (on the left on the photo, 0 is for trig mode). Otherwise, you won't measure anything. Also, the No_sample can be reduced to <10 (>2) to avoid measuring many times. Finally, the Scan_timer (integration time) is adjusted to something like 20 000. Unit is in microsecond. Comments:

- Without DOE (only one beam with higher intensity), Scan_timer = 20 000 gives a good chirp scan. 
- Whit DOE (only one of the four beams), Scan_timer = 50 000 seems ok. 

2. The first thing you have to do is take the background by simply block the laser from Colbert, i.e. you do have to block the ambient light in front of the monochromator. By clicking on Background, the background will be saved in Data_Handling. 
3. Secondly, you must enter the needed informations in the measurement block, i.e. carrier wavelength, beam number and the chirp scan parameters. YOU ALSO HAVE TO ADD THE SHG BANDPASS FILTER IN FRONT OF THE MONOCHROMATOR. 
5. Then you can click on acquire. If demo mode is selected, it will take old saved data. Otherwise, the program will perform the chirp scan and show you the result on the top right figure. The background saved data will be subtracted from every scan step. 
6. Once the measurement is done, you may want to try to fit a polynomial function on the SHG region of interest. To do so, in the fitting block, the user may choose a wavelength bandwidth and an SNR threshold. By clicking on Apply SNR threshold, the bottom left figure will be adjusted and will show the desired region with nonzero signal where the SNR is big enough. 
7. To perform the fit, you have to choose the polynomial order between 1 to 10. Then by clicking on Fit chirp scan the program will find the maximum chirp value for each wavelength and do the polynomial fitting. The output bottom right graph will show the data and the fit. The outputs coefficients will be printed in the bottom text box. If the fit isn't right, you can try with a different polynomial order. 
8. Once the fit is good, the coefficients seems ok, than you can click on assign calibration. THIS FUNCTION ISN'T IMPLEMENTED YET. Eventually, the coefficients will be associated to the selected beam number. 
