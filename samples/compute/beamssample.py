from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration
from src.compute.SLMBogus import SLM 
from matplotlib import pyplot as plt
from scipy.constants import pi
from numpy.polynomial import Polynomial as P
import numpy as np

'''
A snippet of code demonstrating how to use some of the features in the Beams class
'''

slm=SLM(600,300)
print('Widht: %d and heigth %d of SLM '%(slm.get_size()))
cal=Calibration(slm)# Initialize calibration with SLM object
pix2wave=P(1e-9*np.array([500,1/6]))# Sets bogus polynomial for pix to wave conversion
cal.set_pixelToWavelength(pix2wave)
bm=Beam(cal)
bm.set_compressionCarrierWave(532e-9)
print('Compression carrier wavelenght is %.2e nm'%bm.get_compressionCarrier(unit='wavelength'))
print('Compression carrier angular frequency is %.2e rad.Hz'%bm.get_compressionCarrier(unit='ang_frequency'))
bm.set_optimalPhase(P([0,0,1000,500]))
bm.set_currentPhase(P([0,100,500]),mode='relative')
bm.set_beamVerticalDelimiters([100,250])

print('Optimal phase is now:')
print(bm.get_optimalPhase())
plt.figure()
plt.plot(bm.get_horizontalIndices(),bm.get_sampledCurrentPhase())
plt.xlabel('Pixel column index')
plt.ylabel('Phase (rad)')
print('Current phase is (relative):')
print(bm.get_currentPhase(mode='relative'))
print('Current phase is (absolute):')
print(bm.get_currentPhase(mode='absolute'))
amplitude=1
bm.set_gratingAmplitude(amplitude)
print('Current amplitude (units of 2*pi) is %.2f'%bm.get_gratingAmplitude())
period=10
bm.set_gratingPeriod(period)
print('Current grating period is %d pixels'%bm.get_gratingPeriod())
plt.figure()
num=100
plt.plot(bm.generate_1Dgrating(amplitude,period,0,num),'s',label='0')
plt.plot(bm.generate_1Dgrating(amplitude,period,pi,num),'s',label='Pi')
plt.ylabel('Phase (rad.)')
plt.xlabel('Pixel index')

plt.figure()
plt.imshow(bm.makeGrating())

# Here is how to constraint the horizontal extent of the pattern
mask=np.zeros(slm.get_size()[0])
mask[325:330]=1
bm.set_gratingAmplitudeMask(mask)
bm.set_maskStatus(True)
plt.figure()
plt.plot(mask)
plt.figure()
plt.imshow(bm.makeGrating())



plt.show()