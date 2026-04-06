from pathlib import Path
import numpy as np
from argparse import ArgumentParser


def main(data_path: str | Path):
    print("Beginning MTF Calculation...")

    data_path = Path(data_path)
    data = np.load(data_path)
    assert data.ndim == 2, "Data must be a 2D array"
    assert data.dtype == np.float32, "Data must be of type float32"
    assert data.max() <= 1.0, "Data values must be between 0 and 1"
    assert data.min() >= 0.0, "Data values must be between 0 and 1"


def cli():
    parser = ArgumentParser()
    parser.add_argument("data_path", type=str, help="Path to the input data file")
    args = parser.parse_args()
    main(args.data_path)


if __name__ == "__main__":
    cli()
