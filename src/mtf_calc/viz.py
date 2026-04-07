import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from mtf_calc.models import Anchor, MtfResult


def show_anchor(raw_image: NDArray[np.float32], anchor: Anchor) -> None:
    corners = (
        anchor.roi.top_left,
        anchor.roi.top_right,
        anchor.roi.bottom_right,
        anchor.roi.bottom_left,
        anchor.roi.top_left,
    )
    x_coords = [point.x for point in corners]
    y_coords = [point.y for point in corners]
    centroid = anchor.centroid

    _, ax = plt.subplots()  # pyright: ignore[reportUnknownMemberType]
    _ = ax.imshow(raw_image, cmap="gray", origin="upper")  # pyright: ignore[reportUnknownMemberType]
    _ = ax.plot(x_coords, y_coords, color="tab:red", linewidth=2)  # pyright: ignore[reportUnknownMemberType]
    _ = ax.scatter(  # pyright: ignore[reportUnknownMemberType]
        [centroid.x],
        [centroid.y],
        color="tab:cyan",
        s=48,
        zorder=3,
    )
    _ = ax.set_title("Anchor ROI")  # pyright: ignore[reportUnknownMemberType]
    ax.set_axis_off()
    plt.show()  # pyright: ignore[reportUnknownMemberType]


def show_mtf_graph(mtf_result: MtfResult) -> None:
    del mtf_result
    raise NotImplementedError
