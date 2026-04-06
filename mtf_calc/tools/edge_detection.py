"""Run edge detection on a .npy array and return detected edge lines."""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
from scipy import ndimage


def detect_edges(array: np.ndarray, threshold: float) -> dict:
    """Find strong edges and fit lines to horizontal/vertical clusters.

    Returns overlay-compatible dict with "lines" and "points" (corners).
    """
    rows, cols = array.shape

    # Sobel gradients
    gy = ndimage.sobel(array, axis=0)
    gx = ndimage.sobel(array, axis=1)
    mag = np.hypot(gx, gy)

    # Threshold
    mask = mag > threshold

    # Separate into roughly horizontal and roughly vertical edges
    angle = np.arctan2(np.abs(gy), np.abs(gx))
    h_mask = mask & (angle > np.pi / 4)  # gradient mostly vertical → horizontal edge
    v_mask = mask & (angle <= np.pi / 4)  # gradient mostly horizontal → vertical edge

    lines = []
    edge_rows = []
    edge_cols = []

    # Cluster horizontal edges by row coordinate
    h_coords = np.argwhere(h_mask)  # (row, col)
    if len(h_coords) > 0:
        h_rows = h_coords[:, 0]
        clusters = _cluster_1d(h_rows, gap=max(5, rows // 100))
        for cluster_indices in clusters:
            pts = h_coords[cluster_indices]
            mean_row = float(pts[:, 0].mean())
            min_col = int(pts[:, 1].min())
            max_col = int(pts[:, 1].max())
            lines.append([min_col, round(mean_row), max_col, round(mean_row)])
            edge_rows.append(mean_row)

    # Cluster vertical edges by col coordinate
    v_coords = np.argwhere(v_mask)
    if len(v_coords) > 0:
        v_cols = v_coords[:, 1]
        clusters = _cluster_1d(v_cols, gap=max(5, cols // 100))
        for cluster_indices in clusters:
            pts = v_coords[cluster_indices]
            mean_col = float(pts[:, 1].mean())
            min_row = int(pts[:, 0].min())
            max_row = int(pts[:, 0].max())
            lines.append([round(mean_col), min_row, round(mean_col), max_row])
            edge_cols.append(mean_col)

    # Compute corner intersections
    points = []
    for r in edge_rows:
        for c in edge_cols:
            points.append([round(c), round(r)])

    return {
        "lines": lines,
        "points": points,
        "edge_rows": [round(r, 2) for r in sorted(edge_rows)],
        "edge_cols": [round(c, 2) for c in sorted(edge_cols)],
    }


def _cluster_1d(values: np.ndarray, gap: int) -> list[np.ndarray]:
    """Group sorted values into clusters separated by at least `gap`."""
    order = np.argsort(values)
    sorted_vals = values[order]
    splits = np.where(np.diff(sorted_vals) > gap)[0] + 1
    groups = np.split(order, splits)
    return [g for g in groups if len(g) > 10]  # drop tiny clusters


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge detection on .npy array")
    parser.add_argument("input", help="Path to .npy file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Gradient magnitude threshold (default: 0.1)",
    )
    args = parser.parse_args()

    array = np.load(args.input, allow_pickle=False)
    if array.ndim != 2:
        print(f"Error: expected 2D array, got shape={array.shape}", file=sys.stderr)
        sys.exit(1)

    result = detect_edges(array, args.threshold)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
