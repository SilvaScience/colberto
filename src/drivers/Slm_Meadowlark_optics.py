# -*- coding: utf-8 -*-
"""
Created on Mon May 13 15:06:04 2024

@author: Mathieu Desmarais, Katherine Kosh
"""
# importation of the necessary libraries
import ctypes
from ctypes import *
from pathlib import Path
import logging
import datetime
logger = logging.getLogger(__name__)
awareness = ctypes.c_int()
errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
print(awareness.value)

# Set DPI Awareness  (Windows 10 and 8)
errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
# the argument is the awareness level, which can be 0, 1 or 2:
# for 1-to-1 pixel control I seem to need it to be non-zero (I'm using level 2)

# Set DPI Awareness  (Windows 7 and Vista)
success = ctypes.windll.user32.SetProcessDPIAware()
# behaviour on later OSes is undefined, although when I run it on my Windows 10 machine, it seems to work with effects identical to SetProcessDpiAwareness(1)


########### Path to the DLL file ############
folder_path = Path(__file__).resolve().parent.parent.parent #add or remove parent based on the file location

# Path to the DLL file
path_blink_c_wrapper = folder_path / "src" / "drivers" / "SDK" / "Blink_C_Wrapper.dll"
path_image_gen = folder_path / "src" / "drivers" / "SDK" / "Imagegen.dll"
path_blink_c_wrapper = str(path_blink_c_wrapper)
path_image_gen = str(path_image_gen)


