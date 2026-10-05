# Satellite Crop Monitoring

Seven real Sentinel-2 observations reveal the seasonal evolution of an Iowa agricultural landscape on a consistent, cloud-masked 20 m grid.

![Landscape maps](reports/figures/ndvi-maps.png)

## Problem and scope

Comparing satellite dates is misleading when cloud masks, resolution or reflectance calibration change. This pipeline preserves a common spatial footprint and records those choices. It is descriptive monitoring, with no trained stress detector, crop classification or yield prediction. No field observations or crop-parcel labels are available.

## Dataset

Seven Sentinel-2 Collection-1 Level-2A scenes, April–October 2024, from [Earth Search](https://earth-search.aws.element84.com/v1), collection `sentinel-2-c1-l2a`. WGS84 area: `[-94.50, 41.40, -94.46, 41.44]`. The [frozen manifest](data/scene-manifest.json) retains complete source asset URLs and calibration. Select the lowest scene-cloud-cover eligible observation per month; these are individual observations, not monthly composites. Discovery found 44 eligible items; selection uses cloud metadata, never index values.

Code is MIT. Source data have [Copernicus Sentinel terms](https://dataspace.copernicus.eu/terms-and-conditions); they are not relicensed MIT or CC BY. Attribution: **Modified Copernicus Sentinel data (2024)**. See [data provenance](data/README.md).

## Workflow

```text
Frozen public STAC items → HTTPS COG windows → common 20 m grid
→ reflectance calibration → SCL quality mask → four indices
→ common valid footprint → GeoTIFFs, CSV, maps and provenance
```

Continuous bands use bilinear resampling; categorical SCL uses nearest neighbour. STAC metadata specify scale `0.0001`, offset `-0.1`, raw nodata `0`; relying on Rasterio defaults would omit calibration. Arithmetic uses float64 before float32 storage to avoid masking zero reflectance due to rounding. SCL classes 4/5/6 are admitted, including water and nonvegetated land. Cloud, shadow, snow, unclassified and nodata pixels are excluded. Negative reflectance and nonpositive index denominators are conservatively masked.

| Index | Definition | Interpretation |
|---|---|---|
| NDVI | (NIR − red)/(NIR + red) | Greenness |
| NDWI, McFeeters | (green − NIR)/(green + NIR) | Water contrast; different from NDMI |
| NDMI | (NIR − SWIR1)/(NIR + SWIR1) | Moisture-sensitive spectral contrast |
| SAVI | 1.5 × (NIR − red)/(NIR + red + 0.5) | Soil-adjusted greenness |

## Executed results

The projected grid is EPSG:32615, 172 × 226 pixels at 20 m. The common valid footprint contains **38,720 pixels (99.61%, 1548.80 ha)**. See [all observed values](reports/time-series.csv) and [execution manifest](reports/run-manifest.json).

![Index evolution](reports/figures/index-time-series.png)

The curves summarize the same pixels at every date. Shading is the spatial 10–90% range, not confidence intervals. A seasonal rise and decline in greenness is consistent with changing vegetation cover, but these data alone do not identify crops or diagnose drought. Scene cloud percentage describes the full source tile; ROI coverage is calculated independently.

## Run locally

Python 3.12 is required. Until daily publication, clone the supplied local repository or use its source archive. After publication, the same commands apply to its GitHub clone.

```bash
python -m venv .venv
# Activate .venv using your platform's command.
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
python -m satellite.cli run
python -m pytest -q
python -m ruff check .
```

No API token or paid account is needed. The first run reads public COG windows; later runs use ignored ROI caches. Source imagery and generated GeoTIFFs remain local under `data/raw` and `data/processed`. A changed manifest, configuration or calibration fingerprint raises an error rather than silently reusing stale cache. Remove only obsolete cache files explicitly.

`python -m satellite.cli discover` prints newly discovered scene IDs without modifying the frozen study. Inspect [the executed notebook](notebooks/01_inspection.ipynb), [verification](docs/verification.md), [French learning guide](docs/learning-guide.md), [interview notes](docs/interview-notes.md) and [design](docs/design.md).

## Structure and technologies

`src/satellite`: catalog, raster alignment, indices, pipeline and CLI. `configs`: study parameters. `data`: frozen metadata and ignored imagery. `reports`: actual statistics and figures. `tests`: numeric, mask, grid and GeoTIFF contracts. Python, NumPy, pandas, Rasterio/GDAL, matplotlib, pytest and GitHub Actions.

## Limitations and next work

Seven carefully selected clear observations undersample rapid events and do not measure monthly means. A rectangular landscape is not a crop-only mask; SCL can misclassify and bilinear resampling mixes boundaries. Sentinel reflectance and indices are proxies, not physiological measurements. Add independent parcel/crop labels, additional years and field measurements before interpreting crop-specific anomalies. No accuracy metric is applicable because there is no labeled prediction task.

Developed with AI assistance. Results come from executed public data, with no invented observations or backdated history. Public GitHub CI will be checked on the scheduled publication day; it has not yet run for this local repository.


## GitHub publication

[Public repository](https://github.com/idrisslemnouni-crypto/satellite-crop-monitoring) · [Current CI results](https://github.com/idrisslemnouni-crypto/satellite-crop-monitoring/actions). Published following the user's explicit 5 October 2026 request to release the prepared portfolio together. Earlier local-verification notes describe the pre-publication checkpoint. Raw sources and trained artifacts remain excluded from Git; reproduction commands regenerate them.
