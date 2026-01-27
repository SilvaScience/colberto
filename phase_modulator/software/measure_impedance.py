import numpy as np
from awg_scpi import AWG
from time import sleep
from pymeasure.instruments.keysight import KeysightDSOX1102G
from matplotlib import pyplot as plt
import argparse
parser = argparse.ArgumentParser(description='Access and control an AWG')
parser.add_argument('chan', nargs='?', type=int, help='Channel to access/control (starts at 1)', default=1)
args = parser.parse_args()

from os import environ
resource = environ.get('AWG_IP', 'TCPIP::192.168.1.127::INSTR')
awg = AWG(resource)
scope = KeysightDSOX1102G('TCPIP::192.168.1.126::INSTR')
scope.autoscale()
ch1_data_array, ch1_preamble = scope.download_data(source="channel1", points=2000)
plt.figure()
plt.plot(ch1_data_array)
plt.show()
## Upgrade Object to best match based on IDN string
awg = awg.getBestClass()

## Open this object and work with it
awg.open()

print('Using SCPI Device:     ' + awg.idn() + ' of series: ' + awg.series + '\n')

# set the channel (can pass channel to each method or just set it
# once and it becomes the default for all following calls)
awg.channel = str(args.chan)
if awg.isOutputHiZ(awg.channel):
    print("Output High Impedance")
else:
    print("Output 50 ohm load")

awg.beeperOn()

# return to default parameters
awg.reset()               

awg.setWaveType('SINE')
awg.setFrequency(34.4590897823e3)
awg.setVoltageProtection(6.6)
awg.setAmplitude(3.2)
awg.setOffset(1.6)
awg.setPhase(0.45)

print("Voltage Protection is set to maximum: {}V Amplitude (assumes 0V offset)".format(awg.queryVoltageProtection()))

# turn on the channel
awg.outputOn()

# return to LOCAL mode
awg.setLocal()

awg.close()
scope.shutdown()