# Definition of the SLM class
class SLM:
    '''
    A class to interface with a Spatial Light Modulator (SLM) via a C-based DLL.

    The SLM class loads the necessary DLL, sets up expected data types for various 
    functions, and provides methods to interact with the SLM hardware. This includes 
    creating and deleting the SDK, writing images, loading lookup tables (LUTs), 
    and retrieving or setting various SLM parameters.

    Attributes:
    -----------
    blink_dll : ctypes.CDLL
        The loaded DLL that contains the functions for controlling the SLM.

    Methods:
    --------
    create_sdk():
        Initializes the SDK for interacting with the SLM.

    delete_sdk():
        Deletes the SDK and frees associated resources.

    write_image(image_data, is_8_bit):
        Writes an image to the SLM. The image data is passed as a ctypes pointer, 
        and a flag indicates whether the image is 8-bit.

    load_lut(file_path):
        Loads a lookup table (LUT) from a file to the SLM. The file path is provided 
        as a string.

    set_post_ramp_slope(postRampSlope):
        Sets the post-ramp slope for the SLM. The slope value is provided as an integer.

    set_pre_ramp_slope(preRampSlope):
        Sets the pre-ramp slope for the SLM. The slope value is provided as an integer.

    set_channel(channel):
        Sets the SLM to a specific channel. The channel is specified as an integer.

    get_slm_temp():
        Retrieves the current temperature of the SLM in degrees Celsius.

    get_slm_vcom():
        Retrieves the current VCOM (common voltage) of the SLM in volts.

    set_slm_vcom(volts):
        Sets the VCOM (common voltage) of the SLM. The voltage value is provided as a float.

    get_height():
        Retrieves the height of the SLM display in pixels.

    get_width():
        Retrieves the width of the SLM display in pixels.

    get_depth():
        Retrieves the color depth (bit depth) of the SLM display.

    get_slm_found():
        Checks whether the SLM hardware was found and initialized successfully.

    get_com_found():
        Checks whether the COM (communication) port for the SLM was found.

    parameter_slm():
        Retrieves and returns key SLM parameters such as height, width, depth, 
        along with default RGB and bit-depth settings.

    Usage:
    ------
    slm = SLM()
    slm.create_sdk()
    slm.set_channel(1)
    image_data = np.array([...], dtype=np.uint8)
    slm.write_image(image_data, is_8_bit=True)
    slm.delete_sdk()
'''

    def __init__(self):
        # Chargement de la DLL
        # Loading the DLL
        logger.info('Trying to create the blink dll using path %s'%path_blink_c_wrapper)
        self.blink_dll = ctypes.CDLL(path_blink_c_wrapper)
        logger.info('Created the blink dll()')

        # Définition des types de données attendus pour les fonctions
        # Defining expected data types for functions 
        self.blink_dll.Create_SDK.restype = None
        self.blink_dll.Delete_SDK.restype = None
        self.blink_dll.Write_image.restype = ctypes.c_int
        self.blink_dll.Load_lut.restype = ctypes.c_int
        self.blink_dll.SetPostRampSlope.restype = ctypes.c_int
        self.blink_dll.SetPreRampSlope.restype = ctypes.c_int
        self.blink_dll.Set_channel.restype = ctypes.c_int
        self.blink_dll.Get_SLMTemp.restype = ctypes.c_double
        self.blink_dll.Get_SLMVCom.restype = ctypes.c_double
        self.blink_dll.Set_SLMVCom.restype = ctypes.c_int
        self.blink_dll.Get_Height.restype = ctypes.c_int
        self.blink_dll.Get_Width.restype = ctypes.c_int
        self.blink_dll.Get_Depth.restype = ctypes.c_int
        self.blink_dll.Get_SLMFound.restype = ctypes.c_int
        self.blink_dll.Get_COMFound.restype = ctypes.c_int

    def create_sdk(self):
        """Loads the DLLs and creates the window in the off-screen required to send the image to the SLM """
        self.blink_dll.Create_SDK()

    def delete_sdk(self):
        """Graciously closes the communication with the SLM"""
        self.blink_dll.Delete_SDK()

    def write_image(self, image_data, is_8_bit):
        """
        Writes an image to the SLM.
        input:
            - image_data (uint8 np.array): either a 1D 8-bit array of image data that has 1920*1152 or 1920*1200 elements or can be an RGB 1D 8-bit
                array that has 1920x1152*3 elements or 1920*1200*3. RGB data is expected as follows: pixel 0 Red, pixel
                0 green, pixel 0 blue, pixel 1 red, pixel 1 green, pixel 1 blue, and so on. It is expected through the SDK that
                the array size will match the SLM dimensions
            - is_8_bit: If an RGB array is passed, should be set to 0 otherwise should be 1.
        """
        self.blink_dll.Write_image(image_data.ctypes.data_as(POINTER(c_ubyte)), is_8_bit)
        logger.info('Image written')

    def load_lut(self, file_path):
        """
        Loads a calibration to the hardware that corrects for the nonlinear response of the
        liquid crystal to voltage
        input:
            - file_path: Path to the LUT file. Because images are processed through the LUT in hardware, it is important that the LUT file be loaded to
                the hardware prior to writing images to the SLM. The function takes a path to a LUT file and supports file
                types of: *.blt, *.lut, and *.txt.
        """
        logger.info('%s LoadLUT Successful'%(datetime.datetime.now()))
        return self.blink_dll.Load_lut(file_path.encode())

    def set_post_ramp_slope(self, postRampSlope):
        return self.blink_dll.SetPostRampSlope(postRampSlope)

    def set_pre_ramp_slope(self, preRampSlope):
        return self.blink_dll.SetPreRampSlope(preRampSlope)

    def set_channel(self, channel):
        return self.blink_dll.Set_channel(channel)

    def get_slm_temp(self):
        return self.blink_dll.Get_SLMTemp()

    def get_slm_vcom(self):
        return self.blink_dll.Get_SLMVCom()

    def set_slm_vcom(self, volts):
        return self.blink_dll.Set_SLMVCom(ctypes.c_float(volts))

    def get_height(self):
        return self.blink_dll.Get_Height()

    def get_width(self):
        return self.blink_dll.Get_Width()

    def get_depth(self):
        return self.blink_dll.Get_Depth()
    
    def get_slm_found(self):
        return self.blink_dll.Get_SLMFound()

    def get_com_found(self):
        return self.blink_dll.Get_COMFound()
    
    def parameter_slm(self):
        rgb=1
        bit=1
        height= SLM.get_height(self)
        width = SLM.get_width(self)
        depth = SLM.get_depth(self)
        RGB   = ctypes.c_uint(rgb)
        isEightBitImage = ctypes.c_uint(bit)
        return height,width,depth,RGB,isEightBitImage
    
    def get_size(self):
        width=SLM.get_width(self)
        height=SLM.get_height(self)
        return width,height


