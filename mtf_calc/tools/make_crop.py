"""Crop a region from a .npy array and save as a new .npy file."""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop a .npy array")
    parser.add_argument("input", help="Path to .npy file")
    parser.add_argument("output", help="Output .npy path")
    parser.add_argument("--bbox", required=True, help="Bounding box as x1,y1,x2,y2 (col,row,col,row)")
    args = parser.parse_args()

    array = np.load(args.input, allow_pickle=False)
    if array.ndim != 2:
        print(f"Error: expected 2D array, got shape={array.shape}", file=sys.stderr)
        sys.exit(1)

    x1, y1, x2, y2 = (int(v) for v in args.bbox.split(","))
    # bbox is col,row,col,row — slice as array[y1:y2, x1:x2]
    crop = array[y1:y2, x1:x2].copy()
    np.save(args.output, crop)

    print(json.dumps({
        "path": args.output,
        "shape": list(crop.shape),
        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
    }))


if __name__ == "__main__":
    main()
