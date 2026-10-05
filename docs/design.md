# Design and implementation plan — Satellite crop monitoring

Goal: reproducible geospatial monitoring of an Iowa agricultural landscape using seven real Sentinel-2 Collection-1 L2A scenes, one low scene-cloud-cover observation per month, April–October 2024. This is an index/quality-control study, not a trained stress detector.

Area: WGS84 bbox [-94.50, 41.40, -94.46, 41.44]. Grid: EPSG:32615, 20 m, snapped projected extent; all bands/dates align. Reflectance uses each asset's raster:bands scale/offset; raw DN nodata masked before conversion. Read only ROI blocks from public HTTPS COGs with certificate verification. Bilinear continuous-band resampling; nearest-neighbor SCL.

Quality: admit SCL 4/5/6 (vegetation, non-vegetated land, water); reject cloud, shadows, snow, unclassified and nodata. Monthly selection is not a monthly composite. Track clear-pixel fractions and counts. For cross-date statistics use the intersection of valid pixels across all dates, plus single-date statistics for coverage comparison. No crop mask or field labels are available, so the ROI is an agricultural landscape, not an identified crop parcel.

Indices: NDVI=(NIR−red)/(NIR+red); McFeeters NDWI=(green−NIR)/(green+NIR); NDMI=(NIR−SWIR1)/(NIR+SWIR1); SAVI=1.5*(NIR−red)/(NIR+red+0.5). SAVI requires scaled reflectance. Nonpositive denominators, nonfinite or negative reflectance are masked; physical index bounds checked. Negative values are masked conservatively rather than presented as physical reflectance.

Outputs: fixed scene manifest with source URLs and calibration; cropped raw cache ignored in Git; per-date GeoTIFFs (CRS, transform, nodata, units); common-support CSV; NDVI map montage with consistent scale; temporal index curves; manifest of actual pixel counts/checksums/versions. Changes are descriptive phenology/land-cover observations, not drought diagnoses.

Modules: catalog.py (discovery/frozen metadata), raster.py (alignment/calibration/masking), indices.py (mathematics), pipeline.py (statistics/georeferenced outputs/report), cli.py. Tests: offset before SAVI, zero denominators, categorical resampling, common support, fixed grid, bad metadata, nodata propagation, GeoTIFF roundtrip. One executed inspection notebook; README and French interview/learning guides; MIT code with separate Copernicus Sentinel terms for source data. No secrets, raw imagery or artificial metrics.

Plan: implement acquisition/index contracts → tests → execute all seven scenes → inspect real maps/statistics → document limitations → clean clone reproduction → publish and verify CI. Sources and processing are explicit; no request for a new credential or paid service is necessary.
