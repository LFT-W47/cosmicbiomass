# Project State

Last updated: 2026-06-16

## Current priorities

- TODO: What is actively in flight? The working tree is clean at `main` (v0.2.3) with the two
  most recent bugfixes released, so there is no obvious in-progress work to infer from the
  repo. Maintainer to fill in current focus.

## Recent changes

- 2026-06-10: **v0.2.3** — out-of-coverage years are clamped to an available layer by default
  (`anchor_year="nearest"`) instead of raising; footprint CRS is now resolved dynamically
  rather than hardcoded to `EPSG:32632`. See `CHANGELOG.md` (issues #1, #2).
- 2026-06-03: **v0.2.2** — removed the vendored "custom Cubo"; rely on upstream `cubo`.
- 2026-02-06: **v0.2.1** — corrected `_deg_to_m_grid`, streamlined `stackstac` integration,
  added Earth Engine auth instructions.

## Open questions

- README's API reference lists `get_average_biomass(... radius=500 ...)`, but the implementation
  in `core.py` defaults `radius=200.0`. TODO: confirm the intended default and align docs/code.

## Decisions made

- **Footprint CRS is resolved dynamically, never hardcoded.** Order of preference:
  `data.rio.crs` → cubo's `attrs["epsg"]` → UTM zone derived from the requested center. Fixes
  zero-pixel results for sites outside UTM 32N. (CHANGELOG 0.2.3, issue #1.)
- **Out-of-coverage years clamp to the nearest available layer by default.** Vegetation indices
  carry the seasonality; `anchor_year=None` disables the fallback. (CHANGELOG 0.2.3, issue #2.)
- **Rely on upstream `cubo`** rather than a vendored fork. (CHANGELOG 0.2.2.)
- **Dependency version policy:** track minimum supported versions, avoid strict upper bounds;
  pin a specific package only when a breaking change appears. (README.)
