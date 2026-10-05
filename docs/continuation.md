# Checkpoint — 5 October 2026

The user requests one project per day. Do not publish this repository on 5 October or start later projects today. Resume this project on or after 6 October, complete it, publish at most this one repository, then stop for the day.

## Completed locally

- Frozen seven real public Earth Search Sentinel-2 C1 L2A items; no credentials required. ROI [-94.50, 41.40, -94.46, 41.44], grid EPSG:32615, 20 m, 172 × 226 pixels.
- Acquisition, calibration, SCL masking, index computation, common spatial support, CSV, georeferenced TIFFs and plots implemented.
- First real seven-scene execution completed. Existing reports are provisional because calibration was subsequently corrected.
- Fixed a float32 rounding issue where DN=1000 became a tiny negative reflectance and was masked. Calibration now computes in float64 before casting; cache fingerprint includes calibration_version=2.
- Nine tests pass; Ruff lint and format pass. Pytest emitted Windows temporary-directory cleanup warnings, unrelated to test assertions.
- No remote repository created, no push performed.

## Resume steps

1. Use the existing project workspace and virtual environment at ../../work/venv/Scripts/python.exe. Package is installed editable. Do not reset unrelated files.
2. Existing data/raw/*.npz use the old calibration fingerprint. Remove only these seven project-owned cache files using native PowerShell LiteralPath file operations. Do not recursively remove directories. Then run python -m satellite.cli run to regenerate imagery and all reports under the corrected calibration.
3. Inspect the real CSV, maps and run manifest. Clearly distinguish scene cloud cover from ROI coverage and the spatial quantile band from statistical confidence intervals. All cross-date summaries use the common valid footprint. No crop mask, stress labels, classification or accuracy claims.
4. Complete README, data provenance/licence documentation, French learning/interview notes, executed inspection notebook and CI. Do not claim full-tile source checksums have been verified; ROI cache hashes are computed locally.
5. Verify reproduction in a clean environment with scoped dependencies, run meaningful checks, inspect actual maps and retain evidence. Current reports are not yet final verified deliverables.
6. Commit actual changes, create idrisslemnouni-crypto/satellite-crop-monitoring public with gh, push to main, verify GitHub CI, add genuine improvement issues and create a source archive. gh is authenticated; the GitHub connector previously returned 403 for issue creation, so use the CLI. Never print authentication tokens.
7. Update ../portfolio-progress.json with the real publication date in Africa/Casablanca and URL; check GitHub for an already-published project first. Stop after this project. Do not build or publish the next project during the same day.

## Sources and interpretation

- Public catalog: https://earth-search.aws.element84.com/v1 ; collection sentinel-2-c1-l2a.
- Processing/calibration documentation: https://github.com/Element84/earth-search/blob/main/README.md ; https://sentiwiki.copernicus.eu/web/s2-products ; https://sentiwiki.copernicus.eu/web/s2-processing .
- Source collection specifies custom Sentinel terms (license field proprietary), not CC BY or MIT. Its legal-notice link is in data/collection.json. Verify an accessible official legal notice and attribute Modified Copernicus Sentinel data (2024).
- Bands carry scale=0.0001, offset=-0.1, raw nodata=0. Use these explicit metadata; Rasterio source defaults alone omit this calibration.
- SCL 4/5/6 are admitted. The common footprint includes vegetated/nonvegetated land and water; it is not a crop-only mask. Monthly dates are individual scenes, not monthly composites.
- There is no Docker execution capability established in this environment. Do not claim a container was tested or a service deployed without doing so.
