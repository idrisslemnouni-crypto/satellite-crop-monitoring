"""Spectral indices from calibrated reflectance, not unscaled digital numbers."""

import numpy as np


def ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    output = np.full(numerator.shape, np.nan, dtype=np.float32)
    valid = np.isfinite(numerator) & np.isfinite(denominator) & (denominator > 1e-8)
    np.divide(numerator, denominator, out=output, where=valid)
    return output


def compute_indices(bands: dict[str, np.ndarray], valid: np.ndarray) -> dict[str, np.ndarray]:
    red, green, nir, swir = [bands[name] for name in ("red", "green", "nir", "swir16")]
    if any(b.shape != valid.shape for b in (red, green, nir, swir)):
        raise ValueError("All bands and validity mask must share a grid")
    output = {
        "NDVI": ratio(nir - red, nir + red),
        "NDWI": ratio(green - nir, green + nir),
        "NDMI": ratio(nir - swir, nir + swir),
        "SAVI": ratio(1.5 * (nir - red), nir + red + 0.5),
    }
    for name, array in output.items():
        array[~valid] = np.nan
        limit = 1.5 if name == "SAVI" else 1.0
        if np.isfinite(array).any() and np.nanmax(np.abs(array)) > limit + 1e-5:
            raise ValueError(f"{name} outside physical range; check calibration")
    return output
