"""Run real scenes, common-support statistics, georeferenced outputs and figures."""

import json
import logging
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from satellite.indices import compute_indices
from satellite.raster import grid_spec, load_scene, write_geotiff


def common_support(masks: list[np.ndarray]) -> np.ndarray:
    if not masks or any(m.shape != masks[0].shape for m in masks):
        raise ValueError("Masks must be nonempty and aligned")
    return np.logical_and.reduce(masks)


def run(root: Path) -> dict:
    config = json.loads((root / "configs/default.json").read_text())
    items = json.loads((root / "data/scene-manifest.json").read_text())
    if len(items) != len(config["months"]):
        raise ValueError("Manifest must contain exactly one scene per configured month")
    dates = [i["properties"]["datetime"][:7] for i in items]
    expected = [f"{config['year']}-{m:02d}" for m in config["months"]]
    if dates != expected:
        raise ValueError("Manifest dates are not ordered configured months")
    raw, processed, reports = root / "data/raw", root / "data/processed", root / "reports"
    processed.mkdir(parents=True, exist_ok=True)
    (reports / "figures").mkdir(parents=True, exist_ok=True)
    grid = grid_spec(config)
    index_arrays, masks, provenance = [], [], []
    for item in items:
        logging.info("Read public COG windows for %s", item["id"])
        bands, valid, evidence = load_scene(item, config, raw)
        indices = compute_indices(bands, valid)
        # The common footprint must also exclude mathematically undefined indices.
        valid &= np.logical_and.reduce([np.isfinite(a) for a in indices.values()])
        for array in indices.values():
            array[~valid] = np.nan
        index_arrays.append(indices)
        masks.append(valid)
        evidence["all_indices_valid_fraction"] = float(valid.mean())
        provenance.append(evidence)
        write_geotiff(processed / f"{evidence['date']}_indices.tif", indices, grid)
    common = common_support(masks)
    if common.mean() < config["minimum_common_fraction"]:
        raise ValueError("Insufficient common support: cannot compare dates reliably")
    rows = []
    for arrays, mask, evidence in zip(index_arrays, masks, provenance, strict=True):
        row = {
            "date": evidence["date"],
            "valid_fraction": float(mask.mean()),
            "common_pixels": int(common.sum()),
        }
        for name, array in arrays.items():
            values = array[common]
            row.update(
                {
                    f"{name}_median": float(np.median(values)),
                    f"{name}_q10": float(np.quantile(values, 0.1)),
                    f"{name}_q90": float(np.quantile(values, 0.9)),
                    f"{name}_own_valid_median": float(np.nanmedian(array)),
                }
            )
        rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(reports / "time-series.csv", index=False)
    result = {
        "config": config,
        "grid": {
            "crs": grid["crs"],
            "resolution_m": config["resolution"],
            "width": grid["width"],
            "height": grid["height"],
            "transform": list(grid["transform"]),
        },
        "scenes": provenance,
        "common_pixels": int(common.sum()),
        "common_fraction": float(common.mean()),
        "common_area_hectares": float(common.sum() * config["resolution"] ** 2 / 10000),
        "versions": {name: version(name) for name in ["rasterio", "numpy", "pandas", "matplotlib"]},
        "interpretation": "Landscape indices and phenology; no crop identity, yield or diagnosed water stress labels",
    }
    (reports / "run-manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(2, 4, figsize=(14, 8), layout="constrained")
    for ax, arrays, evidence in zip(axes.flat, index_arrays, provenance, strict=False):
        image = ax.imshow(
            np.where(common, arrays["NDVI"], np.nan),
            vmin=0,
            vmax=1,
            cmap="YlGn",
            extent=[
                grid["transform"].c,
                grid["transform"].c + grid["width"] * 20,
                grid["transform"].f - grid["height"] * 20,
                grid["transform"].f,
            ],
        )
        ax.set_title(evidence["date"])
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        ax.ticklabel_format(style="plain", useOffset=False)
        ax.tick_params(axis="x", rotation=30)
    axes.flat[-1].axis("off")
    fig.colorbar(image, ax=list(axes.flat), label="NDVI · common clear support", shrink=0.65)
    fig.suptitle("Modified Copernicus Sentinel data (2024) · EPSG:32615 · 20 m")
    fig.savefig(reports / "figures/ndvi-maps.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    x = pd.to_datetime(summary.date)
    for ax, name in zip(axes.flat, ["NDVI", "NDMI", "NDWI", "SAVI"], strict=True):
        ax.plot(
            x, summary[name + "_median"], marker="o", color="#176b50", label="Common support median"
        )
        ax.fill_between(
            x,
            summary[name + "_q10"],
            summary[name + "_q90"],
            color="#176b50",
            alpha=0.15,
            label="Spatial 10–90% range",
        )
        ax.set_title(name)
        ax.set_ylabel("Dimensionless")
        ax.tick_params(axis="x", rotation=30)
    axes.flat[0].legend(fontsize=8)
    fig.suptitle("Seven observations, not monthly composites or uncertainty intervals")
    fig.savefig(reports / "figures/index-time-series.png", dpi=150)
    plt.close(fig)
    return result
