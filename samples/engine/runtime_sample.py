from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.engine.runtime import Runtime 

engine=Runtime()
engine.catalog