import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(HERE / "build_25cat_library.py"), "--github-only"], check=True)
