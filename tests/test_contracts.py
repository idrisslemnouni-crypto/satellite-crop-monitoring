import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

from satellite.indices import compute_indices, ratio
from satellite.pipeline import common_support
from satellite.raster import calibrate, clear_mask, grid_spec, write_geotiff


def test_calibration_offset_and_nodata():
    asset = {"raster:bands": [{"scale": 0.0001, "offset": -0.1, "nodata": 0}]}
    output = calibrate(np.array([[0, 1000, 2000, 900]], dtype=np.float32), asset)
    assert np.isnan(output[0, 0])
    assert output[0, 1] == pytest.approx(0)
    assert output[0, 2] == pytest.approx(0.1)
    assert np.isnan(output[0, 3])


def test_missing_scale_is_rejected():
    with pytest.raises(ValueError, match="scale"):
        calibrate(np.ones((2, 2)), {"raster:bands": [{"nodata": 0}]})


def test_zero_denominator_is_nan():
    assert np.isnan(ratio(np.array([0.0]), np.array([0.0]))).all()


def test_indices_use_scaled_reflectance():
    bands = {
        name: np.array([[value]], dtype=np.float32)
        for name, value in [("red", 0.1), ("green", 0.2), ("nir", 0.5), ("swir16", 0.3)]
    }
    output = compute_indices(bands, np.array([[True]]))
    assert output["NDVI"][0, 0] == pytest.approx(2 / 3)
    assert output["SAVI"][0, 0] == pytest.approx(0.6 / 1.1)
    assert output["NDMI"][0, 0] == pytest.approx(0.25)
    assert output["NDWI"][0, 0] == pytest.approx(-3 / 7)


def test_cloud_shadow_and_nonfinite_values_are_masked():
    scl = np.array([[4, 5, 6, 3, 8, 9, 10, 11, 0, 7]])
    bands = {"red": np.ones(scl.shape)}
    valid = clear_mask(scl, bands, [4, 5, 6])
    assert valid.tolist() == [[True, True, True, False, False, False, False, False, False, False]]
    bands["red"][0, 0] = np.nan
    assert not clear_mask(scl, bands, [4, 5, 6])[0, 0]


def test_common_support_prevents_changing_pixel_sample():
    a = np.array([[True, True], [False, True]])
    b = np.array([[False, True], [True, True]])
    np.testing.assert_array_equal(common_support([a, b]), [[False, True], [False, True]])


def test_mismatched_grids_are_rejected():
    with pytest.raises(ValueError, match="aligned"):
        common_support([np.ones((2, 2), bool), np.ones((2, 3), bool)])


def test_grid_is_projected_and_fixed():
    root = Path(__file__).parents[1]
    grid = grid_spec(json.loads((root / "configs/default.json").read_text()))
    assert grid["crs"] == "EPSG:32615"
    assert (grid["width"], grid["height"]) == (172, 226)
    assert grid["transform"].a == 20 and grid["transform"].e == -20


def test_geotiff_roundtrip_preserves_georeferencing(tmp_path):
    from rasterio.transform import from_origin

    grid = {
        "crs": "EPSG:32615",
        "transform": from_origin(300000, 4500000, 20, 20),
        "width": 2,
        "height": 2,
    }
    values = np.array([[0.2, np.nan], [0.7, 0.8]])
    path = tmp_path / "indices.tif"
    write_geotiff(path, {"NDVI": values}, grid)
    with rasterio.open(path) as data:
        assert data.crs.to_epsg() == 32615
        assert data.transform == grid["transform"]
        assert data.descriptions == ("NDVI",)
        assert data.read(1, masked=True).mask[0, 1]
        np.testing.assert_allclose(data.read(1)[[0, 1, 1], [0, 0, 1]], [0.2, 0.7, 0.8])
