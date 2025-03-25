from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# only need one or the other for SLM class
#from src.drivers.Slm_Meadowlark_optics import SLM
from src.compute.SLMBogus import SLM

from src.compute import colbertoutils as co
from src.compute.calibration import Calibration

cal = Calibration(SLM)

folder_path = Path(__file__).resolve().parent.parent.parent #add or remove parent based on the file location
path = folder_path / "samples" / "compute" / "test_files" 
path = str(path)
#print(path)

Data = np.loadtxt(path + r'/mercury_lamp_calib_August2024')
Data = np.transpose(Data)

pixels = Data[:,0]
test_spectra = Data[:,1]

height = 7000
peak_pos, peak_heights = co.peak_finder(test_spectra, height)

plt.plot(pixels,test_spectra)
plt.plot(peak_pos,peak_heights, 'x')
plt.xlabel('pixel number')
plt.ylabel('intensity')
plt.show()

#wave = cal.user_input_assign_pixelnumber_to_wavelength(peak_pos)
#for the sample data:
    #peak 226 = 365
    #peak 309 = 404
    #peak 374 = 435
    #peak 607 = 546

#use this wavelength array for testing to avoid having to input values everytime 
wavelength = [365, 404, 435, 546]
#print(wavelength)

degree = 3
wavelength_calib = cal.spectral_camera_pixel2wavelength_calib(peak_pos,wavelength,degree,pixels)

plt.plot(peak_pos,wavelength,'x')
plt.plot(pixels, wavelength_calib)
plt.xlabel('pixel number')
plt.ylabel('wavelength')
plt.show()


filename = 'test_save_function'

co.save_data(filename,wavelength_calib)
