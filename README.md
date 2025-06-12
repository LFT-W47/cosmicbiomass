# CosmicBiomass

A modern Python package for extracting and analyzing aboveground biomass density (AGBD) from satellite data sources with support for geospatial footprint weighting and statistical analysis.

## Features

- 🌍 **Geospatial biomass extraction** from DLR STAC data sources (2017-2023)
- 📊 **Footprint-weighted statistics** with circular, Gaussian, and CRNS weighting schemes  
- 🔬 **CRNS weighting function** implementing Schrön et al. (2017) for cosmic ray neutron sensing
- 🎯 **High precision analysis** with uncertainty quantification and outlier detection
- 🏗️ **Modular architecture** with pluggable data sources and processing components
- ✅ **89% test coverage** with comprehensive unit and integration tests
- 🐍 **Modern Python 3.10+** with type hints, Poetry dependency management, and `src/` layout

## Quick Start

### Installation

#### Option 1: Install from GitHub (Recommended)

```bash
# Install directly from GitHub using pip
pip install git+https://github.com/LFT-W47/cosmicbiomass.git

# Or install in development mode for contributions
pip install -e git+https://github.com/LFT-W47/cosmicbiomass.git#egg=cosmicbiomass
```

#### Option 2: Install with conda/mamba

```bash
# First install dependencies via conda
conda install -c conda-forge numpy xarray matplotlib pyproj

# Then install cosmicbiomass from GitHub
pip install git+https://github.com/LFT-W47/cosmicbiomass.git
```

#### Option 3: Development Installation

```bash
# Clone the repository
git clone https://github.com/LFT-W47/cosmicbiomass.git
cd cosmicbiomass

# Install Poetry if you haven't already
pip install poetry

# Install dependencies and package in development mode
poetry install
```

### Reproducible Workflow Example

Here's a complete example extracting biomass data at the TERENO Hohes Holz station:

```python
import cosmicbiomass

# TERENO Hohes Holz station coordinates
lat, lon = 52.09, 11.226  # degrees N, E
footprint_radius = 240    # meters

# Extract biomass data with 240m circular footprint
result = cosmicbiomass.get_average_biomass(
    lat=lat,
    lon=lon,
    radius=footprint_radius,
    source="dlr",
    dataset="agbd_2018"  # Available: 2017-2023
)

# Access results
biomass_mgha = result['summary']['mean_biomass_Mg_ha']
uncertainty_mgha = result['summary']['uncertainty_Mg_ha']

print(f"Mean AGBD: {biomass_mgha:.1f} ± {uncertainty_mgha:.1f} Mg/ha")
# Output: Mean AGBD: 202.6 ± 27.8 Mg/ha

# Access detailed information
print(f"Footprint coverage: {result['footprint']['effective_pixels']} pixels")
print(f"Data source: {result['metadata']['source']}")
print(f"Dataset: {result['metadata']['dataset_id']}")
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

**Returns:**
Dictionary with biomass statistics, location info, and metadata.

#### `list_available_datasets(source="dlr")`

Get information about available datasets for a data source.

#### `validate_coordinates(lat, lon)`

Validate latitude/longitude coordinates are within valid ranges.

## Directory Structure

```
cosmicbiomass/
├── README.md
├── pyproject.toml              # Poetry configuration
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

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=cosmicbiomass --cov-report=html

# Run specific test modules
poetry run pytest tests/test_core.py -v
```

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
years = [2017, 2018, 2019, 2020, 2021, 2022, 2023]
biomass_time_series = []

for year in years:
    result = cosmicbiomass.get_average_biomass(
        lat=52.09, lon=11.226, 
        radius=240,
        dataset=f"agbd_{year}"
    )
    biomass_time_series.append({
        'year': year,
        'biomass': result['summary']['mean_biomass_Mg_ha'],
        'uncertainty': result['summary']['uncertainty_Mg_ha']
    })
```

## Data Sources

### DLR Global Aboveground Biomass Density

- **Coverage**: 2017-2023 annual products
- **Resolution**: 10m spatial resolution  
- **Units**: Mg/ha (megagrams per hectare)
- **Uncertainty**: Available via data spread analysis
- **Access**: STAC catalog via `cubo` integration

## Contributing

- Follow PEP 8 and modern Python best practices
- Add tests for new features (maintain >85% coverage)
- Use f-strings, pathlib, and type hints
- Run `poetry run pytest` before submitting changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Louis Ferdinand Trinkle
