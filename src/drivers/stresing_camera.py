#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  5 10:52:39 2024

@author: katiekoch
"""
from ctypes import *
from pathlib import Path
import configparser

class camera_settings(Structure):
	_fields_ = [("use_software_polling", c_uint32),
		("sti_mode", c_uint32),
		("bti_mode", c_uint32),
		("stime_in_microsec", c_uint32),
		("btime_in_microsec", c_uint32),
		("sdat_in_10ns", c_uint32),
		("bdat_in_10ns", c_uint32),
		("sslope", c_uint32),
		("bslope", c_uint32),
		("xckdelay_in_10ns", c_uint32),
		("sec_in_10ns", c_uint32),
		("trigger_mode_cc", c_uint32),
		("SENSOR_TYPE", c_uint32),
		("CAMERA_SYSTEM", c_uint32),
		("CAMCNT", c_uint32),
		("PIXEL", c_uint32),
		("mshut", c_uint32),
		("led_off", c_uint32),
		("sensor_gain", c_uint32),
		("adc_gain", c_uint32),
		("temp_level", c_uint32),
		("shortrs", c_uint32),
		("gpx_offset", c_uint32),
		("FFT_LINES", c_uint32),
		("VFREQ", c_uint32),
		("fft_mode", c_uint32),
		("lines_binning", c_uint32),
		("number_of_regions", c_uint32),
		("keep", c_uint32),
		("region_size", c_uint32 * 8),
		("dac_output", c_uint32 * 8 * 8), # 8 channels for 8 possible cameras in line
		("tor", c_uint32),
		("adc_mode", c_uint32),
		("adc_custom_pattern", c_uint32),
		("bec_in_10ns", c_uint32),
		("IS_HS_IR", c_uint32),
		("ioctrl_impact_start_pixel", c_uint32),
		("ioctrl_output_width_in_5ns", c_uint32 * 8),
		("ioctrl_output_delay_in_5ns", c_uint32 * 8),
		("ictrl_T0_period_in_10ns", c_uint32),
		("dma_buffer_size_in_scans", c_uint32),
		("tocnt", c_uint32),
		("ticnt", c_uint32),
		("use_ec", c_uint32),
		("write_to_disc", c_uint32),
		("file_path", c_char * 256),
		("file_split_mode", c_uint32),
		("is_cooled_cam", c_uint32),]

class measurement_settings(Structure):
	_fields_ = [("board_sel", c_uint32),
	("nos", c_uint32), 
	("nob", c_uint32),
	("contiuous_measurement", c_uint32),
	("cont_pause_in_microseconds", c_uint32),
	("camera_settings", camera_settings * 5)]
    
class stresing:

    def __init__(self, path_config, path_camera_dll):
        
        # Create a ConfigParser object
        config = configparser.ConfigParser()

        # Read the INI file
        config.read(path_config)
        
        ''' Initializes camera and camera settings '''
        
        # Create an instance of the settings struct
        self.settings = measurement_settings()
        
        # Set all settings that are needed for the measurement. See EBST_CAM/shared_src/struct.h for details.
        
        #identifier of PCIe card
        self.drvno = 0 
        
        #controls which boards are used for the measurement 
        self.settings.board_sel = int(config.get("General","boardSel"))  #1 ?? 
        
        #number of samples
        self.settings.nos = int(config.get("General","nos")) #1000

        #number of boards
        self.settings.nob = int(config.get("General","nob")) 
        
        board_num = [0,1,2,3,4]
        i=0
        for i in board_num:
            value = config.get("General", f'board{i}')
            if value == "true":
                Board = f'board{i}'
        
        #Scan trigger input mode
        self.settings.camera_settings[0].sti_mode = int(config.get(Board,"sti")) #4 
        
        #Block trigger input counter 
        self.settings.camera_settings[0].bti_mode = int(config.get(Board,"bti")) #4 
            #determines how many block trigger inputs are skipped before the next block start is triggered
            #min = 0/step = 1/ max = 127
        
        #senor_type for camera 
        self.settings.camera_settings[0].SENSOR_TYPE = int(config.get(Board,"sensorType")) #0 
            #0: PDA - Photodiode Array
            
        #type of camera system 
        self.settings.camera_settings[0].CAMERA_SYSTEM = int(config.get(Board,"cameraSystem")) #2 
            #2: 3030 system
            
        #Camcnt is the number of cameras which are connected to one PCIe board
        self.settings.camera_settings[0].CAMCNT = int(config.get(Board,"camcnt")) #1
       
        #Pixel is the number of pixels in one sensor
        self.settings.camera_settings[0].PIXEL = int(config.get(Board,"pixelcnt")) #1024 
        
        #Size of DMA buffer in scans
        self.settings.camera_settings[0].dma_buffer_size_in_scans = 1000 
            #1000 is our default
            #60 is also working with high speed
        
        #Scan timer in microseconds is the time between the start of two readouts.
        self.settings.camera_settings[0].stime_in_microsec = int(config.get(Board,"stimer")) #8000 
            #min = 1 µs/step: 1 µs/max: 268,435,455 µs = 268.435455 s
        
        #Block timer in microseconds is the time between the start of two blocks of readouts
        self.settings.camera_settings[0].btime_in_microsec = int(float(config.get(Board,"btimer"))) #1000000 
            #min = 1 µs/step: 1 µs/max: 268,435,455 µs = 268.435455 s
	    
        self.settings.camera_settings[0].number_of_regions = int(config.get(Board,"numberOfRegions"))
        self.settings.camera_settings[0].region_size[0] = int(config.get(Board,"regionSize1"))
        self.settings.camera_settings[0].region_size[1] = int(config.get(Board,"regionSize2"))
        self.settings.camera_settings[0].region_size[2] = int(config.get(Board,"regionSize3"))
        
        if config.get(Board,"use_software_polling")=="true":
            self.settings.camera_settings[0].use_software_polling = 1
        else:
            self.settings.camera_settings[0].use_software_polling = 0
        
        self.settings.camera_settings[0].VFREQ = int(config.get(Board,"vfreq"))
	    
        #:dac_output[MAXCAMCNT][DACCOUNT] = Array for output levels of each digital to analog converter
        self.settings.camera_settings[0].dac_output[0][0] = 55000
        self.settings.camera_settings[0].dac_output[0][1] = 55000
        self.settings.camera_settings[0].dac_output[0][2] = 55000
        self.settings.camera_settings[0].dac_output[0][3] = 55000
        self.settings.camera_settings[0].dac_output[0][4] = 55000
        self.settings.camera_settings[0].dac_output[0][5] = 55000
        self.settings.camera_settings[0].dac_output[0][6] = 55000
        self.settings.camera_settings[0].dac_output[0][7] = 55000
        
        # Load ESLSCDLL.dll
        self.camera_dll = WinDLL(path_camera_dll)
        
        # Set the return type of DLLConvertErrorCodeToMsg to c-string pointer
        self.camera_dll.DLLConvertErrorCodeToMsg.restype = c_char_p
        
        # Create a variable of type uint8_t
        self.number_of_boards = c_uint8(0)
        
        # Get the pointer the variable
        self.ptr_number_of_boards = pointer(self.number_of_boards)
        
        '''DLLInitDriver: Initialize the driver. Call it once at startup.'''

        # Initialize the driver and pass the created pointer to it. 
        #number_of_boards should show the number of detected PCIe boards after the next call.
        self.status = self.camera_dll.DLLInitDriver(self.ptr_number_of_boards)
        
        # Check the status code after each DLL call. 
        #When it is not 0, which means there is no error, an exception is raised. 
        #The error message will be displayed and the script will stop.
        if(self.status != 0):
        	raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))
       
        ''' DLLInitBoard: Initialize PCIe board. Call it once at startup.''' 
       
        # Initialize the PCIe board.
        self.status = self.camera_dll.DLLInitBoard()
        if(self.status != 0):
         	raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))
        
        ''' DLLSetGlobalSettings or DLLSetGlobalSettings_matlab:
            Set settings parameter according to your camera system. 
            Call it once at startup and every time you changed settings.'''
        
        # Set all settings with the earlier created settings struct
        self.status = self.camera_dll.DLLSetGlobalSettings(self.settings)
        if(self.status != 0):
            raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))
        
        ''' DLLInitMeasurement: Initialize Hardware and Software for the Measurement. 
            Call it once at startup and every time you changed settings. '''
      
        # Initialize the measurement. The settings from the step before will be used for this.
        self.status = self.camera_dll.DLLInitMeasurement()
        if(self.status != 0):
            raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))

    def close(self):
        
        ''' DLLExitDriver: Before exiting your software, use this call for cleanup.'''
        
        # Exit the driver
        self.status = self.camera_dll.DLLExitDriver()
        if(self.status != 0):
        	raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))
            
    def measure(self, use_blocking_call):
        
        ''' Initializes and starts a measurment
            Input: use_blocking_call = True or False 
                True - data is returned after the measurement is finished 
                False - data is returned immediately'''
        
        ''' DLLStartMeasurement_blocking or DLLStartMeasurement_nonblocking: 
            Start the measurement. 
            Call it every time you want to measure.'''
        
        # Initialize the measurement. The settings from the step before will be used for this.
        self.status = self.camera_dll.DLLInitMeasurement()
        if(self.status != 0):
            raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))
        
        if use_blocking_call:
        	# Start the measurement. 
            #This is the blocking call, which means it will return when the measurement is finished
            #This is done to ensure that no data access happens before all data is collected.
        	self.status = self.camera_dll.DLLStartMeasurement_blocking()
        	if(self.status != 0):
        		raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(status))
        else:
        	# Start the measurement. This is the nonblocking call, which means it will return immediately. 
        	self.camera_dll.DLLStartMeasurement_nonblocking()

        	self.cur_sample = c_int64(-2)
        	self.ptr_cur_sample = pointer(self.cur_sample)
        	self.cur_block = c_int64(-2)
        	self.ptr_cur_block = pointer(self.cur_block)

        	while self.cur_sample.value < self.settings.nos-1 or self.cur_block.value < self.settings.nob-1:
        		self.camera_dll.DLLGetCurrentScanNumber(self.drvno, self.ptr_cur_sample, self.ptr_cur_block)
        		print("sample: "+str(self.cur_sample.value)+" block: "+str(self.cur_block.value))

    def stop(self):
        
        '''DLLAbortMeasurement: Use this call, if you want to abort the measurement.'''
        
        return self.camera_dll.DLLAbortMeasurement
    
# DLLReturnFrame, DLLCopyAllData, or DLLCopyOneBlock: Get the data with one of the following 3 calls. Call it how many times you want.

    def get_data_one_frame(self,sample,block):
        
        ''' Get data of a single measurment
            Inputs: sample = sample numner between 0 & nos-1 (uint32_t) 
                    block = sample numner between 0 & nob-1 (uint32_t)
                    
              
              camera_dll.DLLReturnFrame(drvno,sample,block,camera,pixel,uint16_t*pdest)
                  #drvno = identifier of PCIe card
                  #camera = camera number between 0...CAMCNT - 1 (uint16_t) 
                      !!for now we only have one camera, so this doesnt need to be an input!!
                  #pdest = Pointer where frame data will be written with size of (uint16_t) * pixel
                  #pixel = Length of the frame to copy. Typically = pixel
                  
            Ouput: python list with length = pixel number (one value for each pixel)
                
            '''
        
        # Create an c-style uint16 array of size pixel which is initialized to 0
        self.PIXEL = self.settings.camera_settings[0].PIXEL
        self.frame_buffer = (c_uint16 * self.PIXEL)(0)
        self.ptr_frame_buffer = pointer(self.frame_buffer)
                
        # Get the data of one frame. (camera = 0 in this case b/c we only have one)        
        self.status = self.camera_dll.DLLReturnFrame(self.drvno, sample, block, 0, self.PIXEL, self.ptr_frame_buffer)

        if(self.status != 0):
        	raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))
        
        # Convert the c-style array to a python list
        self.list_frame_buffer = [self.frame_buffer[i] for i in range(self.PIXEL)]
        
        return self.list_frame_buffer

    def get_data_one_block(self, block):
        
        ''' Copies one block of pixel data to pdest
            Inputs: block = selects which block to copy 
                
            camera_dll.DLLReturnFrame(drvno,block,uint16_t*pdest)
                #drvno = identifier of PCIe card
                #block = selects which block to copy 
                #pdest = address where data is written, should be a buffer with 
                size: nos * camcnt * pixel * size of (uint16_t)
        
        '''
        
        self.block_buffer = (c_uint16 * (self.settings.PIXEL * self.settings.nos * 
                                         self.settings.camera_settings[0].CAMCNT))(0)
        self.ptr_block_buffer = pointer(self.block_buffer)
        
        # This block is showing you how to get all data of one frame with one DLL call
        self.status = self.camera_dll.DLLCopyOneBlock(self.drvno, block, ptr_block_buffer)
        if(self.status != 0):
         	raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))
        
        return 
    
    def get_all_data(self):
        
        ''' Copies all pixel data to pdest
                
            camera_dll.DLLCopyAllData(drvno,uint16_t*pdest)
                #drvno = identifier of PCIe card
                #pdest = address where data is written, should be a buffer with
                size: nos * nob * camcnt * pixel * size of (uint16_t)
        
        '''
        self.data_buffer = (c_uint16 * (self.settings.camera_settings[0].PIXEL
                                        * self.settings.nos * self.settings.camera_settings[0].CAMCNT 
                                        * self.settings.nob))(0)
        self.ptr_data_buffer = pointer(self.data_buffer)
        
        # # This block is showing you how to get all data of the whole measurement with one DLL call
        self.status = self.camera_dll.DLLCopyAllData(self.drvno, self.ptr_data_buffer)
        if(self.status != 0):
         	raise BaseException(self.camera_dll.DLLConvertErrorCodeToMsg(self.status))
             
        return
