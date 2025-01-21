from pathlib import Path
import sys



sys.path.append(str(Path(__file__).resolve().parent.parent.parent)) #add or remove parent based on the file location
from src.drivers.Slm_Meadowlark_optics import SLM
from src.drivers.Slm_Meadowlark_optics import ImageGen

# Initiate the SLM class
slm = SLM()
Image=ImageGen()


slm.create_sdk()
print("Blink SDK was successfully constructed")


height ,width, depth,RGB, isEightBitImage = slm.parameter_slm()
print("height:",height,"width:",width,"depth:",depth,"is8bit:",isEightBitImage)

slm.load_lut("c:\Program Files\Meadowlark Optics\Blink 1920 HDMI\LUT Files\19x12_8bit_linearVoltage.lut");

slm.write_image(image, isEightBitImage)

slm.delete_sdk()