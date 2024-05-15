
from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.calibration import Calibration
from src.compute.SLMBogus import SLM 


slm=SLM(600,300)
print('Widht: %d and heigth %d of SLM '%(slm.width,slm.height))
cal=Calibration(slm)

