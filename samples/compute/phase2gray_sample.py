from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration
from matplotlib import pyplot as plt
from scipy.constants import pi
from numpy.polynomial import Polynomial 
import numpy as np

def process_Phase2Gray_calibration(filepath):
    """
    Loads and stores SLM calibration coefficients from a CSV or TXT file.
    """
    try:
        calibration_file = filepath
        phase2gray_coeffs = np.loadtxt(filepath, delimiter=',', skiprows=1)
        
        #print(f"Loaded SLM calibration from: {filepath}")
        #logger.info(f"Loaded SLM calibration from: {filepath}")
        #print(f"Shape of coeffs: {self.phase2gray_coeffs.shape}")
        #logger.info(f"Shape of coeffs: {self.phase2gray_coeffs.shape}")

        phase2gray_coeffs = phase2gray_coeffs
        #logger.info('calibration coeffs sent to SLMWorker')

        print(f"Type of my_list: {type(phase2gray_coeffs)}")

    except Exception as e:
        print(f"Error loading SLM calibration: {e}")
        phase2gray_coeffs = None
        raise
        
    return phase2gray_coeffs


def phase2gray(phase_image):
    """
    Convert a phase image to grayscale values using the wavelength-dependent calibration.
    Each SLM column is assigned a wavelength using the stored pixel→wavelength polynomial.

    Parameters
    ----------
    phase_image : np.ndarray
        2D phase image (radians).
    self.phase2gray_coeffs : np.ndarray, optional
        Table of polynomial coefficients mapping phase→gray per wavelength, shape (Nwaves, 6)
        [wavelength, a5, a4, a3, a2, a1, a0].

    Returns
    -------
    gray_image : np.ndarray
        2D array (same shape as phase_image) with grayscale values [0–255].
    """

    # --- 1. Get or create wavelength mapping across SLM columns ---
    if pixelToWavelength is None:
        # fallback: use provided coefficients (if calibration not loaded)
        poly_coeffs = [691.50709535, 95.41146932, -0.03298118, 0.38760572, 0.00850083, -0.33233454]
        pixel_to_wavelength = Polynomial(poly_coeffs)
        print("Created synthetic pixel→wavelength calibration")

    else:
        pixel_to_wavelength = pixelToWavelength
        print("Using loaded pixel→wavelength calibration")

    # --- 3. Loop through each column and apply wavelength-dependent phase→gray mapping ---
    if phase2gray_coeffs is None:
        raise ValueError("phase2gray_coeffs (the LUT) must be provided.")

    cal_wavelengths = phase2gray_coeffs[:, 0]
    coeff_table = phase2gray_coeffs[:, 1:]  # shape: (N, 5 or 6)

    width = 1920
    height = 1200
    wavelengths_per_column = pixel_to_wavelength(width)

    # Interpolate coefficients for each column based on wavelength
    coeffs_interp = np.empty((width, coeff_table.shape[1]))
    for i in range(coeff_table.shape[1]):
        coeffs_interp[:, i] = np.interp(wavelengths_per_column, cal_wavelengths, coeff_table[:, i])

    # Create an empty grayscale image matching the input
    gray_image = np.zeros((height, width), dtype=np.float32)

    # --- 4. Compute grayscale for each pixel column ---
    for col in range(width):
        coeffs = coeffs_interp[col]
        # polynomial order should match your LUT (assumed 5th-order)
        gray_image[:, col] = (
            coeffs[0] * phase_image[:, col] ** 5 +
            coeffs[1] * phase_image[:, col] ** 4 +
            coeffs[2] * phase_image[:, col] ** 3 +
            coeffs[3] * phase_image[:, col] ** 2 +
            coeffs[4] * phase_image[:, col] +
            coeffs[5]
        )

    # --- 5. Normalize and clip ---
    #gray_image = np.clip(gray_image, 0, 255).astype(np.uint8)

    print("phase2gray: completed normalization using pixel→wavelength calibration.")

    return gray_image
#################################################################################################################
calibration_file = 'test_files/poly5_coeffs_by_wavelength_FYLA_600nm_750nm.csv'
pixelToWavelength = None

phase2gray_coeffs = process_Phase2Gray_calibration(calibration_file)
###############################################################################
bm=Beam(1920,1200)

amplitude = 1
bm.set_gratingAmplitude(amplitude)
period = 100
bm.set_gratingPeriod(period)

phase_image = bm.makeGrating()
# print(phase_image)

plt.figure()
plt.title('Phase grating')
plt.imshow(phase_image)
###############################################################################
gray_image = phase2gray(phase_image)
# print(gray_image)

plt.figure()
plt.title('Phase2Gray Normalization')
plt.imshow(gray_image)

plt.show()
###############################################################################
