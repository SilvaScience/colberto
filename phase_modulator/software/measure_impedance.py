import numpy as np
from awg_scpi import AWG
from time import sleep
from pymeasure.instruments.keysight import KeysightDSOX1102G
from matplotlib import pyplot as plt
import argparse
from time import localtime, strftime
from electrutils.waveform import Wave# This is a repo on https://github.com/fthouin/electrutils/
import h5py

parser = argparse.ArgumentParser(description='Access and control an AWG')
parser.add_argument('chan', nargs='?', type=int, help='Channel to access/control (starts at 1)', default=1)
args = parser.parse_args()

### Experimental parameters of impedance sweep
resistance=100
filename="47kresistor_"+strftime("%H:%M", localtime())+"_impedance_measurement.h5"



from os import environ
resource = environ.get('AWG_IP', 'TCPIP::192.168.1.127::INSTR')
awg = AWG(resource)
scope = KeysightDSOX1102G('TCPIP::192.168.1.126::INSTR')
## Upgrade Object to best match based on IDN string
awg = awg.getBestClass()

## Open this object and work with it
awg.open()

print('Using SCPI Device:     ' + awg.idn() + ' of series: ' + awg.series + '\n')

# set the channel (can pass channel to each method or just set it
# once and it becomes the default for all following calls)
awg.channel = str(args.chan)
# Prepare the AWG
awg.reset()               
awg.setOutputLoad(True,channel=1)
awg.setVoltageProtection(11)
awg.setAmplitude(5)
awg.setOffset(0)
awg.setPhase(0)
awg.outputOn()
#Prepare scope
data_in_out=[]
times=[]
freqs=np.logspace(1,8,75)
print("Voltage Protection is set to maximum: {}V Amplitude (assumes 0V offset)".format(awg.queryVoltageProtection()))
for freq in freqs:
    print(freq)
    awg.setFrequency(freq)
    scope.autoscale()
    scope.single()
    ch1_data_array, ch1_preamble = scope.download_data(source="channel1", points=2000)
    ch2_data_array, ch2_preamble = scope.download_data(source="channel2", points=2000)
    time=np.arange(len(ch1_data_array))*ch1_preamble["xincrement"]+ch1_preamble["xorigin"]
    times.append(time)
    data_in_out.append(np.array([ch1_data_array,ch2_data_array,time]))
with h5py.File(filename,'w') as f:
    groupin=f.create_group('data')
    groupin.attrs['AWG Output impedance']=50
    for data,freq,time in zip(data_in_out,freqs,times):
        dataset=groupin.create_dataset("%.2e"%freq,data=data)
        dataset.attrs['instructions']='first row is Voltage (V) of chan 1, second row is Voltage of chan 2 third is time (s)'
        dataset.attrs['freq']=freq
    f.create_dataset('resistance',data=resistance)

# return to LOCAL mode
awg.setLocal()

awg.close()
scope.shutdown()