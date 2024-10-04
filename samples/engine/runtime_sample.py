from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.engine import runtime as rt

try:
    rt.setup_bluesky()
except Exception as e:
    print(e)
    print('Setup Failed')
