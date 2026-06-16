# AGENTS.md — CosmicBiomass

CosmicBiomass is a Python library for extracting footprint-weighted aboveground biomass
density (AGBD) from satellite data sources (DLR Global AGBD via STAC/`cubo`), with circular,
Gaussian, and CRNS footprint weighting and statistical analysis.

This is the universal entry point for coding agents working on this repo. Read it first.
Deeper material lives under [`docs/ai/`](docs/ai/) — this file points there rather than
repeating it.

## Commands

This project is managed with [`uv`](https://docs.astral.sh/uv/). Run dev tools through `uv run`.

| Task | Command |
|------|---------|
| Install (dev) | `uv sync --group dev` |
| Test | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format | `uv run black .` |
| Type-check | `uv run mypy src` |
| Build (sdist + wheel) | `uv build` |

There is no CLI; the package is used as a library (`import cosmicbiomass`). CI runs
`uv sync --group dev --frozen`, `uv run ruff check .`, then `uv run pytest`.

## Layout

```text
src/cosmicbiomass/   — the package (public API in __init__.py / core.py)
  ├── config.py      — Pydantic config models
  ├── registry.py    — pluggable data-source registry
  ├── sources/       — data sources (DLR STAC/cubo; vegetation indices)
  └── processing/    — footprint weighting + weighted statistics
tests/               — pytest suite + fixtures (conftest.py)
docs/                — CI/CD docs + the agent/docs layer (docs/ai/)
cosmicbiomass_flowchart.py — standalone matplotlib workflow diagram
```

## Where to find more

- [`docs/ai/README.md`](docs/ai/README.md) — what the shared dir contains and how to add to it
- [`docs/ai/architecture.md`](docs/ai/architecture.md) — module map and how the pieces fit
- [`docs/ai/project-state.md`](docs/ai/project-state.md) — current priorities and recent changes
- [`docs/ai/conventions/`](docs/ai/conventions/) — coding rules (style, tooling, tests)
- [`docs/ai/knowledge/`](docs/ai/knowledge/) — durable concept/system/runbook pages
- [`docs/CI_CD.md`](docs/CI_CD.md) — GitLab pipeline, runner tags, release/tag workflow

## Working agreement

- Follow the conventions in [`docs/ai/conventions/`](docs/ai/conventions/); match the style of
  surrounding code.
- Public functions are fully type-hinted — `mypy` runs in strict mode (see `pyproject.toml`).
- Add tests for new features and keep coverage above 85% (`uv run pytest`).
- When bumping the version, update it in **both** `pyproject.toml` and
  `src/cosmicbiomass/__init__.py`, and add a `CHANGELOG.md` entry (see [`docs/CI_CD.md`](docs/CI_CD.md)).
- Don't commit, tag, or push unless asked; releases are tag-driven and human-initiated.
- When a structural change lands, update the docs layer (see the
  [`structural_doc_update`](docs/ai/skills/structural_doc_update.md) skill).
