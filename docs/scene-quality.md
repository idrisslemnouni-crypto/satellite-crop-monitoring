# Cached ROI quality audit — design and implementation plan

The authorized enhancement is a separate, cache-only audit of the frozen seven-scene study. Its command reads existing NPZ caches and index GeoTIFFs, validates their calibration/configuration fingerprints and historical hashes, and reproduces the original masks. It writes only `reports/scene-quality.csv`, `reports/scene-quality.json` and `reports/figures/scene-quality.png`.

Each ROI is partitioned in this order: rejected SCL; allowed SCL with any nonfinite calibrated band; allowed SCL with finite bands but any undefined index; scene-valid pixels. Scene-valid pixels then split into shared support and pixels excluded from shared support by another date. These counts must sum exactly. Per-band and per-index diagnostic counts can overlap; they are not another partition. Full SCL counts are retained.

Grid shape, categorical SCL values, historical per-scene masks and common support must agree. Areas use the affine pixel determinant only when the CRS is projected in metres. Fractions/counts remain available for other grids. The executed frozen study must reproduce 38,720 common pixels; its original reports and GeoTIFFs stay byte-for-byte unchanged. QA measures data support, not crop identity, diagnosed stress or field accuracy.

Implementation plan:

1. Add pure array validation/partition functions and meaningful synthetic shape, calibrated-nodata, zero-denominator, overlap and support tests.
2. Add the cache-only runner and `quality` CLI command, verify fingerprints/hashes/grid/masks before writing, and record actual hashes and SCL counts.
3. Run the full tests and Ruff using the existing workspace virtual environment with `PYTHONPATH=src`; run the audit on the seven cached scenes and inspect its figure.
4. Document actual counts, command, interpretation and local verification. Check the original artifact hashes after execution. Leave changes uncommitted for root review.
