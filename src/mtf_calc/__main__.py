from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import time
import numpy as np
from argparse import ArgumentParser

from mtf_calc.workflow.find_anchors import main as find_anchors
from mtf_calc.workflow.identify_scale import main as identify_scale
from mtf_calc.workflow.identify_bars import main as identify_bars
from mtf_calc.workflow.extract_rois import main as extract_rois
from mtf_calc.tools.images import image_display

def main(data: np.ndarray):
    print("Beginning MTF Calculation...")

    assert data.ndim == 2, "Data must be a 2D array"
    assert data.dtype == np.float32, "Data must be of type float32"
    assert data.max() <= 1.0, "Data values must be between 0 and 1"
    assert data.min() >= 0.0, "Data values must be between 0 and 1"

    t0 = time.perf_counter()
    anchor = find_anchors(data)
    t1 = time.perf_counter()
    print(f"  Find anchors: {t1 - t0:.3f}s")

    scale = identify_scale(data, anchor)
    t2 = time.perf_counter()
    print(f"  Identify scale: {t2 - t1:.3f}s")

    bars = identify_bars(data, scale)
    t3 = time.perf_counter()
    print(f"  Identify bars: {t3 - t2:.3f}s")

    rois = extract_rois(data, scale, bars)
    t4 = time.perf_counter()
    print(f"  Extract ROIs: {t4 - t3:.3f}s")

    print(f"  Total: {t4 - t0:.3f}s")



def cli():
    parser = ArgumentParser()
    parser.add_argument("data_path", type=str, help="Path to the input data file")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()

    data = np.load(Path(args.data_path))
    image_display.set_headless(args.headless)

    main(data)


if __name__ == "__main__":
    cli()
