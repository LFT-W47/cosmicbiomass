# CRNS Footprint Weighting

CosmicBiomass never reports a plain spatial average. It weights every pixel in the data window
by a **footprint function** centred on the requested coordinate, then computes weighted
statistics. The default footprint is **CRNS** — the cosmic-ray-neutron-sensing weighting of
Schrön et al. (2017) — so the biomass value matches the area a CRNS sensor actually "sees".
This page explains the three footprint shapes, the CRNS formula, and the CRS handling that
makes or breaks the result.

## Where it lives

- `src/cosmicbiomass/processing/footprint.py` — `FootprintProcessor.compute_footprint_weights`
  and the three shape methods.
- `src/cosmicbiomass/config.py` — `FootprintConfig` (`radius` > 0, `shape` ∈
  {`circular`, `gaussian`, `crns`}, default `crns`).
- Weights are consumed by `StatisticsProcessor.compute_weighted_statistics` in
  `processing/statistics.py` (weighted mean/variance/median via `np.average` and a weighted
  percentile).

## How it works

1. Pull the spatial coordinate arrays from the dataset — projected `(x, y)` or geographic
   `(lon, lat)`.
2. **Resolve the data CRS** (this is the critical step — see below).
3. Transform the requested `(center_lon, center_lat)` (always WGS84 input) into the data CRS,
   then build a distance grid `distances = sqrt((X - cx)^2 + (Y - cy)^2)`. For projected data
   these distances are in **metres**.
4. Convert distances → weights using the chosen shape.
5. Report diagnostics: `total_weight = sum(weights)` and `effective_pixels` = count of pixels
   whose weight exceeds 1 % of the max weight.

### The three shapes

| Shape | Weight as a function of distance `r` (metres) |
|-------|-----------------------------------------------|
| `circular` | `1.0` for `r ≤ radius`, else `0` |
| `gaussian` | `exp(-0.5 (r/σ)^2)` with `σ = radius / 2` (radius ≈ 2σ ≈ 95 %); optional hard cutoff at `radius` |
| `crns` (default) | Schrön et al. (2017), below |

### CRNS formula (`_crns_footprint`)

```text
W(r) = 30 * exp(-r / 1.6) + exp(-r / 100)
weight(r) = W(r) / max(r, 1)        # max(r,1) avoids divide-by-zero near the centre
weight = 0 where r > radius          # radius acts as a hard cutoff
```

Reference: Schrön et al. (2017), as applied in Fersch et al. (2018). The constants (`1.6`,
`100`) assume `r` is in **metres**, which is why the CRS resolution below matters.

## CRS resolution — the thing that silently breaks

`compute_footprint_weights` resolves the data CRS in this order of preference (see
`footprint.py` and `CHANGELOG.md` 0.2.3, issue #1):

1. `data.rio.crs` — set by the DLR loader via `rio.write_crs` (see
   [`../datasets/dlr-agbd.md`](../datasets/dlr-agbd.md)),
2. `data.attrs["epsg"]` — where `cubo` records its chosen UTM zone,
3. the UTM zone **derived from the requested centre** (`_utm_epsg_from_lonlat`) — the same zone
   `cubo` would pick — as a last resort for projected `(x, y)` data,
4. `EPSG:4326` only when the data is genuinely geographic `(lon, lat)`.

### Do / Don't

- **Do** make sure projected datasets carry a CRS (`data.rio.crs` or `attrs["epsg"]`). The DLR
  source does this for you.
- **Don't** assume a fixed UTM zone. Hardcoding `EPSG:32632` (the old bug) misprojects the
  centre hundreds of km away for any site east of ~12° E (UTM 33N), collapsing **every** weight
  to 0 → "0 effective pixels" and NaN biomass despite valid data.

**Symptom → cause:** `effective_pixels == 0` or NaN mean almost always means the centre was
projected into the wrong CRS, or `radius` is too small relative to the 10 m pixel grid.

## Related links

- Code: [`processing/footprint.py`](../../../../src/cosmicbiomass/processing/footprint.py),
  [`processing/statistics.py`](../../../../src/cosmicbiomass/processing/statistics.py),
  [`config.py`](../../../../src/cosmicbiomass/config.py)
- [`../../architecture.md`](../../architecture.md) — where footprint weighting sits in the pipeline
- [`../datasets/dlr-agbd.md`](../datasets/dlr-agbd.md) — the dataset whose CRS this depends on
- `CHANGELOG.md` (0.2.3) — the dynamic-CRS fix (issue #1)
