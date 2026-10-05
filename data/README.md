# Source data and rights

Catalog: https://earth-search.aws.element84.com/v1 . Frozen complete items: scene-manifest.json; collection metadata: collection.json. Source: Copernicus Sentinel-2 Collection-1 L2A, 2024, public Earth Search HTTPS cloud-optimized GeoTIFF assets. HTTPS certificate verification is enabled. Only the small ROI is read.

Source data are free and open under the custom Copernicus Sentinel legal notice, linked from https://dataspace.copernicus.eu/terms-and-conditions . The collection's license field is proprietary (custom terms), not the project's MIT code licence. Attribute Modified Copernicus Sentinel data (2024). Earth Search metadata/calibration documentation: https://github.com/Element84/earth-search/blob/main/README.md . Official product and SCL descriptions: https://sentiwiki.copernicus.eu/web/s2-products and https://sentiwiki.copernicus.eu/web/s2-processing .

No source rasters are committed. Reproduction downloads ROI blocks into raw/*.npz; derived four-band GeoTIFFs go to processed/. The run manifest contains hashes of local ROI caches, not independently verified checksums of complete source tiles. Keep source year, calibration and attribution with derived data.
