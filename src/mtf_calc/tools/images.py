import base64
import io

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from agents import function_tool, ToolOutputImage

from mtf_calc.tools.shell import WORKDIR


class ImageDisplay:
    is_headless: bool = False

    def show(
        self,
        img: np.ndarray,
        title: str = "",
        polygons: list[list[tuple[float, float]]] | None = None,
        points: list[tuple[float, float]] | None = None,
        lines: list[tuple[tuple[float, float], tuple[float, float]]] | None = None,
        polygon_color: str = "red",
        point_color: str = "lime",
        line_color: str = "cyan",
        point_size: float = 80,
    ) -> None:
        """Display a float32 grayscale image with annotations.

        Args:
            img: 2D float32 array (0-1).
            title: Plot title.
            polygons: List of closed polygons, each a list of (x, y) vertices.
            points: List of (x, y) points to mark.
            lines: List of ((x1, y1), (x2, y2)) line segments.
            polygon_color: Edge color for polygons.
            point_color: Color for points.
            line_color: Color for lines.
            point_size: Marker size for points.
        """
        from matplotlib.patches import Polygon

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(img, cmap="gray", vmin=0, vmax=1)

        if polygons:
            for verts in polygons:
                ax.add_patch(Polygon(verts, closed=True, linewidth=2, edgecolor=polygon_color, facecolor="none"))

        if lines:
            for (x1, y1), (x2, y2) in lines:
                ax.plot([x1, x2], [y1, y2], color=line_color, linewidth=2)

        if points:
            xs, ys = zip(*points)
            ax.scatter(xs, ys, s=point_size, c=point_color, marker="+", linewidths=2, zorder=5)

        if title:
            ax.set_title(title)
        plt.colorbar(ax.images[0], ax=ax)
        plt.tight_layout()

        # Always save a PNG
        slug = title.replace(" ", "_").lower() if title else "figure"
        filename = f"{slug}.png"
        fig.savefig(filename, dpi=150)
        print(f"Saved {filename}")

        if self.is_headless:
            plt.close(fig)
        else:
            plt.show()

    def set_headless(self, is_headless: bool) -> None:
        self.is_headless = is_headless

image_display = ImageDisplay()


def to_base64_png(
    img: np.ndarray,
    bbox: tuple[int, int, int, int] | None = None,
    gridline_spacing: int | None = None,
) -> str:
    """Convert a float32 grayscale array to a base64-encoded PNG string."""
    uint8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    pil_img = Image.fromarray(uint8, mode="L").convert("RGB")

    if bbox is not None:
        x, y, w, h = bbox
        draw = ImageDraw.Draw(pil_img)
        draw.rectangle([x, y, x + w, y + h], outline="red", width=8)

    if gridline_spacing is not None:
        pil_img = draw_gridlines(pil_img, spacing=gridline_spacing)

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def draw_gridlines(
    pil_img: Image.Image,
    spacing: int = 100,
    color: tuple[int, int, int] = (0, 120, 255),
    opacity: int = 80,
    label_every: int = 1,
) -> Image.Image:
    """Draw gridlines with pixel-coordinate labels onto an RGB PIL image.

    Args:
        pil_img: RGB PIL image (modified in place and returned).
        spacing: Pixel spacing between gridlines.
        color: RGB color for the gridlines.
        opacity: Alpha value (0-255) for gridline blending.
        label_every: Label every Nth gridline (1 = all).

    Returns:
        The image with gridlines composited on top.
    """
    overlay = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = pil_img.size
    line_color = (*color, opacity)
    label_color = (*color, min(opacity + 80, 255))

    idx = 0
    for x in range(0, w, spacing):
        draw.line([(x, 0), (x, h)], fill=line_color, width=1)
        if idx % label_every == 0:
            draw.text((x + 2, 2), str(x), fill=label_color)
        idx += 1

    idx = 0
    for y in range(0, h, spacing):
        draw.line([(0, y), (w, y)], fill=line_color, width=1)
        if idx % label_every == 0:
            draw.text((2, y + 2), str(y), fill=label_color)
        idx += 1

    pil_img = pil_img.convert("RGBA")
    pil_img = Image.alpha_composite(pil_img, overlay)
    return pil_img.convert("RGB")


@function_tool
def render_image(
    filename: str,
    bbox_x1: float | None = None,
    bbox_y1: float | None = None,
    bbox_x2: float | None = None,
    bbox_y2: float | None = None,
    bbox_x3: float | None = None,
    bbox_y3: float | None = None,
    bbox_x4: float | None = None,
    bbox_y4: float | None = None,
    crop_top: int = 0,
    crop_bottom: int = 0,
    crop_left: int = 0,
    crop_right: int = 0,
) -> ToolOutputImage:
    """Render a .npy image file from the working directory as a base64 PNG.

    Args:
        filename: Name of the .npy file in the working directory (e.g. 'input.npy' or 'roi.npy').
        bbox_x1: X of first corner (top-left for axis-aligned box, or first vertex of quadrilateral).
        bbox_y1: Y of first corner.
        bbox_x2: X of second corner (bottom-right for 2-point box, or second vertex of quadrilateral).
        bbox_y2: Y of second corner.
        bbox_x3: X of third vertex (only for quadrilateral, omit for axis-aligned box).
        bbox_y3: Y of third vertex.
        bbox_x4: X of fourth vertex (only for quadrilateral, omit for axis-aligned box).
        bbox_y4: Y of fourth vertex.
        crop_top: Number of pixels to crop from the top before display.
        crop_bottom: Number of pixels to crop from the bottom before display.
        crop_left: Number of pixels to crop from the left before display.
        crop_right: Number of pixels to crop from the right before display.
    """
    img = np.load(WORKDIR / filename)

    # Apply crop
    h, w = img.shape
    t, b, l, r = crop_top, crop_bottom, crop_left, crop_right
    img = img[t : h - b if b else h, l : w - r if r else w]
    # Offset for bbox coordinates after crop
    ox, oy = -l, -t

    uint8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    pil_img = Image.fromarray(uint8, mode="L").convert("RGB")

    # Draw bounding box if coordinates provided
    if bbox_x1 is not None and bbox_y1 is not None and bbox_x2 is not None and bbox_y2 is not None:
        draw = ImageDraw.Draw(pil_img)
        if bbox_x3 is not None and bbox_y3 is not None and bbox_x4 is not None and bbox_y4 is not None:
            # 4-point quadrilateral
            pts = [
                (bbox_x1 + ox, bbox_y1 + oy),
                (bbox_x2 + ox, bbox_y2 + oy),
                (bbox_x3 + ox, bbox_y3 + oy),
                (bbox_x4 + ox, bbox_y4 + oy),
            ]
            for i in range(4):
                draw.line([pts[i], pts[(i + 1) % 4]], fill="red", width=3)
        else:
            # 2-point axis-aligned rectangle (top-left, bottom-right)
            draw.rectangle(
                [bbox_x1 + ox, bbox_y1 + oy, bbox_x2 + ox, bbox_y2 + oy],
                outline="red", width=3,
            )

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")

    return ToolOutputImage(image_url=f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}")
