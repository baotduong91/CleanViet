"""Build the existing React frontend for the native FastAPI deployment."""

from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
subprocess.run(["npm", "ci", "--prefix", "frontend"], cwd=root, check=True)
subprocess.run(["npm", "run", "build", "--prefix", "frontend"], cwd=root, check=True)
if not (root / "frontend/dist/index.html").is_file():
    raise RuntimeError("The frontend build did not produce index.html")
