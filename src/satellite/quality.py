"""Cache-only ROI support diagnostics that preserve the original scientific outputs."""

import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from matplotlib.figure import Figure
from rasterio.crs import CRS

from satellite.indices import compute_indices
from satellite.pipeline import common_support
from satellite.raster import BANDS, grid_spec


def scene_quality(scl: np.ndarray, bands: dict, allowed: list[int]) -> tuple[dict, np.ndarray]:
    """Partition pixels in SCL, calibrated-band, then index order; diagnostics may overlap."""
    if scl.ndim != 2 or not scl.size:
        raise ValueError("SCL must be a nonempty two-dimensional grid")
    if any(name not in bands or bands[name].shape != scl.shape for name in BANDS):
        raise ValueError("All required bands and SCL must share a grid")
    if not np.isfinite(scl).all() or not np.isin(scl, range(12)).all():
        raise ValueError("SCL must contain integer classes 0 through 11")
    if not allowed or any(isinstance(code, bool) or code not in range(12) for code in allowed):
        raise ValueError("Allowed SCL classes must be nonempty integer codes 0 through 11")
    scl_allowed = np.isin(scl, allowed)
    finite = np.logical_and.reduce([np.isfinite(bands[name]) for name in BANDS])
    preliminary = scl_allowed & finite
    indices = compute_indices(bands, preliminary)
    index_finite = np.logical_and.reduce([np.isfinite(array) for array in indices.values()])
    valid = preliminary & index_finite
    count = lambda mask: int(np.count_nonzero(mask))  # noqa: E731
    result = {
        "roi_pixels": int(scl.size),
        "scl_rejected_pixels": count(~scl_allowed),
        "allowed_scl_nonfinite_band_pixels": count(scl_allowed & ~finite),
        "allowed_scl_finite_band_pixels": count(preliminary),
        "undefined_index_pixels": count(preliminary & ~index_finite),
        "scene_valid_pixels": count(valid),
        "scene_valid_fraction": float(valid.mean()),
    }
    result.update({f"scl_{code}_pixels": count(scl == code) for code in range(12)})
    result.update(
        {
            f"allowed_scl_nonfinite_{name}_pixels": count(scl_allowed & ~np.isfinite(bands[name]))
            for name in BANDS
        }
    )
    result.update(
        {
            f"finite_bands_undefined_{name.lower()}_pixels": count(
                preliminary & ~np.isfinite(array)
            )
            for name, array in indices.items()
        }
    )
    partition = (
        "scl_rejected_pixels",
        "allowed_scl_nonfinite_band_pixels",
        "undefined_index_pixels",
        "scene_valid_pixels",
    )
    if sum(result[key] for key in partition) != scl.size:
        raise ValueError("Scene quality partition does not sum to the ROI")
    if sum(result[f"scl_{code}_pixels"] for code in range(12)) != scl.size:
        raise ValueError("SCL counts do not sum to the ROI")
    return result, valid


def support_counts(valid: np.ndarray, common: np.ndarray) -> dict:
    """Split scene validity into common pixels and otherwise valid pixels lost to other dates."""
    if (
        valid.ndim != 2
        or not valid.size
        or valid.shape != common.shape
        or valid.dtype != bool
        or common.dtype != bool
    ):
        raise ValueError("Support masks must be nonempty, boolean and aligned")
    if np.any(common & ~valid):
        raise ValueError("Common support must be a subset of scene validity")
    shared = int(common.sum())
    excluded = int((valid & ~common).sum())
    if shared + excluded != int(valid.sum()):
        raise ValueError("Support counts do not sum to scene validity")
    return {
        "common_pixels": shared,
        "common_fraction": float(common.mean()),
        "scene_valid_excluded_common_pixels": excluded,
    }


