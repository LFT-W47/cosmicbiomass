# CosmicBiomass — Architecture Overview

Quick-reference map of the codebase for new sessions and new contributors.

## Component map

| Component | Purpose |
|-----------|---------|
| `src/cosmicbiomass/__init__.py` | Public API re-exports (`__all__`), package logging, version |
| `core.py` | Public API functions; orchestrates source → footprint → statistics |
| `config.py` | Pydantic config models: `BiomassConfig`, `FootprintConfig` |
| `registry.py` | `SourceRegistry` + `register_source` — register/resolve pluggable data sources |
| `sources/base.py` | `BiomassDataSource` ABC + `DatasetInfo` model (the source contract) |
| `sources/dlr.py` | `DLRBiomassSource` — DLR AGBD for Germany (2017–2023) via STAC + `cubo` |
| `sources/vi.py` | `fetch_vi_timeseries` — vegetation indices (LAI via Earth Engine; EVI/NDVI via Planetary Computer / `stackstac`) |
| `processing/footprint.py` | `FootprintProcessor.compute_footprint_weights` (circular/gaussian/CRNS) + `validate_footprint_coverage` |
| `processing/statistics.py` | `StatisticsProcessor` + `BiomassStatistics` — footprint-weighted stats, uncertainty, outlier detection |
| `tests/` | pytest suite + shared fixtures (`conftest.py`) |
| `cosmicbiomass_flowchart.py` | Standalone matplotlib diagram of the workflow (not imported by the package) |

## How it fits together

The public entry point is `get_average_biomass`; the timeseries and seasonal variants build on
the same pipeline.

```text
1. get_average_biomass(lat, lon, ...)  → validate coordinates, assemble BiomassConfig
2. registry.get_source("dlr")          → resolve the data source
3. source.load_data(dataset_id, bbox)  → fetch an xarray window via STAC/cubo (CRS persisted)
4. FootprintProcessor                  → weights over the window (CRNS by default; circular/gaussian)
5. StatisticsProcessor                 → footprint-weighted mean + uncertainty, optional outlier filtering
6. result                              → 1-row DataFrame (default) or dict payload (return_format="dict")
```

Extensions of this flow:

- `get_average_biomass_timeseries` — repeats step 1–6 per year over annual products; can align/
  forward-fill annual AGBD onto a caller-supplied `reference_index` (DatetimeIndex).
- `get_seasonal_biomass_timeseries` — drives a higher-frequency series by combining annual AGBD
  with vegetation-index seasonality from `sources/vi.py` (requires Earth Engine auth for LAI).

## Key design patterns

- **Pluggable data sources** — sources implement the `BiomassDataSource` ABC and are registered
  in `SourceRegistry`; `core.py` only talks to the registry, never a concrete source. New
  sources are added via `register_source`. See `registry.py` and `sources/base.py`.
- **Pydantic config models** — `BiomassConfig` / `FootprintConfig` validate inputs and carry
  settings through the pipeline. See `config.py`.
- **Footprint weighting schemes** — circular, Gaussian, and CRNS (cosmic-ray neutron sensing,
  per Schrön et al. 2017). CRNS is the default. *Knowledge page TODO — see
  [`knowledge/index.md`](knowledge/index.md).*
- **Dynamic CRS resolution** — footprint weights are computed in the data's real CRS, resolved
  in order: `data.rio.crs` → cubo's `attrs["epsg"]` → UTM zone derived from the requested
  center (never hardcoded). See `processing/footprint.py` and `CHANGELOG.md` (0.2.3).

## Entry points

- **Library / import:** `import cosmicbiomass; cosmicbiomass.get_average_biomass(lat, lon, ...)`
- **CLI:** none (no console scripts defined in `pyproject.toml`).
- **Diagram script:** `python cosmicbiomass_flowchart.py` (needs the `matplotlib` dev dependency).

## Related

- [`README.md`](README.md) — what this directory is
- [`knowledge/index.md`](knowledge/index.md) — deeper concept/system pages
- [`../../README.md`](../../README.md) — user-facing usage and full API reference
