# apps/worker package
import sys
from pathlib import Path

# Automatically ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
