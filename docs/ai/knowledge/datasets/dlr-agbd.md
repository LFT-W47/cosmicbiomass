# DLR Aboveground Biomass Density (AGBD)

The one built-in data source. `DLRBiomassSource` serves annual aboveground biomass density
products (2017–2023) from the DLR STAC catalog, fetched as small xarray windows via `cubo`.
This page documents the dataset's shape, access path, bands, and the CRS quirk every consumer
must know about.

## Source facts (from `sources/dlr.py`)

| Property | Value |
|----------|-------|
| STAC endpoint | `https://geoservice.dlr.de/eoc/ogc/stac/v1` |
| Collection | `FOREST_STRUCTURE_DE_AGBD_P1Y` |
| Datasets | `agbd_2017` … `agbd_2023` (one annual product per year) |
| Spatial resolution | 10 m |
| Units | `Mg/ha` (megagrams per hectare) |
| Data format | GeoTIFF COG, processing level L3 |
| Uncertainty | Reported as available per `DatasetInfo`; see band detection below |

> TODO: The collection id and `DatasetInfo.crs` (`EPSG:32632`, UTM 32N) imply **German**
> coverage, but the README/docstrings call this "DLR **Global** Aboveground Biomass Density".
> Confirm the true geographic extent and align the wording.

## How a window is loaded

`load_data(dataset_id, bbox)`:

1. Validates `dataset_id` against `get_available_datasets()` and parses the year with
   `dataset_id.split("_")[1]`.
2. Derives an `edge_size` in metres from `bbox` (reprojected via `EPSG:3857`); with no `bbox`
   it defaults to a **2000 m** window centred on **Hohes Holz (52.09 N, 11.226 E)**.
3. Calls `cubo.create(...)` with `stac`, `collection`, `gee=False`, `start_date`/`end_date`
   `{year}-01-01`…`{year}-12-31`, `edge_size`, `units="m"`, `resolution=10`.
4. **Persists the CRS:** `cubo` records its chosen UTM zone in `attrs["epsg"]` but does **not**
   set `rio.crs`. The loader calls `ds.rio.write_crs(f"EPSG:{epsg}")` so downstream footprint
   weighting projects into the correct zone (CHANGELOG 0.2.3, issue #1).

### CRS caveat

`DatasetInfo.crs` is a nominal `EPSG:32632`, but the **real** CRS of a loaded window is whatever
UTM zone `cubo` picks for the requested centre. Always trust `data.rio.crs` /
`attrs["epsg"]` over the static `DatasetInfo.crs`. See
[`../concepts/crns-footprint-weighting.md`](../concepts/crns-footprint-weighting.md) for why this
matters.

## Bands / variables

- Primary biomass variable: **`agbd_cog`** (selected in `core.py` and `statistics.py`).
- Uncertainty band is auto-detected from candidates, in order:
  `agbd_cog_uncertainty`, `uncertainty`, `std`, `stderr`. If none is present, uncertainty is
  **estimated from the weighted data spread** (`uncertainty_source = "data_spread"` vs
  `"uncertainty_band"`).

## Year handling

A multi-year request fills the `agbd_{year}` template per year. Years outside 2017–2023 are, by
default, clamped to the nearest available product layer rather than raising — see
[`../concepts/temporal-alignment.md`](../concepts/temporal-alignment.md).

## Related links

- Code: [`sources/dlr.py`](../../../../src/cosmicbiomass/sources/dlr.py),
  [`core.py`](../../../../src/cosmicbiomass/core.py)
- [`../systems/data-source-registry.md`](../systems/data-source-registry.md) — how this source is registered
- [`../concepts/crns-footprint-weighting.md`](../concepts/crns-footprint-weighting.md) — CRS dependency
- [`../concepts/temporal-alignment.md`](../concepts/temporal-alignment.md) — multi-year / out-of-coverage handling
