"""Launch Claude Code as a subprocess to detect the anchor point in a USAF 1951 target."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


PROMPT_FILE = Path(__file__).parent / "anchor_prompt.md"

CLAUDE_BIN = "claude"

# The CLI tools (render-npy, make-crop, edge-detect) live in the same venv bin dir
VENV_BIN = str(Path(sys.executable).parent)


@dataclass(slots=True)
class AnchorResult:
    center_x: float
    center_y: float
    angle_deg: float
    edge_length_px: float
    corners: list[list[float]]


def detect_anchor(npy_path: str | Path, verbose: bool = False) -> AnchorResult:
    """Run anchor detection on a .npy image. Returns the detected anchor point."""
    npy_path = Path(npy_path).resolve()
    if not npy_path.exists():
        raise FileNotFoundError(f"Input file not found: {npy_path}")

    instructions = PROMPT_FILE.read_text()

    workdir = Path(tempfile.mkdtemp(prefix="parasight-anchor-"))
    try:
        input_copy = workdir / "input.npy"
        shutil.copy2(npy_path, input_copy)

        # Everything goes in the user message — instructions + the task
        user_prompt = f"{instructions}\n\n---\n\nThe input image is at: {input_copy}\n\nFind the anchor point."

        env = os.environ.copy()
        env["PATH"] = VENV_BIN + os.pathsep + env.get("PATH", "")

        cmd = [
            CLAUDE_BIN,
            "-p", user_prompt,
            "--output-format", "text",
            "--dangerously-skip-permissions",
            "--model", "sonnet",
            "--max-budget-usd", "1.00",
            "--no-session-persistence",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(workdir),
            env=env,
            timeout=600,
        )

        if verbose:
            print(result.stdout)

        if result.returncode != 0:
            raise RuntimeError(
                f"Claude exited with code {result.returncode}\n"
                f"stderr: {result.stderr[:2000]}\n"
                f"stdout: {result.stdout[:2000]}"
            )

        # Parse RESULT: line from output
        for line in result.stdout.splitlines():
            if line.strip().startswith("RESULT:"):
                json_str = line.strip().removeprefix("RESULT:").strip()
                data = json.loads(json_str)
                return AnchorResult(
                    center_x=float(data["center_x"]),
                    center_y=float(data["center_y"]),
                    angle_deg=float(data["angle_deg"]),
                    edge_length_px=float(data["edge_length_px"]),
                    corners=data["corners"],
                )

        raise RuntimeError(
            f"No RESULT: line found in Claude output.\n"
            f"Full output:\n{result.stdout[:5000]}"
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
