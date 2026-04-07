from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import mtf_calc


def main() -> None:
    raw_image = mtf_calc.io.load_source("example-data.npy")

    black_roi = mtf_calc.select.select_roi(
        raw_image,
        prompt="Select the black normalization ROI from a dark background patch with no bars crossing it.",
    )
    white_roi = mtf_calc.select.select_roi(
        raw_image,
        size_ref=black_roi,
        prompt="Select the white normalization ROI from a bright background patch. Match the black ROI region type and size.",
    )
    bar_roi = mtf_calc.select.select_roi(
        raw_image,
        prompt="Select the bar ROI for the profile.",
    )

    dim = input("Profile direction (X or Y) [X]: ").strip().upper() or "X"
    if dim not in {"X", "Y"}:
        dim = "X"

    profile = mtf_calc.profiles.extract(
        raw_image,
        bar_roi=bar_roi,
        norm_rois={0: black_roi, 1: white_roi},
        dim=dim,
    )

    max_harmonics = 6
    x = np.arange(len(profile.norm_values), dtype=np.float64)
    y = np.asarray(profile.norm_values, dtype=np.float64)
    fits: list[dict[str, object]] = []

    for n_harmonics in range(1, max_harmonics + 1):
        fit = mtf_calc.profiles.fit(
            profile,
            norm_rois={0: black_roi, 1: white_roi},
            n_harmonics=n_harmonics,
        )

        omega = 2.0 * np.pi / float(fit.period_px)
        fitted = fit.slope * x + fit.intercept
        for index, amplitude in enumerate(fit.harmonic_amplitudes, start=0):
            harmonic_order = 2 * index + 1
            fitted += float(amplitude) * np.sin(harmonic_order * (omega * x + float(fit.phase_rad)))

        residual = y - fitted
        rmse = float(np.sqrt(np.mean(np.square(residual))))
        fits.append(
            {
                "n_harmonics": n_harmonics,
                "fit": fit,
                "fitted": fitted,
                "rmse": rmse,
            }
        )

        print(f"{n_harmonics} harmonic(s): period={fit.period_px:.4f}px, rmse={rmse:.6f}")

    best_fit = min(fits, key=lambda entry: float(entry["rmse"]))
    print(
        f"Best (by RMSE): {best_fit['n_harmonics']} harmonic(s), "
        f"rmse={best_fit['rmse']:.6f}"
    )

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), constrained_layout=True)

    axes[0].plot(profile.raw_values)
    axes[0].set_title("Raw profile")
    axes[0].set_xlabel("Pixel")
    axes[0].set_ylabel("Value")
    axes[0].grid(True, alpha=0.4)

    axes[1].plot(profile.norm_values, color="black", linewidth=1.5, label="Normalized profile")
    for entry in fits:
        n_harmonics = int(entry["n_harmonics"])
        fitted = np.asarray(entry["fitted"])
        rmse = float(entry["rmse"])
        axes[1].plot(fitted, label=f"COBF h={n_harmonics}, RMSE={rmse:.4f}")
    axes[1].set_title("Normalized profile")
    axes[1].set_xlabel("Pixel")
    axes[1].set_ylabel("Normalized value")
    axes[1].grid(True, alpha=0.4)
    axes[1].legend(loc="upper right", fontsize="small")

    for entry in fits:
        n_harmonics = int(entry["n_harmonics"])
        residual = y - np.asarray(entry["fitted"])
        axes[2].plot(residual, label=f"h={n_harmonics}")
    axes[2].set_title("Residuals (normalized - COBF)")
    axes[2].set_xlabel("Pixel")
    axes[2].set_ylabel("Residual")
    axes[2].grid(True, alpha=0.4)
    axes[2].legend(loc="upper right", fontsize="small")

    print()
    pick_raw = input("Pick a harmonic count to use [recommended by RMSE]: ").strip()
    try:
        pick = int(pick_raw) if pick_raw else int(best_fit["n_harmonics"])
    except ValueError:
        pick = int(best_fit["n_harmonics"])

    if pick < 1 or pick > max_harmonics:
        pick = int(best_fit["n_harmonics"])

    selected = next((item for item in fits if int(item["n_harmonics"]) == pick), best_fit)
    selected_fit = selected["fit"]
    selected_rmse = selected["rmse"]
    print()
    print(f"Selected harmonic count: {pick}")
    print(f"Selected period (px): {selected_fit.period_px:.4f}")
    print(f"Selected phase (rad): {selected_fit.phase_rad:.6f}")
    print(f"Selected slope: {selected_fit.slope:.6f}")
    print(f"Selected intercept: {selected_fit.intercept:.6f}")
    print(f"Selected RMSE: {selected_rmse:.6f}")
    print("Selected harmonic amplitudes:")
    for index, amplitude in enumerate(selected_fit.harmonic_amplitudes, start=1):
        print(f"  H{2 * index - 1}: {amplitude:.8f}")

    plt.show()
    mtf_calc.viz.close()


if __name__ == "__main__":
    main()
