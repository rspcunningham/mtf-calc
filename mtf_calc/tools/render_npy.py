"""Render a .npy float32 grayscale array to PNG, with optional overlays."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def render(
    array: np.ndarray,
    overlay: dict | None = None,
) -> Image.Image:
    img = Image.fromarray((array * 255).clip(0, 255).astype(np.uint8), mode="L")
    img = img.convert("RGB")

    if overlay:
        draw = ImageDraw.Draw(img)
        for x1, y1, x2, y2 in overlay.get("boxes", []):
            draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
        for x1, y1, x2, y2 in overlay.get("lines", []):
            draw.line([x1, y1, x2, y2], fill="lime", width=2)
        for x, y in overlay.get("points", []):
            r = 4
            draw.ellipse([x - r, y - r, x + r, y + r], fill="cyan")

    return img


def main() -> None:
    parser = argparse.ArgumentParser(description="Render .npy to PNG")
    parser.add_argument("input", help="Path to .npy file")
    parser.add_argument("-o", "--output", help="Output PNG path (default: <input>.png)")
    parser.add_argument(
        "--overlay",
        help='JSON overlay: {"boxes":[[x1,y1,x2,y2],...], "lines":[[x1,y1,x2,y2],...], "points":[[x,y],...]}',
    )
    args = parser.parse_args()

    array = np.load(args.input, allow_pickle=False)
    if array.ndim != 2 or array.dtype != np.float32:
        print(f"Error: expected 2D float32 array, got shape={array.shape} dtype={array.dtype}", file=sys.stderr)
        sys.exit(1)

    overlay = json.loads(args.overlay) if args.overlay else None
    out_path = args.output or str(Path(args.input).with_suffix(".png"))

    img = render(array, overlay)
    img.save(out_path)
    print(json.dumps({"path": out_path, "width": img.width, "height": img.height}))


if __name__ == "__main__":
    main()
