# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** While this project is in initial development (`0.y.z`), the public
> API should not be considered stable. Per SemVer clause 4, a minor version bump
> may include backwards-incompatible changes.

## [Unreleased]

### Fixed

- Footprint weighting no longer hardcodes `EPSG:32632`. For any site outside
  UTM zone 32N (longitude ≳ 12° E → UTM 33N), the footprint center was
  misprojected hundreds of kilometres from the data window, collapsing every
  weight to 0 ("0 effective pixels" and NaN biomass) despite valid data being
  present. `FootprintProcessor.compute_footprint_weights` now resolves the data
  CRS in order of preference: `data.rio.crs`, then cubo's `attrs["epsg"]`, then
  the UTM zone derived from the requested center. (#1)

### Changed

- `DLRBiomassSource.load_data` now persists the projection that `cubo` reports
  in `attrs["epsg"]` onto the dataset via `rio.write_crs`, so downstream
  consumers see a populated `rio.crs`.
- The footprint CRS fallback derives the UTM zone from the requested center
  (the same zone `cubo` selects) instead of a fixed zone, so no projection is
  ever hardcoded.

## [0.2.2] - 2026-06-03

### Changed

- Removed the vendored "custom Cubo"; rely on the upstream `cubo` package.

## [0.2.1] - 2026-02-06

### Fixed

- Corrected the `_deg_to_m_grid` function and improved logging for CRNS weights.
- Streamlined the `stackstac` integration and removed redundant imports.

### Documentation

- Added Earth Engine authentication instructions.

## [0.2.0] - 2026-02-04

### Added

- Timezone harmonization for seasonal biomass time series.

### Changed

- Updated output column naming.

## [0.1.9] - 2026-02-04

### Fixed

- Timezone awareness in biomass time series.

## [0.1.8] - 2026-02-04

### Added

- Output units and timestamp handling in the biomass functions.

### Documentation

- README updates.

## [0.1.7] - 2026-01-23

### Changed

- `get_average_biomass_timeseries` now includes dataset attributes and returns
  an improved DataFrame structure.

## [0.1.6] - 2026-01-23

### Added

- `return_format` option for `get_average_biomass` and
  `get_average_biomass_timeseries` (default: `pandas.DataFrame`).
- Type stubs for pandas, scipy, and shapely (development dependencies).

### Fixed

- Test fixes.

## [0.1.5] - 2026-01-22

### Changed

- Use a `cubo` build compatible with NumPy 2.0.

## [0.1.4] - 2026-01-21

### Fixed

- Added git installation to the CI `before_script`.
- Reordered import statements for consistency across test modules.

## [0.1.3] - 2026-01-21

### Changed

- Moved toward Python 3.14 support and a NumPy-safe `cubo` version.

## [0.1.2] - 2026-01-20

### Changed

- Updated the dependency version policy.

## [0.1.1] - 2026-01-20

Initial public release.

### Added

- Core CosmicBiomass package: configuration, data-source registry, and the DLR
  Global Aboveground Biomass Density source (AGBD 2017–2023) via STAC/`cubo`.
- One-liner API: `get_average_biomass` and `get_average_biomass_timeseries`
  (multi-year analysis).
- Footprint shapes: circular, gaussian, and CRNS weighting following
  Schrön et al. (2017).
- Seasonal interpolation through remote-sensing vegetation indices (VIs).
- `ruff` linting, MIT License, and a README with usage examples and API
  reference.

[Unreleased]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.2.2...HEAD
[0.2.2]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.2.1...v0.2.2
[0.2.1]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.2.0...v0.2.1
[0.2.0]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.9...v0.2.0
[0.1.9]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.8...v0.1.9
[0.1.8]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.7...v0.1.8
[0.1.7]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.6...v0.1.7
[0.1.6]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.5...v0.1.6
[0.1.5]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.4...v0.1.5
[0.1.4]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.3...v0.1.4
[0.1.3]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.2...v0.1.3
[0.1.2]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/compare/v0.1.1...v0.1.2
[0.1.1]: https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass/-/tags/v0.1.1
