# Data Source Registry

Biomass data sources are **pluggable**. Every source implements one abstract contract
(`BiomassDataSource`) and is registered by name in a `SourceRegistry`. The public API
(`core.py`) only ever asks the registry for a source by name — it never imports a concrete
source — so adding a new provider requires no changes to the core pipeline.

## Where it lives

- `src/cosmicbiomass/sources/base.py` — `BiomassDataSource` (ABC) and `DatasetInfo` (Pydantic).
- `src/cosmicbiomass/registry.py` — `SourceRegistry` and the module-level global registry +
  helper functions.
- `src/cosmicbiomass/sources/dlr.py` — the one built-in source, `DLRBiomassSource`.

## The source contract (`BiomassDataSource`)

A source subclasses the ABC and implements four members:

| Member | Responsibility |
|--------|----------------|
| `get_available_datasets() -> dict[str, DatasetInfo]` | Map dataset ids (e.g. `agbd_2021`) to metadata |
| `load_data(dataset_id, bbox=None) -> xr.Dataset` | Fetch the data window for a dataset id |
| `get_metadata(dataset_id) -> dict` | Return descriptive metadata |
| `source_name` (property) | Human-readable source name |

`DatasetInfo` is a Pydantic model (`id`, `name`, `description`, `spatial_resolution`,
`temporal_coverage`, `units`, `uncertainty_available`, `crs`).

## The registry (`SourceRegistry`)

- Holds two dicts: `_sources` (name → class) and `_instances` (name → cached instance).
- `register_source(name, cls)` — validates `issubclass(cls, BiomassDataSource)` and stores it
  under `name.lower()`. **Names are case-insensitive.**
- `get_source(name, config)` — returns a cached instance if one exists **and its `config`
  equals the requested config** (Pydantic value equality); otherwise instantiates `cls(config)`
  and caches it. Raises `ValueError` listing available names if `name` is unknown.
- `list_sources()` / `clear_cache()` — introspect / reset the instance cache.

A module-level `_global_registry` is created at import and **registers `"dlr"` →
`DLRBiomassSource`** in its constructor. The thin module functions wrap it:
`get_source`, `register_source`, `list_available_sources`, `clear_source_cache`.
`register_source` and `list_available_sources` are re-exported from the package root.

```text
core.get_average_biomass(..., source="dlr")
  └─ registry.get_source("dlr", config)   # core only talks to the registry
       └─ DLRBiomassSource(config).load_data(dataset_id, bbox) -> xr.Dataset
```

## Adding a new source

```python
import cosmicbiomass
from cosmicbiomass import BiomassDataSource

class MySource(BiomassDataSource):
    @property
    def source_name(self) -> str: ...
    def get_available_datasets(self): ...
    def load_data(self, dataset_id, bbox=None): ...
    def get_metadata(self, dataset_id): ...

cosmicbiomass.register_source("mysource", MySource)
df = cosmicbiomass.get_average_biomass(lat=..., lon=..., source="mysource", dataset="...")
```

### Gotchas

- **Instance caching is keyed by name + config equality.** Two calls with equal `BiomassConfig`
  reuse the same instance. If a source caches network state internally, call
  `clear_source_cache()` to force a fresh instance.
- Register the class, **not an instance** — `register_source` expects a `type`.

## Related links

- Code: [`registry.py`](../../../../src/cosmicbiomass/registry.py),
  [`sources/base.py`](../../../../src/cosmicbiomass/sources/base.py),
  [`sources/dlr.py`](../../../../src/cosmicbiomass/sources/dlr.py)
- [`../../architecture.md`](../../architecture.md) — the registry's place in the pipeline
- [`../datasets/dlr-agbd.md`](../datasets/dlr-agbd.md) — the built-in source's dataset
