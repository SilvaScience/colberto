from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration
from src.compute.SLMBogus import SLM 
from matplotlib import pyplot as plt
from scipy.constants import pi


slm=SLM(600,300)
print('Widht: %d and heigth %d of SLM '%(slm.width,slm.height))
cal=Calibration(slm)
bm=Beam(cal)
bm.set_compressionCarrierWave(532e-9)
print('Compression carrier wavelenght is %.2e'%bm.get_compressionCarrierWave())

plt.figure()
amplitude=1
period=10
num=100
plt.plot(bm.generate_1Dgrating(amplitude,period,0,num),'s',label='0')
plt.plot(bm.generate_1Dgrating(amplitude,period,pi,num),'s',label='Pi')
plt.ylabel('Phase (rad.)')
plt.xlabel('Pixel index')

plt.show()