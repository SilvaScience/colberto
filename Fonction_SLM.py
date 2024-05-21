'''
Created on  14 mai 2024
@author: Mathieu
'''
from ctypes import *
import ctypes

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


class SLM:
    def __init__(self, dll_path):
        # Chargement de la DLL
        self.blink_dll = ctypes.CDLL(dll_path)

        # Définition des types de données attendus pour les fonctions
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

    def Create_SDK(self):
        '''
        Crée le SDK
        '''
        self.blink_dll.Create_SDK()

    def Delete_SDK(self):
        self.blink_dll.Delete_SDK()



    def Write_image(self, image_data, is_8_bit):
        return self.blink_dll.Write_image(image_data.ctypes.data_as(POINTER(c_ubyte)), is_8_bit)



    def Load_lut(self, file_path):
        return self.blink_dll.Load_lut(file_path.encode())

    def SetPostRampSlope(self, postRampSlope):
        return self.blink_dll.SetPostRampSlope(postRampSlope)

    def SetPreRampSlope(self, preRampSlope):
        return self.blink_dll.SetPreRampSlope(preRampSlope)

    def Set_channel(self, channel):
        return self.blink_dll.Set_channel(channel)

    def Get_SLMTemp(self):
        return self.blink_dll.Get_SLMTemp()

    def Get_SLMVCom(self):
        return self.blink_dll.Get_SLMVCom()

    def Set_SLMVCom(self, volts):
        return self.blink_dll.Set_SLMVCom(ctypes.c_float(volts))

    def Get_Height(self):
        return self.blink_dll.Get_Height()

    def Get_Width(self):
        return self.blink_dll.Get_Width()

    def Get_Depth(self):
        return self.blink_dll.Get_Depth()

    def Get_SLMFound(self):
        return self.blink_dll.Get_SLMFound()

    def Get_COMFound(self):
        return self.blink_dll.Get_COMFound()
    
    def Parameter_SLM(self,rgb,bit):
        height= SLM.Get_Height(self)
        width = SLM.Get_Width(self)
        depth = SLM.Get_Depth(self)
        RGB   = ctypes.c_uint(rgb)
        isEightBitImage = ctypes.c_uint(bit)
        return height,width,depth,RGB,isEightBitImage



class ImageGen:
    def __init__(self, dll_path):
        # Load the DLL
        self.image_gen_dll = ctypes.CDLL(dll_path)
        print("Le DDL est chargé ")
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
        print("test_grating:", array)
        print("WFC:", wfc)
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