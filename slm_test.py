'''
Created on  14 mai 2024
@author: Mathieu
'''
import ctypes

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
        return self.blink_dll.Write_image(image_data, is_8_bit)

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