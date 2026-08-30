from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration
from matplotlib import pyplot as plt
from scipy.constants import pi
from numpy.polynomial import Polynomial as P
import numpy as np

'''
A snippet of code demonstrating how to use some of the features in the Beams class
'''

bm=Beam(1920,1200)
bm.set_pixelToWavelength(P(1e-9*np.array([500,1/6])))# Sets bogus polynomial for pix to wave conversionpix2wave
bm.set_compressionCarrierWave(650e-9)
bm.set_delayCarrierWave(625e-9)
print('Wavelength at pixel 111:  %.3e m'%bm.get_spectrumAtPixel(111))
print('Frequency at pixel 111:  %.3e Hz'%bm.get_spectrumAtPixel(111,unit='frequency'))
print('Frequency at pixel 111:  %.3e PHz'%bm.get_spectrumAtPixel(111,unit='frequencyPHz'))
print('Angular frequency at pixel 111:  %.3e rad Hz'%bm.get_spectrumAtPixel(111,unit='ang_frequency'))
print('Angular frequency at pixel 111:  %.3e rad PHz'%bm.get_spectrumAtPixel(111,unit='ang_frequencyPHz'))
print('Energy at pixel 111:  %.3e eV'%bm.get_spectrumAtPixel(111,unit='energy'))
print('Compression carrier wavelenght is %.2e m'%bm.get_compressionCarrier(unit='wavelength'))
print('Compression carrier angular frequency is %.2e rad.Hz'%bm.get_compressionCarrier(unit='ang_frequency'))
print('Compression carrier angular frequency is %.2e rad.PHz'%bm.get_compressionCarrier(unit='ang_frequencyPHz'))
print('Delay carrier wavelenght is %.2e m'%bm.get_delayCarrier(unit='wavelength'))
print('Delay carrier angular frequency is %.2e rad.Hz'%bm.get_delayCarrier(unit='ang_frequency'))
print('Delay carrier angular frequency is %.2e rad.PHz'%bm.get_delayCarrier(unit='ang_frequencyPHz'))
bm.set_optimalPhase(P([0,0,1000,000]))
bm.set_currentPhase(P([0,00,500,-000]),mode='relative')
bm.set_beamVerticalDelimiters([200,1000])

print('Optimal phase is now:')
print(bm.get_optimalPhase(units_to_return='fs'))
plt.figure()
plt.title('Example of phase profile vs Column index')
plt.plot(bm.get_horizontalIndices(),bm.get_sampledCurrentPhase()/(2*np.pi))
plt.xlabel('Pixel column index')
plt.ylabel('Phase (rad)')
print('Current phase is (relative):')
print(bm.get_currentPhase(mode='relative'))
print('Current phase is (absolute):')
print(bm.get_currentPhase(mode='absolute'))
amplitude=1
bm.set_gratingAmplitude(amplitude)
print('Current amplitude (units of 2*pi) is %.2f'%bm.get_gratingAmplitude())
period=100
bm.set_gratingPeriod(period)
print('Current grating period is %d pixels'%bm.get_gratingPeriod())
plt.figure()
num=100
plt.plot(bm.generate_1Dgrating(amplitude,period,0,num),'s',label='0')
plt.plot(bm.generate_1Dgrating(amplitude,period,pi,num),'s',label='Pi')
plt.ylabel('Phase (rad.)')
plt.xlabel('Pixel index')
plt.legend()
plt.title('1D grating examples')

plt.figure()
plt.title('Phase grating')
plt.imshow(bm.makeGrating())

# Here is how to constraint the horizontal extent of the pattern
bm.set_maskStatus(True)
mask,isMaskOn=bm.get_mask()
plt.figure()
plt.title('Phase grating with mask (Mask is %s)'%'On' if isMaskOn else 'Off')
plt.imshow(bm.makeGrating(horizontalDelimiters=[325,400]))
plt.figure()
mask,isMaskOn=bm.get_mask()
plt.title('Amplitude mask profile is %s'% 'On' if isMaskOn else 'Off')
plt.imshow(mask)

bm.set_maskStatus(False)
plt.figure()
mask,isMaskOn=bm.get_mask()
plt.title('Amplitude mask profile is %s'% 'On' if isMaskOn else 'Off')
plt.imshow(mask)
plt.figure()
plt.title('Phase grating with mask (Mask is %s)'%'On' if isMaskOn else 'Off')
plt.imshow(bm.makeGrating(horizontalDelimiters=[325,400]))


plt.show(block=True)