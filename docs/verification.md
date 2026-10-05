# Local verification — 5 October 2026

Seven fixed public COG scenes were processed with calibration version 2. Nine contract tests, Ruff lint/format and notebook schema validation passed. The inspection notebook was actually executed. The map montage was visually inspected: common-scale georeferenced landscape patterns and date labels are legible. Source SHA hashes, grid and coverage are recorded in reports/run-manifest.json.

A separate clean Python 3.12 virtual environment was installed from scoped dependencies. A local Git clone was installed editable; pip check passed, all nine tests passed, and all seven scenes were independently read again from public HTTPS COG assets. Band arrays and summary CSV reproduce within atol=rtol=1e-7; no raw cache was copied into the clone. Windows temporary-directory cleanup warnings did not fail assertions.

No remote repository, GitHub CI run or external deployment exists yet. The local project is prepared for publication at most one per day, starting on 6 October. After creating the public repository, verify the actual CI before documenting its result. Data and generated GeoTIFFs remain local and ignored in Git; public source acquisition reproduces them.
