import subprocess
import sys
from pathlib import Path

from agents import function_tool

WORKDIR = Path(".mtf-calc/find_anchors")


@function_tool
def run_python(code: str) -> str:
    """Execute a Python script. The working directory contains `input.npy` (a float32 2D grayscale image, values 0-1). numpy, PIL, and scipy are available. Print your results to stdout."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=WORKDIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += "\n[stderr]\n" + result.stderr
    return output.strip() or "(no output)"
