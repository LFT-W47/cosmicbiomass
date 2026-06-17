# CosmicBiomass

A modern Python package for extracting and analyzing aboveground biomass density (AGBD) from satellite data sources with support for geospatial footprint weighting and statistical analysis.

Most users will want to attach annual AGBD to an existing higher-frequency time series.
Jump to: [Align to a Reference Time Index (daily/hourly)](#align-to-a-reference-time-index-dailyhourly)

## Features

- 🌍 **Geospatial biomass extraction** from DLR STAC data sources (2017-2023)
- 📊 **Footprint-weighted statistics** with circular, Gaussian, and CRNS weighting schemes
- 🔬 **CRNS weighting function** implementing Schrön et al. (2017) for cosmic ray neutron sensing
- 🎯 **High precision analysis** with uncertainty quantification and outlier detection
- 🏗️ **Modular architecture** with pluggable data sources and processing components
- ✅ **89% test coverage** with comprehensive unit and integration tests
- 🐍 **Modern Python 3.10+** with type hints, uv-managed environments, and `src/` layout

## Quick Start

### Installation

#### Option 1: PyPI

```bash
pip install cosmicbiomass
```

#### Option 2: Development install (uv)

```bash
# Clone the repository
git clone https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass.git
cd cosmicbiomass

# Create a virtual environment
uv venv .venv

# Activate the environment
source .venv/bin/activate

# Install the package in development mode
uv pip install -e .

# Lock dependencies for reproducibility
uv lock

```

### Dependency Version Policy

We track minimum supported versions and avoid strict upper bounds for most dependencies.
This keeps the project compatible with the newest stable releases and simplifies upgrades.
If a breaking change appears, we will pin that specific package until a fix is available.

### Reproducible Workflow Example

Here's a complete example extracting biomass data at the TERENO Hohes Holz station:

```python
import cosmicbiomass

# TERENO Hohes Holz station coordinates
lat, lon = 52.09, 11.226  # degrees N, E
footprint_radius = 240    # meters

# Extract biomass data with 240m circular footprint
df = cosmicbiomass.get_average_biomass(
    lat=lat,
    lon=lon,
    radius=footprint_radius,
    source="dlr",
    dataset="agbd_2018"  # Available: 2017-2023
)

# Access results (default return is a 1-row DataFrame)
biomass_mgha = df.iloc[0]["mean_biomass_Mg_ha"]
uncertainty_mgha = df.iloc[0]["uncertainty_Mg_ha"]

print(f"Mean AGBD: {biomass_mgha:.1f} ± {uncertainty_mgha:.1f} Mg/ha")
# Output: Mean AGBD: 202.6 ± 27.8 Mg/ha

# Access detailed information (full payload is stored in attrs)
result = df.attrs["result"]
print(f"Footprint coverage: {result['footprint']['effective_pixels']} pixels")
print(f"Data source: {result['data_info']['source']}")
print(f"Dataset: {result['data_info']['dataset']}")
```

### Available Datasets

```python
# List all available datasets
datasets = cosmicbiomass.list_available_datasets(source="dlr")
print("Available years:", list(datasets['datasets'].keys()))
# Output: ['agbd_2017', 'agbd_2018', 'agbd_2019', 'agbd_2020', 'agbd_2021', 'agbd_2022', 'agbd_2023']
```

## API Reference

### Core Functions

#### `get_average_biomass(lat, lon, radius=500, source="dlr", dataset="agbd_2021", **kwargs)`

Extract footprint-weighted biomass statistics for a location.

**Parameters:**

- `lat`, `lon` (float): Center coordinates in WGS84 decimal degrees
- `radius` (float): Footprint radius in meters (default: 500)
- `source` (str): Data source name (default: "dlr")
- `dataset` (str): Dataset identifier like "agbd_2018" (default: "agbd_2021")
- `footprint_shape` (str): "circular", "gaussian", or "crns" (default: "crns")
- `include_uncertainty` (bool): Include uncertainty estimation (default: True)
- `outlier_method` (str): "iqr", "zscore", or None for outlier detection
- `output_units` (str): "Mg/ha" (default) or "kg/m^2" (scales biomass columns)
- `timestamp_index` (bool): If True and a year can be inferred (DLR), index by a year-anchored DatetimeIndex

**Returns:**
By default, a 1-row pandas DataFrame. Use `return_format="dict"` for a dict payload.

#### `get_average_biomass_timeseries(...)`

Multi-year AGBD (annual products). By default returns a DataFrame indexed by year.

Key options:
- `output_units`: "Mg/ha" (default) or "kg/m^2"
- `timestamp_index=True`: switch the index to timestamps (year anchors)
- `reference_index=...`: when `timestamp_index=True`, align/forward-fill annual AGBD onto your target DatetimeIndex

#### `list_available_datasets(source="dlr")`

Get information about available datasets for a data source.

#### `validate_coordinates(lat, lon)`

Validate latitude/longitude coordinates are within valid ranges.

## Directory Structure

```
cosmicbiomass/
├── README.md
├── pyproject.toml              # Python project configuration
├── src/
│   └── cosmicbiomass/
│       ├── __init__.py         # Public API
│       ├── core.py             # Main analysis functions  
│       ├── config.py           # Configuration classes
│       ├── registry.py         # Data source management
│       ├── processing/         # Statistical and footprint processing
│       └── sources/            # Data source implementations
└── tests/                      # Comprehensive test suite (89% coverage)
```

## Dependency Lock

Use the lockfile for reproducible environments:

```bash
uv lock
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=cosmicbiomass --cov-report=html

# Run specific test modules
uv run pytest tests/test_core.py -v
```

## Publishing to PyPI

```bash
# Build wheel and sdist
uv build

# Publish to PyPI (requires credentials)
uv publish
```

## CI/CD (GitLab)

See [docs/CI_CD.md](docs/CI_CD.md) for the GitLab pipeline, runner tags, and release tag formats.


## Advanced Usage

### Custom Footprint Analysis

```python
# CRNS footprint (default) - Schrön et al. (2017) weighting
result = cosmicbiomass.get_average_biomass(
    lat=52.09, lon=11.226,
    radius=500,
    footprint_shape="crns",  # Cosmic ray neutron sensing weighting
    dataset="agbd_2020"
)

# Gaussian footprint with outlier detection
result_gaussian = cosmicbiomass.get_average_biomass(
    lat=52.09, lon=11.226,
    radius=500,
    footprint_shape="gaussian",
    outlier_method="iqr",
    dataset="agbd_2020"
)

# Access detailed footprint info
print(f"Effective pixels: {result['footprint']['effective_pixels']}")
print(f"Total weight: {result['footprint']['total_weight']:.1f}")
```

### Multi-year Analysis

```python
annual = cosmicbiomass.get_average_biomass_timeseries(
    lat=52.09,
    lon=11.226,
    radius=240,
    dataset="agbd_{year}",
    start_time="2017-01-01",
    end_time="2023-12-31",
)

# If you prefer a list of dicts (year/dataset/result payload):
series = cosmicbiomass.get_average_biomass_timeseries(
    lat=52.09,
    lon=11.226,
    radius=240,
    dataset="agbd_{year}",
    start_time="2017-01-01",
    end_time="2023-12-31",
    return_format="list",
)

```

### Align to a Reference Time Index (daily/hourly)

When attaching AGBD to a higher-frequency time series (e.g., Neptoon CRNS data),
pass a **DatetimeIndex** as `reference_index`. This aligns the annual values to
that index and forward-fills within each year. **Do not** pass a frequency
string like "H" or "D"—use a real index instead.

```python
# You need pandas for date_range and DatetimeIndex
import pandas as pd

# Example: align to a daily index
daily_index = pd.date_range("2017-01-01", "2023-12-31", freq="D", tz="UTC")

agbd_daily = cosmicbiomass.get_average_biomass_timeseries(
    lat=52.09,
    lon=11.226,
    radius=170,
    dataset="agbd_{year}",
    start_time="2017-01-01",
    end_time="2023-12-31",
    output_units="kg/m^2",
    timestamp_index=True,
    reference_index=daily_index,
)

### Example: align to Neptoon CRNS timestamps
from neptoon.io.read import DataHubFromConfig

# station_config_path has to provided by the user
hub_creator = DataHubFromConfig(path_to_sensor_config=station_config_path)
data_hub = hub_creator.create_data_hub()

# ...
# ...
# ...

crns_index = data_hub.crns_data_frame.index
lat = data_hub.crns_data_frame.latitude.unique()[0]
lon = data_hub.crns_data_frame.longitude.unique()[0]

agbd_on_crns = cosmicbiomass.get_average_biomass_timeseries(
    lat=lat,
    lon=lon,
    radius=170,
    dataset="agbd_{year}",
    start_time="2017-01-01",
    end_time="2023-12-31",
    output_units="kg/m^2",
    timestamp_index=True,
    reference_index=crns_index,
)

# Attach to Neptoon DataFrame (forward-fill is already applied by alignment)
data_hub.crns_data_frame["above_ground_biomass"] = agbd_on_crns["mean_biomass_kg_m2"]
```

### VI-driven Seasonal Interpolation (pandas output)

Use vegetation indices (LAI/EVI/NDVI) to create a higher-frequency biomass series. The
frequency is inferred from your VI data or you can provide one (e.g., "1H", "1D").

If you use LAI (GEE) via `vi_source="auto"`, `"gee+pc"`, or `"gee"`, you must authenticate
and initialize Earth Engine **before** calling `get_seasonal_biomass_timeseries()`:

```python
import ee

ee.Authenticate()
ee.Initialize()
```

```python
seasonal = cosmicbiomass.get_seasonal_biomass_timeseries(
    lat=52.09,
    lon=11.226,
    radius=170,
    dataset="agbd_{year}",
    start_time="2017-01-01",
    end_time="2023-12-31",
    target_frequency="1D",
    vi_source="auto",  # fetch LAI via GEE, EVI/NDVI via Planetary Computer
)

print(seasonal.head())
```
```

## Data Sources

### DLR Aboveground Biomass Density (Germany)

- **Coverage**: Germany only, 2017-2023 annual products
- **Resolution**: 10m spatial resolution
- **Units**: Mg/ha (megagrams per hectare)
- **Uncertainty**: Available via data spread analysis
- **Access**: STAC catalog via `cubo` integration

## Contributing

- Follow PEP 8 and modern Python best practices
- Add tests for new features (maintain >85% coverage)
- Use f-strings, pathlib, and type hints
- Run `uv run pytest` before submitting changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Louis Ferdinand Trinkle
