# Temporal Alignment & Year Resolution

The annual AGBD products only exist for a fixed set of years (2017–2023 for DLR), yet callers
want biomass attached to arbitrary time ranges and to high-frequency series (daily/hourly CRNS
data). The temporal helpers in `core.py` bridge that gap: they resolve which product layer each
requested year maps to, then align/forward-fill the annual values onto a target index. This
logic is non-obvious and was added across several releases (CHANGELOG 0.2.3, issue #2), so it
earns its own page.

## Where it lives

All in `src/cosmicbiomass/core.py`:

- `_build_dataset_id(dataset, year)` — turn a dataset spec + year into a concrete dataset id.
- `_available_years(source, data_dir)` — the product years a source actually exposes.
- `_resolve_anchor_for_year(anchor_year, year, available_years)` — fallback for out-of-coverage years.
- `_infer_target_index(...)` — choose the DatetimeIndex to align onto.
- `_coerce_year`, `_scale_series_by_year` — supporting helpers.

Used by `get_average_biomass_timeseries` and `get_seasonal_biomass_timeseries`.

## Dataset id resolution (`_build_dataset_id`)

| `dataset` argument | Behaviour |
|--------------------|-----------|
| `"agbd_{year}"` (template) | `{year}` is filled per year → `agbd_2019`, `agbd_2020`, … |
| `"agbd_2023"` (fixed year) | Returned **unchanged** — pins every year of the range to that one layer (with a warning) |
| `"agbd"` (no year) | Year appended → `agbd_2019` |

## Out-of-coverage years (`anchor_year`, default `"nearest"`)

When a requested year falls outside the source's real coverage, it is clamped to an available
layer instead of raising. `anchor_year` controls the fallback:

- `"nearest"` (default) — closest available year; ties prefer the **newer** year
  (`key = (abs(a - year), -a)`).
- `"latest"` — the most recent available year.
- a concrete year (int or year-like string) — pin to that layer.
- `None` — disable the fallback (no clamping).

Covered years always keep their own real layer; only out-of-coverage years are remapped, and the
remapping is reported in a single warning. In `get_seasonal_biomass_timeseries`, the vegetation
indices still carry the seasonality even when the AGBD layer is clamped.

## Aligning onto a target index (`_infer_target_index`)

Precedence for the output DatetimeIndex:

1. an explicit `reference_index` (a real `pd.DatetimeIndex`) — used verbatim,
2. else `target_frequency` (e.g. `"1D"`), or the frequency inferred from the VI series,
   spanning `start_time`-Jan-01 … `end_time`-Dec-31,
3. else the VI series' own index.

Annual AGBD values are then aligned to that index and **forward-filled within each year**. This
is how you attach AGBD to Neptoon CRNS timestamps (see the repo `README.md`).

### Do / Don't

- **Do** pass a real `pd.DatetimeIndex` as `reference_index` when aligning to an external series.
- **Don't** pass a frequency string (`"H"`, `"D"`) as `reference_index` — use a real index, or
  pass `target_frequency` instead.

## Related options

- `timestamp_index=True` switches the index from plain years to a year-anchored
  `DatetimeIndex` (`timestamp_anchor="year_start"`).
- `output_units` (`"Mg/ha"` default, or `"kg/m^2"`) scales the biomass columns.
- `_scale_series_by_year` min-max normalises a VI series per calendar year — the seasonality
  shape that `get_seasonal_biomass_timeseries` multiplies onto annual AGBD.

## Related links

- Code: [`core.py`](../../../../src/cosmicbiomass/core.py)
- [`../datasets/dlr-agbd.md`](../datasets/dlr-agbd.md) — the source whose coverage defines "in range"
- [`../../architecture.md`](../../architecture.md) — the timeseries/seasonal entry points
- `CHANGELOG.md` (0.2.3) — `anchor_year` and out-of-coverage handling (issue #2)
