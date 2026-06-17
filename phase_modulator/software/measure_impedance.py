import numpy as np
from time import sleep
from pymeasure.instruments.keysight import KeysightDSOX1102G
from pymeasure.instruments.agilent import Agilent33500
from matplotlib import pyplot as plt
import argparse
from time import localtime, strftime
from electrutils.waveform import Wave# This is a repo on https://github.com/fthouin/electrutils/
import h5py


### Experimental parameters of impedance sweep
resistance=100
filename="piezo_od1_noair"+strftime("%H_%M", localtime())+"_impedance_measurement.h5"



from os import environ
generator = Agilent33500('TCPIP::192.168.1.130::INSTR')
generator.reset()
generator.shape = 'SIN'                 # Sets default channel output signal shape to sine
generator.amplitude= 5# Sets default channel output frequency to 1 kHz
generator.output='on'
scope = KeysightDSOX1102G('TCPIP::192.168.1.126::INSTR')


#Prepare scope
data_in_out=[]
times=[]
freqs=np.logspace(4,6,200)
for freq in freqs:
    print(freq)
    generator.frequency=freq
    scope.autoscale()
    scope.single()
    ch1_data_array, ch1_preamble = scope.download_data(source="channel1", points=2000)
    ch2_data_array, ch2_preamble = scope.download_data(source="channel2", points=2000)
    time=np.arange(len(ch1_data_array))*ch1_preamble["xincrement"]+ch1_preamble["xorigin"]
    times.append(time)
    data_in_out.append(np.array([ch1_data_array,ch2_data_array,time]))
with h5py.File(filename,'w') as f:
    groupin=f.create_group('data')
    groupin.attrs['generator Output impedance']=50
    for data,freq,time in zip(data_in_out,freqs,times):
        dataset=groupin.create_dataset("%.2e"%freq,data=data)
        dataset.attrs['instructions']='first row is Voltage (V) of chan 1, second row is Voltage of chan 2 third is time (s)'
        dataset.attrs['freq']=freq
    f.create_dataset('resistance',data=resistance)
generator.output='off'
scope.shutdown()