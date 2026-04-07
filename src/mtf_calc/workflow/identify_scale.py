import numpy as np
from pydantic import BaseModel
from agents import Agent, Runner, ModelSettings
from openai.types.shared import Reasoning

from mtf_calc.tools.images import to_base64_png
from mtf_calc.workflow.find_anchors import AnchorResult

# Precomputed from USAF 1951 spec: square_edge = 5000 / (2 * 2^(group + 1/6))
SQUARE_EDGE_UM = {
    -2: 5000 / (2 * 2**(-2 + 1/6)),
    0:  5000 / (2 * 2**(0 + 1/6)),
    2:  5000 / (2 * 2**(2 + 1/6)),
    4:  5000 / (2 * 2**(4 + 1/6)),
    6:  5000 / (2 * 2**(6 + 1/6)),
}

PROMPT = """\
This image shows a USAF 1951 resolution test chart. The red rectangle highlights \
a reference square. What even-numbered group does this square belong to?

Valid answers: -2, 0, 2, 4, 6.\
"""


class GroupResult(BaseModel):
    group_number: int


class ScaleResult(BaseModel):
    group_number: int
    square_edge_um: float
    scale_um_per_px: float


identify_scale_agent = Agent(
    name="identify_scale",
    instructions=PROMPT,
    model="gpt-5.4-nano",
    model_settings=ModelSettings(reasoning=Reasoning(effort="low"), verbosity="low"),
    tools=[],
    output_type=GroupResult,
)


def main(data: np.ndarray, anchor: AnchorResult) -> ScaleResult:
    print("Running stage 1: identify_scale")

    cx, cy = anchor.center_x, anchor.center_y
    half = anchor.edge_length_px / 2
    bbox = (
        int(cx - half),
        int(cy - half),
        int(anchor.edge_length_px),
        int(anchor.edge_length_px),
    )
    base64_image = to_base64_png(data, bbox=bbox)

    result = Runner.run_sync(
        identify_scale_agent,
        max_turns=1,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "What group number is the highlighted reference square?",
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

    group = result.final_output.group_number
    square_edge_um = SQUARE_EDGE_UM[group]
    scale_um_per_px = square_edge_um / anchor.edge_length_px

    scale = ScaleResult(
        group_number=group,
        square_edge_um=square_edge_um,
        scale_um_per_px=scale_um_per_px,
    )
    print(f"Scale result:")
    print(f"  Group: {scale.group_number}")
    print(f"  Square edge: {scale.square_edge_um:.2f} µm")
    print(f"  Scale: {scale.scale_um_per_px:.4f} µm/px")

    return scale
