# Satellite crop monitoring — work in progress

Local checkpoint for a reproducible Sentinel-2 study of an Iowa agricultural landscape. This repository has not been published. The portfolio is being built one project per day, starting with this project on 6 October 2026.

The frozen [scene manifest](data/scene-manifest.json) contains seven real public Sentinel-2 Collection-1 L2A scenes from April–October 2024. The pipeline aligns reflectance bands and scene classification to EPSG:32615 at 20 m, applies scale and offset from STAC metadata, masks cloud and shadows, and calculates NDVI, NDWI, NDMI and SAVI. It describes landscape seasonality; crop labels and field measurements are unavailable.

See the [design](docs/design.md) and [continuation checkpoint](docs/continuation.md). Final results, reproduction instructions and learning guides will be added after verification.

Code was developed with AI assistance. Code uses the MIT licence; Copernicus source data have separate terms.
