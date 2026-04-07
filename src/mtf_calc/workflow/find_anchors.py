import numpy as np
from pydantic import BaseModel
from scipy import ndimage

from mtf_calc.tools.images import image_display


class Point(BaseModel):
    x: float
    y: float

class AnchorResult(BaseModel):
    center_x: float
    center_y: float
    angle_deg: float
    edge_length_px: float
    corners: list[Point]


def _find_large_square(data: np.ndarray) -> tuple[int, int, int, int]:
    """Find the bounding box of the largest square-ish dark blob."""
    mask = data < 0.2
    labels, n = ndimage.label(mask)
    objs = ndimage.find_objects(labels)

    best = None
    best_area = 0
    for i, slc in enumerate(objs, 1):
        if slc is None:
            continue
        h = slc[0].stop - slc[0].start
        w = slc[1].stop - slc[1].start
        area = int(np.sum(labels[slc] == i))
        aspect = min(h, w) / max(h, w)
        # Must be roughly square and filled
        if aspect > 0.8 and area > best_area and area / (h * w) > 0.8:
            best_area = area
            best = (slc[1].start, slc[0].start, slc[1].stop, slc[0].stop)

    if best is None:
        raise RuntimeError("Could not find a reference square in the image")
    return best


def _refine_anchor(data: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> AnchorResult:
    """Deterministic edge detection + line fitting on a known bbox."""
    margin = 25
    ry1 = max(0, y1 - margin)
    ry2 = min(data.shape[0] - 1, y2 + margin)
    rx1 = max(0, x1 - margin)
    rx2 = min(data.shape[1] - 1, x2 + margin)
    roi = data[ry1:ry2 + 1, rx1:rx2 + 1]

    # Sobel edge detection
    sm = ndimage.gaussian_filter(roi, 1.0)
    gx = ndimage.sobel(sm, axis=1)  # horizontal gradient
    gy = ndimage.sobel(sm, axis=0)  # vertical gradient
    mag = np.sqrt(gx**2 + gy**2)

    # Threshold edges
    thr = 0.15
    edge_mask = mag > thr

    # Classify edges by gradient direction
    ey, ex = np.where(edge_mask)
    gx_vals = gx[ey, ex]
    gy_vals = gy[ey, ex]

    roi_cy = roi.shape[0] / 2
    roi_cx = roi.shape[1] / 2

    # Horizontal edges (strong vertical gradient)
    h_mask = np.abs(gy_vals) > np.abs(gx_vals)
    h_x, h_y = ex[h_mask], ey[h_mask]
    top_mask = h_y < roi_cy
    bot_mask = h_y >= roi_cy

    # Vertical edges (strong horizontal gradient)
    v_mask = ~h_mask
    v_x, v_y = ex[v_mask], ey[v_mask]
    left_mask = v_x < roi_cx
    right_mask = v_x >= roi_cx

    # Fit lines
    # Horizontal edges: y = a*x + b
    top_p = np.polyfit(h_x[top_mask], h_y[top_mask], 1)
    bot_p = np.polyfit(h_x[bot_mask], h_y[bot_mask], 1)
    # Vertical edges: x = c*y + d
    left_p = np.polyfit(v_y[left_mask], v_x[left_mask], 1)
    right_p = np.polyfit(v_y[right_mask], v_x[right_mask], 1)

    # Intersect adjacent lines to get corners (in ROI coords)
    def intersect_hv(h_coeffs, v_coeffs):
        """Intersect y=a*x+b with x=c*y+d."""
        a, b = h_coeffs
        c, d = v_coeffs
        # y = a*x + b, x = c*y + d → x = c*(a*x+b) + d = c*a*x + c*b + d
        # x(1 - c*a) = c*b + d → x = (c*b + d) / (1 - c*a)
        x = (c * b + d) / (1 - c * a)
        y = a * x + b
        return x, y

    tl = intersect_hv(top_p, left_p)
    tr = intersect_hv(top_p, right_p)
    br = intersect_hv(bot_p, right_p)
    bl = intersect_hv(bot_p, left_p)

    # Convert to full image coordinates
    corners = [
        Point(x=tl[0] + rx1, y=tl[1] + ry1),
        Point(x=tr[0] + rx1, y=tr[1] + ry1),
        Point(x=br[0] + rx1, y=br[1] + ry1),
        Point(x=bl[0] + rx1, y=bl[1] + ry1),
    ]

    center_x = np.mean([c.x for c in corners])
    center_y = np.mean([c.y for c in corners])

    # Edge lengths
    def dist(p1, p2):
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    edge_length = np.mean([
        dist(corners[0], corners[1]),
        dist(corners[1], corners[2]),
        dist(corners[2], corners[3]),
        dist(corners[3], corners[0]),
    ])

    # Angle from horizontal edges
    angle_top = np.degrees(np.arctan(top_p[0]))
    angle_bot = np.degrees(np.arctan(bot_p[0]))
    angle_deg = (angle_top + angle_bot) / 2

    return AnchorResult(
        center_x=float(center_x),
        center_y=float(center_y),
        angle_deg=float(angle_deg),
        edge_length_px=float(edge_length),
        corners=corners,
    )


def main(data: np.ndarray) -> AnchorResult:
    print("Running stage 0: find_anchors")

    x1, y1, x2, y2 = _find_large_square(data)
    print(f"  Bbox: ({x1}, {y1}) → ({x2}, {y2})")

    anchor = _refine_anchor(data, x1, y1, x2, y2)
    print(f"Anchor result:")
    print(f"  Center: ({anchor.center_x:.1f}, {anchor.center_y:.1f})")
    print(f"  Angle: {anchor.angle_deg:.3f}°")
    print(f"  Edge length: {anchor.edge_length_px:.1f} px")
    print(f"  Corners: {anchor.corners}")

    image_display.show(
        data,
        title="Anchor detection result",
        polygons=[[(c.x, c.y) for c in anchor.corners]],
        points=[(anchor.center_x, anchor.center_y)],
    )
    return anchor