class ImageGen:
    def __init__(self):
        # Load the DLL
        self.image_gen_dll = ctypes.CDLL(path_image_gen)
        #print("Le DDL est chargé ")
        print("The DDL is loaded")
        # Define function prototypes for the image generation functions
        self.image_gen_dll.Concatenate_TenBit.restype = None
        self.image_gen_dll.Generate_Stripe.restype = None
        self.image_gen_dll.Generate_Checkerboard.restype = None
        self.image_gen_dll.Generate_Solid.restype = None
        self.image_gen_dll.Generate_Random.restype = None
        self.image_gen_dll.Generate_Zernike.restype = None
        self.image_gen_dll.Generate_FresnelLens.restype = None
        self.image_gen_dll.Generate_Grating.restype = None
        self.image_gen_dll.Generate_Sinusoid.restype = None
        self.image_gen_dll.Generate_LG.restype = None
        self.image_gen_dll.Generate_ConcentricRings.restype = None
        self.image_gen_dll.Generate_Axicon.restype = None
        self.image_gen_dll.Mask_Image.restype = None
        self.image_gen_dll.Initialize_HologramGenerator.restype = ctypes.c_int
        self.image_gen_dll.CalculateAffinePolynomials.restype = ctypes.c_int
        self.image_gen_dll.Generate_Hologram.restype = ctypes.c_int
        self.image_gen_dll.Destruct_HologramGenerator.restype = None
        self.image_gen_dll.Initialize_GerchbergSaxton.restype = ctypes.c_int
        self.image_gen_dll.GerchbergSaxton.restype = ctypes.c_int
        self.image_gen_dll.Destruct_GerchbergSaxton.restype = None
        self.image_gen_dll.Initialize_RegionalLUT.restype = ctypes.c_int
        self.image_gen_dll.Load_RegionalLUT.restype = ctypes.c_int
        self.image_gen_dll.Apply_RegionalLUT.restype = ctypes.c_int
        self.image_gen_dll.Destruct_RegionalLUT.restype = None
        self.image_gen_dll.SetBESTConstants.restype = ctypes.c_int
        self.image_gen_dll.GetBESTAmplitudeMask.restype = ctypes.c_int
        self.image_gen_dll.GetBESTAxialPSF.restype = ctypes.c_int
        self.image_gen_dll.Generate_BESTRings.restype = None

    def concatenate_ten_bit(self, array_one, array_two, width, height):
        self.image_gen_dll.Concatenate_TenBit(array_one, array_two, width, height)
    
    def generate_stripe(self, array, wfc, width, height, depth, pixel_val_one, pixel_val_two, pixels_per_stripe, b_vert, rgb):
        self.image_gen_dll.Generate_Stripe(array, wfc, width, height, depth, pixel_val_one, pixel_val_two, pixels_per_stripe, b_vert, rgb)
    
    def generate_checkerboard(self, array, wfc, width, height, depth, pixel_val_one, pixel_val_two, pixels_per_check, rgb):
        self.image_gen_dll.Generate_Checkerboard(array, wfc, width, height, depth, pixel_val_one, pixel_val_two, pixels_per_check, rgb)
    
    def generate_solid(self, array, wfc, width, height, depth, pixel_val, rgb):
        self.image_gen_dll.Generate_Solid(array, wfc, width, height, depth, pixel_val, rgb)
    
    def generate_random(self, array, wfc, width, height, depth, rgb):
        self.image_gen_dll.Generate_Random(array, wfc, width, height, depth, rgb)
    
    def generate_zernike(self, array, wfc, width, height, depth, center_x, center_y, radius, piston, tilt_x, tilt_y, power, astig_x, astig_y, coma_x, coma_y, primary_spherical, trefoil_x, trefoil_y, secondary_astig_x, secondary_astig_y, secondary_coma_x, secondary_coma_y, secondary_spherical, tetrafoil_x, tetrafoil_y, tertiary_spherical, quaternary_spherical, rgb):
        self.image_gen_dll.Generate_Zernike(array, wfc, width, height, depth, center_x, center_y, radius, piston, tilt_x, tilt_y, power, astig_x, astig_y, coma_x, coma_y, primary_spherical, trefoil_x, trefoil_y, secondary_astig_x, secondary_astig_y, secondary_coma_x, secondary_coma_y, secondary_spherical, tetrafoil_x, tetrafoil_y, tertiary_spherical, quaternary_spherical, rgb)
    
    def generate_fresnel_lens(self, array, wfc, width, height, depth, center_x, center_y, radius, power, cylindrical, horizontal, rgb):
        self.image_gen_dll.Generate_FresnelLens(array, wfc, width, height, depth, center_x, center_y, radius, power, cylindrical, horizontal, rgb)
    
    def generate_grating(self, array, wfc, width, height, depth, period, increasing, horizontal, rgb):
        #print("test_grating:", array)
        #print("WFC:", wfc)
        self.image_gen_dll.Generate_Grating(array, wfc, width, height, depth, period, increasing, horizontal, rgb)
        
    def generate_sinusoid(self, array, wfc, width, height, depth, period, horizontal, rgb):
        self.image_gen_dll.Generate_Sinusoid(array, wfc, width, height, depth, period, horizontal, rgb)

    def generate_lg(self, array, wfc, width, height, depth, vortex_charge, center_x, center_y, fork, rgb):
        self.image_gen_dll.Generate_LG(array, wfc, width, height, depth, vortex_charge, center_x, center_y, fork, rgb)
    
    def generate_concentric_rings(self, array, wfc, width, height, depth, inner_diameter, outer_diameter, pixel_val_one, pixel_val_two, center_x, center_y, rgb):
        self.image_gen_dll.Generate_ConcentricRings(array, wfc, width, height, depth, inner_diameter, outer_diameter, pixel_val_one, pixel_val_two, center_x, center_y, rgb)
    
    def generate_axicon(self, array, wfc, width, height, depth, phase_delay, center_x, center_y, increasing, rgb):
        self.image_gen_dll.Generate_Axicon(array, wfc, width, height, depth, phase_delay, center_x, center_y, increasing, rgb)
    
    def mask_image(self, array, width, height, depth, region, num_regions, rgb):
        self.image_gen_dll.Mask_Image(array, width, height, depth, region, num_regions, rgb)
    
    def initialize_hologram_generator(self, width, height, depth, iterations, rgb):
        return self.image_gen_dll.Initialize_HologramGenerator(width, height, depth, iterations, rgb)
    
    def calculate_affine_polynomials(self, slm_x_0, slm_y_0, cam_x_0, cam_y_0, slm_x_1, slm_y_1, cam_x_1, cam_y_1, slm_x_2, slm_y_2, cam_x_2, cam_y_2):
        return self.image_gen_dll.CalculateAffinePolynomials(slm_x_0, slm_y_0, cam_x_0, cam_y_0, slm_x_1, slm_y_1, cam_x_1, cam_y_1, slm_x_2, slm_y_2, cam_x_2, cam_y_2)
    
    def generate_hologram(self, array, wfc, x_spots, y_spots, z_spots, i_spots, n_spots, apply_affine):
        return self.image_gen_dll.Generate_Hologram(array, wfc, x_spots, y_spots, z_spots, i_spots, n_spots, apply_affine)
    
    def destruct_hologram_generator(self):
        self.image_gen_dll.Destruct_HologramGenerator()
    
    def initialize_gerchberg_saxton(self):
        return self.image_gen_dll.Initialize_GerchbergSaxton()
    
    def gerchberg_saxton(self, phase, input_img, wfc, width, height, depth, iterations, rgb):
        return self.image_gen_dll.GerchbergSaxton(phase, input_img, wfc, width, height, depth, iterations, rgb)
    
    def destruct_gerchberg_saxton(self):
        self.image_gen_dll.Destruct_GerchbergSaxton()
    
    def initialize_regional_lut(self, width, height, depth, num_boards):
        return self.image_gen_dll.Initialize_RegionalLUT(width, height, depth, num_boards)
    
    def load_regional_lut(self, regional_lut_path, max_val, min_val, board):
        return self.image_gen_dll.Load_RegionalLUT(regional_lut_path.encode(), max_val, min_val, board)
    
    def apply_regional_lut(self, array, board):
        return self.image_gen_dll.Apply_RegionalLUT(array, board)
    
    def destruct_regional_lut(self):
        self.image_gen_dll.Destruct_RegionalLUT()
    
    def set_best_constants(self, focal_length, beam_diameter, wavelength, slm_pitch, slm_num_pixels, obj_na, obj_mag, obj_ref_ind, tube_length, relay_mag):
        return self.image_gen_dll.SetBESTConstants(focal_length, beam_diameter, wavelength, slm_pitch, slm_num_pixels, obj_na, obj_mag, obj_ref_ind, tube_length, relay_mag)
    
    def get_best_amplitude_mask(self, amplitude_y, peaks, peaks_index, period):
        return self.image_gen_dll.GetBESTAmplitudeMask(amplitude_y, peaks, peaks_index, period)
    
    def get_best_axial_psf(self, axial_amplitude, intensity, period, outer_diameter, inner_diameter):
        return self.image_gen_dll.GetBESTAxialPSF(axial_amplitude, intensity, period, outer_diameter, inner_diameter)
    
    def generate_best_rings(self, array, wfc, width, height, depth, center_x, center_y, s, rgb):
        self.image_gen_dll.Generate_BESTRings(array, wfc, width, height, depth, center_x, center_y, s, rgb)

if __name__ == "__main__":
    SLM()