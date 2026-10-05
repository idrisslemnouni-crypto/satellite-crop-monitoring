"""Read a fixed 20 m grid with explicit calibration and categorical quality masks."""

import hashlib
import json
from pathlib import Path

import certifi
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

BANDS = ("red", "green", "nir", "swir16")


def grid_spec(config: dict) -> dict:
    resolution = config["resolution"]
    if resolution != 20:
        raise ValueError("This benchmark grid is fixed at 20 m")
    left, bottom, right, top = transform_bounds("EPSG:4326", config["crs"], *config["bbox"])
    left = np.floor(left / resolution) * resolution
    top = np.ceil(top / resolution) * resolution
    return {
        "crs": config["crs"],
        "transform": from_origin(left, top, resolution, resolution),
        "width": int(np.ceil((right - left) / resolution)),
        "height": int(np.ceil((top - bottom) / resolution)),
    }


def calibrate(dn: np.ndarray, asset: dict) -> np.ndarray:
    metadata = asset.get("raster:bands", [{}])[0]
    if "scale" not in metadata or "offset" not in metadata:
        raise ValueError("Reflectance asset must explicitly specify scale and offset")
    nodata = metadata.get("nodata")
    if nodata is None:
        raise ValueError("Reflectance asset must specify raw nodata")
    # Calibrate in float64 so DN=1000 remains zero rather than a tiny negative
    # value caused by float32 subtraction with scale=0.0001 and offset=-0.1.
    output = dn.astype(np.float64) * metadata["scale"] + metadata["offset"]
    output[(dn == nodata) | ~np.isfinite(dn)] = np.nan
    output[output < 0] = np.nan
    return output.astype(np.float32)


def clear_mask(scl: np.ndarray, bands: dict, allowed: list[int]) -> np.ndarray:
    valid = np.isin(scl, allowed)
    for array in bands.values():
        valid &= np.isfinite(array)
    return valid


def load_scene(item: dict, config: dict, raw_dir: Path) -> tuple[dict, np.ndarray, dict]:
    grid = grid_spec(config)
    raw_dir.mkdir(parents=True, exist_ok=True)
    cached = raw_dir / f"{item['id']}.npz"
    fingerprint = hashlib.sha256(
        json.dumps(
            {"item": item, "config": config, "calibration_version": 2}, sort_keys=True
        ).encode()
    ).hexdigest()
    if cached.exists():
        with np.load(cached, allow_pickle=False) as data:
            if str(data["fingerprint"]) != fingerprint:
                raise ValueError(
                    "Cached scene manifest/config changed; remove only the obsolete cache file"
                )
            bands = {name: data[name].copy() for name in BANDS}
            scl = data["scl"].copy()
    else:
        bands = {}
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
            GDAL_HTTP_TIMEOUT=30,
            GDAL_HTTP_MAX_RETRY=2,
            CURL_CA_BUNDLE=certifi.where(),
        ):
            for name in (*BANDS, "scl"):
                asset = item["assets"][name]
                if not asset["href"].startswith("https://"):
                    raise ValueError("Use only public HTTPS COG assets")
                with rasterio.open(asset["href"]) as source:
                    if source.crs is None:
                        raise ValueError("Source raster has no CRS")
                    method = Resampling.nearest if name == "scl" else Resampling.bilinear
                    with WarpedVRT(
                        source,
                        **grid,
                        resampling=method,
                        dtype="uint8" if name == "scl" else "float32",
                    ) as vrt:
                        array = vrt.read(1)
                if name == "scl":
                    scl = array
                else:
                    bands[name] = calibrate(array, asset)
        np.savez_compressed(cached, **bands, scl=scl, fingerprint=fingerprint)
    valid = clear_mask(scl, bands, config["allowed_scl"])
    evidence = {
        "id": item["id"],
        "date": item["properties"]["datetime"][:10],
        "scene_cloud_percent": item["properties"]["eo:cloud_cover"],
        "roi_valid_fraction": float(valid.mean()),
        "roi_valid_pixels": int(valid.sum()),
        "roi_cache_sha256": hashlib.sha256(cached.read_bytes()).hexdigest(),
        "calibration": {name: item["assets"][name]["raster:bands"][0] for name in BANDS},
    }
    return bands, valid, evidence


def write_geotiff(path: Path, arrays: dict, grid: dict) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        **grid,
        count=len(arrays),
        dtype="float32",
        nodata=-9999.0,
        compress="deflate",
    ) as target:
        for index, (name, array) in enumerate(arrays.items(), start=1):
            target.write(np.where(np.isfinite(array), array, -9999.0).astype(np.float32), index)
            target.set_band_description(index, name)
        target.update_tags(
            source="Modified Copernicus Sentinel data (2024)", units="dimensionless indices"
        )
