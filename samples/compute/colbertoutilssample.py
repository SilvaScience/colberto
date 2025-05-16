from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute import colbertoutils as co
wavelength=532e-9
print('Wavelength of %.2e m is %.2e eV, %.2e Hz and %.2e rad.Hz'%(wavelength,co.waveToeV(wavelength),co.waveToFreq(wavelength),co.waveToAngFreq(wavelength)))
angFreq=3.54e15
print('Angular frequency of %.2e rad.Hz is wavelenght of %.2e m'%(angFreq,co.angFreqToWave(angFreq)))