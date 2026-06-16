# CosmicBiomass — Knowledge Index

Durable, cross-linked project knowledge for coding agents and human contributors. This is the
stuff that should survive individual sessions: how concepts and systems work, what the data
looks like, and how to perform recurring operations.

It complements — but does not replace:

- `../conventions/` — binding coding rules and anti-patterns,
- `../skills/` — reusable procedures,
- `../architecture.md` — the high-level code map,
- `../project-state.md` — the current state of active work.

## How to use this directory

- Start here when you need project knowledge beyond coding rules.
- Prefer updating an existing page over creating a near-duplicate.
- One concept / system / dataset / runbook per file.
- Cross-link related pages with relative Markdown links.
- Put transient working notes elsewhere (a plan dir or your tracker), not here.

## Pages

### Concepts — `concepts/`
Durable concepts used across the codebase.
- [CRNS Footprint Weighting](concepts/crns-footprint-weighting.md) — the default Schrön et al. (2017) footprint, the three shapes, and the CRS handling that makes weights valid.
- [Temporal Alignment & Year Resolution](concepts/temporal-alignment.md) — mapping requested years to product layers (`anchor_year`) and aligning annual AGBD onto a target time index.

### Systems — `systems/`
Major subsystems and how they interact.
- [Data Source Registry](systems/data-source-registry.md) — the pluggable `BiomassDataSource` contract and how `core.py` resolves sources by name.

### Datasets — `datasets/`
Input/reference data, schemas, fixtures.
- [DLR Aboveground Biomass Density (AGBD)](datasets/dlr-agbd.md) — the built-in 2017–2023 annual products: STAC/`cubo` access, bands, and the CRS caveat.

### Runbooks — `runbooks/`
Operational guides for recurring tasks.
- _none yet_

### Raw — `raw/`
Curated source material that feeds pages (notes, syntheses). Inputs, not canonical pages.
- _none yet_

## Core files

- [log.md](log.md) — chronological history of knowledge updates.

## Page-creation rules

Create a new page only if **all** are true:

1. the knowledge will likely matter again in future sessions,
2. it is broader than a single temporary plan,
3. it describes a concept / system / dataset / procedure — not a one-off decision or a code
   review comment,
4. it is substantial enough to deserve its own file (aim for 100+ words, clear structure).

Do **not** create a page for: quick debugging notes (use a plan dir or code comments),
single-session decisions (use git messages or an ADR in `../decisions/`), or code-only
problems (those belong in the code and its tests).