def pixel_area_m2(grid: dict) -> float | None:
    """Use affine pixel area only for a verified projected metre CRS."""
    crs = CRS.from_user_input(grid["crs"])
    if not crs.is_projected or crs.linear_units_factor[1] != 1.0:
        return None
    affine = grid["transform"]
    area = abs(affine.a * affine.e - affine.b * affine.d)
    if not np.isfinite(area) or area <= 0:
        raise ValueError("A finite positive affine pixel area is required")
    return float(area)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root: Path) -> dict:
    """Read only existing caches/rasters; reject incompatible history before writing QA files."""
    config_path = root / "configs/default.json"
    manifest_path = root / "data/scene-manifest.json"
    historical_path = root / "reports/run-manifest.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    items = json.loads(manifest_path.read_text(encoding="utf-8"))
    historical = json.loads(historical_path.read_text(encoding="utf-8"))
    expected_dates = [f"{config['year']}-{month:02d}" for month in config["months"]]
    if [item["properties"]["datetime"][:7] for item in items] != expected_dates or len(
        {item["id"] for item in items}
    ) != len(items):
        raise ValueError("Manifest must contain one unique ordered scene per configured month")
    if historical["config"] != config:
        raise ValueError("Historical configuration differs from the frozen study")
    if [scene["id"] for scene in historical["scenes"]] != [item["id"] for item in items]:
        raise ValueError("Historical scene IDs/order differ")
    grid = grid_spec(config)
    original_grid = historical["grid"]
    if (
        original_grid["crs"] != grid["crs"]
        or original_grid["width"] != grid["width"]
        or original_grid["height"] != grid["height"]
        or original_grid["transform"] != list(grid["transform"])
    ):
        raise ValueError("Historical grid differs")
    caches = [root / "data/raw" / f"{item['id']}.npz" for item in items]
    rasters = [
        root / "data/processed" / f"{scene['date']}_indices.tif" for scene in historical["scenes"]
    ]
    if any(not path.is_file() for path in caches + rasters):
        raise ValueError(
            "Quality audit requires all existing ROI caches and index rasters; run the original pipeline first"
        )
    protected = [
        historical_path,
        root / "reports/time-series.csv",
        root / "reports/figures/ndvi-maps.png",
        root / "reports/figures/index-time-series.png",
        *rasters,
        *caches,
    ]
    protected_hashes = {
        str(path.relative_to(root)).replace("\\", "/"): _sha256(path) for path in protected
    }
    rows, masks = [], []
    for item, cache, raster, original in zip(
        items, caches, rasters, historical["scenes"], strict=True
    ):
        fingerprint = hashlib.sha256(
            json.dumps(
                {"item": item, "config": config, "calibration_version": 2}, sort_keys=True
            ).encode()
        ).hexdigest()
        if _sha256(cache) != original["roi_cache_sha256"]:
            raise ValueError("Cached scene hash differs from historical evidence")
        with np.load(cache, allow_pickle=False) as data:
            if str(data["fingerprint"]) != fingerprint:
                raise ValueError("Cached scene fingerprint differs")
            bands = {name: data[name].copy() for name in BANDS}
            scl = data["scl"].copy()
        if scl.shape != (grid["height"], grid["width"]):
            raise ValueError("Cached shape differs from the configured grid")
        counts, valid = scene_quality(scl, bands, config["allowed_scl"])
        if counts["allowed_scl_finite_band_pixels"] != original[
            "roi_valid_pixels"
        ] or not np.isclose(
            counts["scene_valid_fraction"],
            original["all_indices_valid_fraction"],
            rtol=0,
            atol=1e-12,
        ):
            raise ValueError("Cached validity differs from historical evidence")
        with rasterio.open(raster) as source:
            if (
                source.crs != CRS.from_user_input(grid["crs"])
                or source.transform != grid["transform"]
                or (source.height, source.width) != valid.shape
                or source.count != 4
                or source.descriptions != ("NDVI", "NDWI", "NDMI", "SAVI")
            ):
                raise ValueError("Historical index raster is not aligned")
            stored = source.read(masked=True)
            stored_valid = ~np.ma.getmaskarray(stored)
            if (
                not np.all(stored_valid == valid[None, :, :])
                or not np.isfinite(stored.data[stored_valid]).all()
            ):
                raise ValueError("Recomputed masks differ from historical index rasters")
        rows.append(
            {
                "id": item["id"],
                "date": original["date"],
                "scene_cloud_percent": item["properties"]["eo:cloud_cover"],
                "roi_cache_sha256": _sha256(cache),
                **counts,
            }
        )
        masks.append(valid)
    common = common_support(masks)
    if int(common.sum()) != historical["common_pixels"]:
        raise ValueError("Common support differs from historical evidence")
    area = pixel_area_m2(grid)
    for row, valid in zip(rows, masks, strict=True):
        row.update(support_counts(valid, common))
        if area is not None:
            row["scene_valid_area_hectares"] = row["scene_valid_pixels"] * area / 10000
            row["common_area_hectares"] = row["common_pixels"] * area / 10000
    result = {
        "protocol": "cached_roi_quality_partition_v1",
        "config": config,
        "grid": original_grid,
        "pixel_area_m2": area,
        "scene_manifest_sha256": _sha256(manifest_path),
        "config_sha256": _sha256(config_path),
        "preserved_artifact_sha256": protected_hashes,
        "common_pixels": int(common.sum()),
        "common_fraction": float(common.mean()),
        "scenes": rows,
        "partition": [
            "scl_rejected_pixels",
            "allowed_scl_nonfinite_band_pixels",
            "undefined_index_pixels",
            "scene_valid_excluded_common_pixels",
            "common_pixels",
        ],
        "diagnostic_notice": "Per-band and per-index counts overlap; only the ordered partition and SCL class counts sum to ROI pixels.",
        "interpretation": "ROI data support; SCL admits vegetation, nonvegetated land and water. No crop identity, diagnosed stress or field-accuracy claim.",
        "versions": {name: version(name) for name in ["numpy", "pandas", "rasterio", "matplotlib"]},
    }
    for row in rows:
        if sum(row[key] for key in result["partition"]) != row["roi_pixels"]:
            raise ValueError("Common-support partition does not sum to ROI pixels")
    reports = root / "reports"
    pd.DataFrame(rows).to_csv(reports / "scene-quality.csv", index=False)
    (reports / "scene-quality.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    fig = Figure(figsize=(11, 7.3))
    axes = fig.subplots(2, 1, sharex=True)
    fig.subplots_adjust(left=0.095, right=0.98, top=0.88, bottom=0.17, hspace=0.15)
    x = np.arange(len(rows))
    bottom = np.zeros(len(rows))
    for key, label, color in [
        ("scl_rejected_pixels", "Rejected SCL", "#cc713d"),
        ("allowed_scl_nonfinite_band_pixels", "Nonfinite bands after SCL", "#9a7896"),
        ("undefined_index_pixels", "Undefined indices after finite bands", "#767676"),
        ("scene_valid_excluded_common_pixels", "Valid here, excluded by another date", "#2b7690"),
    ]:
        values = np.array([row[key] for row in rows])
        axes[0].bar(x, values, bottom=bottom, color=color, label=label)
        bottom += values
    axes[0].set(
        ylabel="Pixels excluded from common support",
        title=f"Shared footprint: {int(common.sum()):,} of {common.size:,} ROI pixels",
    )
    axes[0].set_ylim(0, max(float(bottom.max()), 1) * 1.33)
    axes[0].legend(fontsize=8, ncol=2, loc="upper right")
    axes[1].plot(
        x,
        [100 * row["scene_valid_fraction"] for row in rows],
        marker="o",
        color="#176b50",
        label="Valid for all four indices on this date",
    )
    axes[1].axhline(
        100 * common.mean(),
        color="#2b7690",
        linestyle="--",
        label=f"Valid on all {len(rows)} dates",
    )
    axes[1].set(
        ylabel="ROI valid pixels (%)",
        xlabel="Individual scene date",
        xticks=x,
        xticklabels=[row["date"] for row in rows],
    )
    axes[1].legend(fontsize=8, loc="upper left")
    axes[1].tick_params(axis="x", rotation=25)
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    fig.suptitle("ROI quality audit · Modified Copernicus Sentinel data (2024)", y=0.98)
    fig.savefig(reports / "figures/scene-quality.png", dpi=160)
    if any(_sha256(root / path) != digest for path, digest in protected_hashes.items()):
        raise ValueError("An original artifact changed during the quality audit")
    return result
