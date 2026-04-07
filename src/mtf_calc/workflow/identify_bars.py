from uuid import uuid4
import numpy as np
from pydantic import BaseModel
from agents import Agent, Runner, ModelSettings, SQLiteSession
from openai.types.shared import Reasoning

from mtf_calc.tools.images import image_display, to_base64_png, render_image
from mtf_calc.workflow.identify_scale import ScaleResult

PROMPT = """\
You are visually locating every bar pattern set on a USAF 1951 resolution test chart image.

The image is saved as `input.npy` in your working directory.

## What you know

You are given:
- The reference square's group number
- The image dimensions

## Your task

Look at the image and find every set of three bars. For each one, report:
- Which **group** and **element** it belongs to
- Whether the bars are **horizontal** or **vertical**
- An approximate **center point** (x, y) in pixel coordinates — just a point somewhere \
  on the bars, it does not need to be precise

## How to identify groups and elements

The USAF 1951 chart has **group numbers and element numbers printed directly on it**. \
Read them. That is the primary identification method.

Use these layout rules to resolve any ambiguity:

- **Even-numbered groups** (0, 2, 4, ...): bars are on the LEFT side of their region. \
  The group number is printed above element 1. Horizontal bars are on the left, \
  vertical bars to their right.
- **Odd-numbered groups** (1, 3, 5, ...): bars are on the RIGHT side / upper-right. \
  Vertical bars are on the right, horizontal bars to their left.
- Groups are arranged in pairs that spiral inward: largest groups outermost, smallest \
  innermost.
- Within each group, elements 1–6 go from largest bars to smallest.
- Each element has exactly TWO bar sets: one horizontal, one vertical.

## Gridlines

The image has semi-transparent blue gridlines overlaid at regular pixel intervals, \
with pixel coordinates labeled along the top and left edges. Use these gridlines to \
estimate center points accurately — count grid squares and interpolate.

## Workflow

1. Start by looking at the full image to get oriented. Read the printed group numbers \
   to understand which groups are visible. Note the gridline spacing.
2. Work through each visible group. Use `render_image` with crop params to zoom in \
   if needed for smaller/denser groups.
3. For each bar set you can see, note its group, element, orientation, and drop a \
   center point on it.
4. Skip any bars that are too small to visually distinguish — if you can't see \
   individual bars, don't report it.

Do NOT try to measure bar widths or compute expected pixel sizes. Just read the \
numbers on the chart and use the layout rules.\
"""


class BarSetLocation(BaseModel):
    group: int
    element: int
    orientation: str  # "horizontal" or "vertical"
    center_x: float
    center_y: float


class BarIdentificationResult(BaseModel):
    bar_sets: list[BarSetLocation]


identify_bars_agent = Agent(
    name="identify_bars",
    instructions=PROMPT,
    model="gpt-5.4",
    model_settings=ModelSettings(reasoning=Reasoning(effort="high")),
    tools=[render_image],
    output_type=BarIdentificationResult,
)


def main(data: np.ndarray, scale: ScaleResult) -> BarIdentificationResult:
    print("Running stage 2: identify_bars")

    # Choose gridline spacing: ~10 lines across the shorter dimension
    grid_spacing = max(50, min(data.shape) // 10)
    grid_spacing = round(grid_spacing / 50) * 50  # snap to nearest 50
    base64_image = to_base64_png(data, gridline_spacing=grid_spacing)
    h, w = data.shape

    context = (
        f"Reference square group: {scale.group_number}\n"
        f"Image dimensions: {w} × {h} pixels\n"
        f"Gridline spacing: {grid_spacing} pixels"
    )

    session_id = f"identify_bars_{uuid4().hex}"
    session = SQLiteSession(session_id, db_path=".data.db")

    result = Runner.run_sync(
        identify_bars_agent,
        max_turns=30,
        session=session,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Locate all visible bar pattern sets.\n\n{context}",
                    },
                    {
                        "type": "input_image",
                        "detail": "original",
                        "image_url": f"data:image/png;base64,{base64_image}",
                    },
                ],
            }
        ],
    )

    bars = result.final_output
    print(f"Bar sets found: {len(bars.bar_sets)}")
    for bs in bars.bar_sets:
        freq = 2 ** (bs.group + (bs.element - 1) / 6)
        print(f"  G{bs.group}E{bs.element} {bs.orientation:10s} "
              f"{freq:.2f} lp/mm  "
              f"center=({bs.center_x:.0f}, {bs.center_y:.0f})")
    print(f"  Completed session ID: {session_id}")

    image_display.show(
        data,
        title="Identified bar sets",
        points=[(bs.center_x, bs.center_y) for bs in bars.bar_sets],
    )

    return bars
