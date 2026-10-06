# Local verification — 5 October 2026

Seven fixed public COG scenes were processed with calibration version 2. Nine contract tests, Ruff lint/format and notebook schema validation passed. The inspection notebook was actually executed. The map montage was visually inspected: common-scale georeferenced landscape patterns and date labels are legible. Source SHA hashes, grid and coverage are recorded in reports/run-manifest.json.

A separate clean Python 3.12 virtual environment was installed from scoped dependencies. A local Git clone was installed editable; pip check passed, all nine tests passed, and all seven scenes were independently read again from public HTTPS COG assets. Band arrays and summary CSV reproduce within atol=rtol=1e-7; no raw cache was copied into the clone. Windows temporary-directory cleanup warnings did not fail assertions.

The notes above describe the pre-publication checkpoint. The existing public repository and actual software checks are linked in [GitHub Actions](https://github.com/idrisslemnouni-crypto/satellite-crop-monitoring/actions). No external deployment or field validation is claimed. Data and generated GeoTIFFs remain local and ignored in Git; public source acquisition reproduces them.

## Cached ROI quality enhancement — 6 October 2026

The existing public repository was clean before this change. Using the workspace Python 3.12 environment with `PYTHONPATH=src`, the full suite passed **26 tests** and Ruff passed. Added cases cover calibrated nodata, overlapping rejection reasons, zero denominators, broadcastable shape mismatches, invalid SCL classes, exact common-support partitions, projected-metre area, absent/corrupt caches, historical mask mismatch, reproducible CSV/JSON and byte preservation. Synthetic fixtures test contracts only; no simulated scene result is reported as an observation.

The cache-only quality command was executed on all seven original NPZ scenes. Their SHA-256 hashes equal the historical run manifest; all four index-raster masks reproduce exactly. Every ROI contains 38,872 pixels, SCL class counts and ordered exclusion counts sum exactly, and common support remains **38,720 pixels (99.608973%, 1548.80 ha)**. Scene SCL rejection counts are 94, 78, 50, 10, 52, 0 and 0; no additional finite-band/index exclusions occur. The original run manifest, time-series CSV, both original figures, seven index GeoTIFFs and seven caches remained byte-for-byte unchanged; their hashes are recorded in the separate QA JSON.

Only separate `scene-quality.csv`, `scene-quality.json` and `figures/scene-quality.png` outputs were generated. The final figure was visually inspected for complete titles, dates, legends and readable count/fraction panels. This check establishes numerical/mask compatibility and presentation quality, not field accuracy. No new imagery was downloaded or model trained. Inspect the exact-commit GitHub Actions run for remote software evidence.
