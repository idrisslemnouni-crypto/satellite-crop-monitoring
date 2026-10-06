"""Synthetic fixtures exercise quality exclusions; they are not observed scene results."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from satellite.indices import compute_indices
from satellite.pipeline import common_support
from satellite.quality import pixel_area_m2, run, scene_quality, support_counts
from satellite.raster import BANDS, calibrate, clear_mask, write_geotiff


def bands(shape):
    return {name: np.full(shape, 0.2, dtype=np.float32) for name in BANDS}


def test_ordered_partition_handles_overlapping_exclusions():
    scl = np.array([[0, 4, 5, 6, 4, 3]])
    values = bands(scl.shape)
    values["red"][0, [0, 1, 5]] = np.nan
    values["nir"][0, 1] = np.inf
    values["red"][0, 2] = values["nir"][0, 2] = 0
    counts, valid = scene_quality(scl, values, [4, 5, 6])
    assert [
        counts[name]
        for name in [
            "scl_rejected_pixels",
            "allowed_scl_nonfinite_band_pixels",
            "undefined_index_pixels",
            "scene_valid_pixels",
        ]
    ] == [2, 1, 1, 2]
    assert valid.tolist() == [[False, False, False, True, True, False]]
    assert counts["allowed_scl_nonfinite_red_pixels"] == 1
    assert counts["allowed_scl_nonfinite_nir_pixels"] == 1
    assert counts["finite_bands_undefined_ndvi_pixels"] == 1
    assert counts["finite_bands_undefined_savi_pixels"] == 0
    assert sum(counts[f"scl_{code}_pixels"] for code in range(12)) == counts["roi_pixels"]


def test_raw_nodata_is_calibrated_to_nonfinite_exclusion():
    scl = np.array([[4, 5, 6]])
    values = bands(scl.shape)
    values["red"] = calibrate(
        np.array([[0, 900, 2000]], dtype=np.float32),
        {"raster:bands": [{"scale": 0.0001, "offset": -0.1, "nodata": 0}]},
    )
    counts, valid = scene_quality(scl, values, [4, 5, 6])
    assert counts["allowed_scl_nonfinite_band_pixels"] == 2
    assert counts["undefined_index_pixels"] == 0
    assert valid.tolist() == [[False, False, True]]
    np.testing.assert_array_equal(valid, clear_mask(scl, values, [4, 5, 6]))


def test_zero_reflectance_excluded_once_even_when_multiple_indices_undefined():
    scl = np.array([[4]])
    counts, valid = scene_quality(
        scl, {name: np.zeros((1, 1), dtype=np.float32) for name in BANDS}, [4]
    )
    assert counts["undefined_index_pixels"] == 1
    assert counts["scene_valid_pixels"] == 0
    assert not valid.any()
    assert (
        sum(
            counts[f"finite_bands_undefined_{name}_pixels"]
            for name in ["ndvi", "ndwi", "ndmi", "savi"]
        )
        == 3
    )


@pytest.mark.parametrize("shape", [(1, 3), (3,), (1, 2, 1)])
def test_broadcastable_band_shapes_are_rejected(shape):
    scl = np.full((2, 3), 4)
    values = bands(scl.shape)
    values["red"] = np.ones(shape)
    with pytest.raises(ValueError, match="share a grid"):
        scene_quality(scl, values, [4])


@pytest.mark.parametrize(
    "scl",
    [np.array([4]), np.empty((0, 2)), np.array([[4.5]]), np.array([[np.nan]]), np.array([[12]])],
)
def test_invalid_scl_rejected(scl):
    with pytest.raises(ValueError, match="SCL"):
        scene_quality(scl, bands(scl.shape), [4])


def test_common_support_is_exact_and_five_way_partition_closes():
    a = np.array([[True, True, False], [True, False, True]])
    b = np.array([[True, False, True], [True, True, True]])
    common = common_support([a, b])
    assert support_counts(a, common)["scene_valid_excluded_common_pixels"] == 1
    assert support_counts(b, common)["scene_valid_excluded_common_pixels"] == 2
    assert support_counts(a, common)["common_pixels"] == 3
    scl = np.where(a, 4, 0)
    counts, valid = scene_quality(scl, bands(scl.shape), [4])
    counts.update(support_counts(valid, common))
    assert (
        sum(
            counts[key]
            for key in [
                "scl_rejected_pixels",
                "allowed_scl_nonfinite_band_pixels",
                "undefined_index_pixels",
                "scene_valid_excluded_common_pixels",
                "common_pixels",
            ]
        )
        == scl.size
    )
    with pytest.raises(ValueError, match="subset"):
        support_counts(a, np.ones_like(a))
    with pytest.raises(ValueError, match="aligned"):
        support_counts(a, np.ones((1, 3), bool))
    with pytest.raises(ValueError, match="boolean"):
        support_counts(a.astype(int), common)


def test_area_requires_projected_metres_and_uses_affine_determinant():
    affine = Affine(20, 2, 0, 3, -20, 0)
    assert pixel_area_m2({"crs": "EPSG:32615", "transform": affine}) == 406
    assert pixel_area_m2({"crs": "EPSG:4326", "transform": affine}) is None
    assert pixel_area_m2({"crs": "EPSG:2277", "transform": affine}) is None
    with pytest.raises(ValueError, match="positive"):
        pixel_area_m2({"crs": "EPSG:32615", "transform": Affine.scale(0)})


def test_missing_cache_never_falls_back_to_network(tmp_path):
    root = Path(__file__).parents[1]
    for relative in [
        "configs/default.json",
        "data/scene-manifest.json",
        "reports/run-manifest.json",
    ]:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(json.loads((root / relative).read_text())))
    with pytest.raises(ValueError, match="existing ROI caches"):
        run(tmp_path)
    assert not (tmp_path / "reports/scene-quality.json").exists()


@pytest.fixture
def cached_study(tmp_path, monkeypatch):
    from satellite import quality

    grid = {
        "crs": "EPSG:32615",
        "transform": Affine(20, 0, 300000, 0, -20, 4500000),
        "width": 2,
        "height": 2,
    }
    config = {"year": 2024, "months": [4, 5], "allowed_scl": [4, 5, 6]}
    monkeypatch.setattr(quality, "grid_spec", lambda _: grid)
    items, scenes, masks = [], [], []
    for index, month in enumerate(config["months"]):
        item = {
            "id": f"synthetic_fixture_{month}",
            "properties": {"datetime": f"2024-{month:02d}-01T00:00:00Z", "eo:cloud_cover": 1},
        }
        items.append(item)
        scl = np.array([[4, 4], [4, 4]])
        scl[index, 1] = 0
        values = bands(scl.shape)
        counts, valid = scene_quality(scl, values, config["allowed_scl"])
        masks.append(valid)
        cache = tmp_path / "data/raw" / f"{item['id']}.npz"
        cache.parent.mkdir(parents=True, exist_ok=True)
        fingerprint = hashlib.sha256(
            json.dumps(
                {"item": item, "config": config, "calibration_version": 2}, sort_keys=True
            ).encode()
        ).hexdigest()
        np.savez_compressed(cache, **values, scl=scl, fingerprint=fingerprint)
        date = item["properties"]["datetime"][:10]
        raster = tmp_path / "data/processed" / f"{date}_indices.tif"
        raster.parent.mkdir(parents=True, exist_ok=True)
        write_geotiff(raster, compute_indices(values, valid), grid)
        scenes.append(
            {
                "id": item["id"],
                "date": date,
                "roi_cache_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
                "roi_valid_pixels": counts["allowed_scl_finite_band_pixels"],
                "all_indices_valid_fraction": counts["scene_valid_fraction"],
            }
        )
    history = {
        "config": config,
        "scenes": scenes,
        "grid": {
            "crs": grid["crs"],
            "transform": list(grid["transform"]),
            "width": grid["width"],
            "height": grid["height"],
        },
        "common_pixels": int(common_support(masks).sum()),
    }
    for relative, data in [
        ("configs/default.json", config),
        ("data/scene-manifest.json", items),
        ("reports/run-manifest.json", history),
    ]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    for relative in [
        "reports/time-series.csv",
        "reports/figures/ndvi-maps.png",
        "reports/figures/index-time-series.png",
    ]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Synthetic preserved artifact fixture")
    return tmp_path


def test_cached_runner_preserves_originals_and_reproduces_outputs(cached_study):
    originals = {path: path.read_bytes() for path in cached_study.rglob("*") if path.is_file()}
    first = run(cached_study)
    assert first["common_pixels"] == 2
    assert first["pixel_area_m2"] == 400
    assert all(row["scene_valid_excluded_common_pixels"] == 1 for row in first["scenes"])
    output_paths = [
        cached_study / "reports/scene-quality.csv",
        cached_study / "reports/scene-quality.json",
    ]
    written = [path.read_bytes() for path in output_paths]
    assert run(cached_study) == first
    assert [path.read_bytes() for path in output_paths] == written
    assert all(path.read_bytes() == content for path, content in originals.items())


def test_corrupt_cache_rejected_before_reports(cached_study):
    cache = next((cached_study / "data/raw").glob("*.npz"))
    cache.write_bytes(cache.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="hash differs"):
        run(cached_study)
    assert not (cached_study / "reports/scene-quality.csv").exists()


def test_historical_mask_mismatch_rejected_before_reports(cached_study):
    with rasterio.open(next((cached_study / "data/processed").glob("*.tif")), "r+") as source:
        array = source.read(1)
        array[0, 0] = source.nodata
        source.write(array, 1)
    with pytest.raises(ValueError, match="Recomputed masks"):
        run(cached_study)
    assert not (cached_study / "reports/scene-quality.csv").exists()
