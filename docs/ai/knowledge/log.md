# Knowledge Log

Chronological history of important updates to `docs/ai/knowledge/`. Record:

- new concept/system/dataset/runbook pages,
- major restructures,
- substantial revisions to existing pages,
- ingestion of important raw material that changes the knowledge model.

Newest entries go at the top.

## Entry format

```md
## YYYY-MM-DD

- Added `path/to/file.md` — short note on what was added and why.
- Updated `path/to/file.md` — short note on what changed.
- Linked `path/to/file.md` ↔ `path/to/other.md` — short note on the new connection.
```

## 2026-06-17

- Updated `knowledge/datasets/dlr-agbd.md` — resolved the coverage/CRS TODO. Confirmed (by the
  maintainer) the dataset is **Germany only**, not "Global"; the real CRS spans UTM 32N
  (EPSG:32632) and 33N (EPSG:32633, eastern Germany). Documented the "Global" wording as a
  misnomer in the code/README.

## 2026-06-16

- Added `knowledge/concepts/crns-footprint-weighting.md` — CRNS/Schrön (2017) footprint shapes
  and CRS resolution.
- Added `knowledge/concepts/temporal-alignment.md` — `anchor_year` year resolution and
  reference-index alignment.
- Added `knowledge/systems/data-source-registry.md` — pluggable `BiomassDataSource` + registry.
- Added `knowledge/datasets/dlr-agbd.md` — the built-in DLR AGBD 2017–2023 source.
- Linked the four pages to each other and from `index.md`.
- Created `knowledge/index.md` and `knowledge/log.md` — established the knowledge layer.
