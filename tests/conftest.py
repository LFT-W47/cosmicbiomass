"""
Pytest configuration and shared fixtures for cosmicbiomass tests.

This module provides common fixtures and configuration for all tests,
following modern pytest best practices and supporting both unit and
integration testing scenarios.
"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest
import xarray as xr

# Import the package for testing
import cosmicbiomass
from cosmicbiomass.config import BiomassConfig, FootprintConfig
from cosmicbiomass.sources.base import DatasetInfo


@pytest.fixture(scope="session")
def sample_coordinates():
    """Sample coordinates for testing - TERENO Hohes Holz station."""
    return {
        "lat": 52.09,  # TERENO Hohes Holz, Germany
        "lon": 11.226,
        "radius": 240.0,
    }


@pytest.fixture(scope="session")
def edge_coordinates():
    """Edge case coordinates for testing validation."""
    return [
        {"lat": 90.0, "lon": 0.0, "radius": 100.0},  # North Pole
        {"lat": -90.0, "lon": 180.0, "radius": 50.0},  # South Pole
        {"lat": 0.0, "lon": -180.0, "radius": 300.0},  # Equator
    ]


@pytest.fixture(scope="session")
def invalid_coordinates():
    """Invalid coordinates for testing error handling."""
    return [
        {"lat": 91.0, "lon": 0.0, "radius": 100.0},  # Invalid lat
        {"lat": 0.0, "lon": 181.0, "radius": 100.0},  # Invalid lon
        {"lat": 50.0, "lon": 10.0, "radius": -100.0},  # Invalid radius
        {"lat": 50.0, "lon": 10.0, "radius": 0.0},  # Zero radius
    ]


@pytest.fixture
def sample_config():
    """Sample BiomassConfig for testing."""
    return BiomassConfig(
        data_dir="test_data",
        resolution=10,
        stac_url="https://test.stac.catalog/v1"
    )


@pytest.fixture
def sample_footprint_config():
    """Sample FootprintConfig for testing."""
    return FootprintConfig(
        radius=240.0,
        shape="circular"
    )


@pytest.fixture
def sample_dataset_info():
    """Sample DatasetInfo for testing."""
    return DatasetInfo(
        id="test_agbd_2021",
        name="Test AGBD 2021",
        description="Test dataset for unit tests",
        spatial_resolution=100.0,
        temporal_coverage="2021",
        units="Mg/ha",
        uncertainty_available=True,
        crs="EPSG:32632"
    )


@pytest.fixture
def sample_biomass_data():
    """Sample biomass data for testing."""
    # Create realistic biomass data
    np.random.seed(42)  # For reproducible tests

    x_coords = np.arange(600000, 602000, 100)  # UTM coordinates
    y_coords = np.arange(5770000, 5772000, 100)

    # Simulate biomass values (100-250 Mg/ha)
    biomass_values = np.random.normal(175, 25, (len(y_coords), len(x_coords)))
    biomass_values = np.clip(biomass_values, 50, 300)  # Realistic range

    # Create DataArray
    data = xr.DataArray(
        biomass_values,
        dims=['y', 'x'],
        coords={
            'x': x_coords,
            'y': y_coords,
            'band': 'agbd_cog'
        },
        attrs={
            'units': 'Mg/ha',
            'description': 'Test aboveground biomass density'
        }
    )

    return data


@pytest.fixture
def sample_biomass_dataset():
    """Sample biomass dataset with multiple bands for testing."""
    np.random.seed(42)

    x_coords = np.arange(600000, 602000, 100)
    y_coords = np.arange(5770000, 5772000, 100)

    # Create multiple bands
    biomass_values = np.random.normal(175, 25, (len(y_coords), len(x_coords)))
    uncertainty_values = np.random.normal(15, 5, (len(y_coords), len(x_coords)))

    # Create dataset with multiple variables
    dataset = xr.Dataset({
        'agbd_cog': xr.DataArray(
            biomass_values,
            dims=['y', 'x'],
            coords={'x': x_coords, 'y': y_coords}
        ),
        'agbd_cog_uncertainty': xr.DataArray(
            uncertainty_values,
            dims=['y', 'x'],
            coords={'x': x_coords, 'y': y_coords}
        )
    })

    return dataset


@pytest.fixture
def sample_weights():
    """Sample footprint weights for testing."""
    # Create circular weights pattern
    size = 20
    center = size // 2
    weights = np.zeros((size, size))

    for i in range(size):
        for j in range(size):
            distance = np.sqrt((i - center)**2 + (j - center)**2)
            if distance <= 8:  # Radius of 8 pixels
                weights[i, j] = 1.0

    return weights


@pytest.fixture
def mock_data_source():
    """Mock data source for testing."""
    mock_source = Mock()

    # Mock methods
    mock_source.source_name = "mock"
    mock_source.get_available_datasets.return_value = {
        "test_dataset": DatasetInfo(
            id="test_dataset",
            name="Test Dataset",
            description="Mock dataset for testing",
            spatial_resolution=100.0,
            temporal_coverage="2021",
            units="Mg/ha"
        )
    }
    mock_source.get_metadata.return_value = {
        "source": "mock",
        "dataset_info": {
            "units": "Mg/ha",
            "spatial_resolution": 100.0,
            "temporal_coverage": "2021"
        }
    }

    return mock_source


@pytest.fixture
def suppress_warnings():
    """Suppress specific warnings during tests."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", UserWarning)
        yield


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests as unit tests by default
        if "integration" not in item.keywords and "slow" not in item.keywords:
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def mock_biomass_cube():
    """Create a mock xarray Dataset representing biomass data."""
    # Create synthetic biomass data
    x_coords = np.linspace(13.78, 13.80, 20)  # ~2km at this latitude
    y_coords = np.linspace(51.16, 51.18, 20)  # ~2km
    time_coords = ["2020-01-01", "2021-01-01", "2022-01-01"]

    # Synthetic biomass values (Mg/ha) with some spatial variation
    biomass_data = np.random.normal(150, 30, (len(time_coords), len(y_coords), len(x_coords)))
    biomass_data = np.clip(biomass_data, 0, 400)  # Realistic biomass range

    # Create xarray Dataset
    ds = xr.Dataset(
        {
            "agbd": (["time", "y", "x"], biomass_data, {
                "units": "Mg/ha",
                "long_name": "Above-ground biomass density",
                "description": "Synthetic test data"
            })
        },
        coords={
            "x": x_coords,
            "y": y_coords,
            "time": pd.to_datetime(time_coords)
        },
        attrs={
            "source": "Mock data for testing",
            "crs": "EPSG:4326"
        }
    )

    return ds


@pytest.fixture
def mock_fractional_weights():
    """Create mock fractional coverage weights."""
    # Circular pattern typical of footprint weighting
    size = 20
    center = size // 2
    y, x = np.ogrid[:size, :size]

    # Distance from center
    distance = np.sqrt((x - center)**2 + (y - center)**2)

    # Circular weights with gradual falloff
    weights = np.maximum(0, 1 - distance / (size / 2))
    weights = weights.astype(np.float32)

    return weights


@pytest.fixture
def mock_dlr_source():
    """Create a mock DLR biomass source for testing."""
    source = Mock(spec=cosmicbiomass.DLRBiomassSource)
    source.stac_url = "https://test.stac.url"
    source.collection = "TEST_COLLECTION"
    source.start_date = "2020-01-01"
    source.end_date = "2023-12-31"
    source.resolution = 10

    # Mock methods
    source.get_source_info.return_value = {
        "name": "Mock DLR Source",
        "provider": "Test Provider",
        "units": "Mg/ha",
        "description": "Mock source for testing"
    }

    return source


@pytest.fixture
def mock_cubo_create(mock_biomass_cube):
    """Mock the cubo.create function to return synthetic data."""
    with patch('cosmicbiomass.cubo.create') as mock_create:
        mock_create.return_value = mock_biomass_cube
        yield mock_create


@pytest.fixture
def mock_rasterio_features():
    """Mock rasterio.features.rasterize for testing fractional coverage."""
    def mock_rasterize(shapes, out_shape, transform, fill=0, **kwargs):
        """Create a simple circular mask for testing."""
        height, width = out_shape
        center_y, center_x = height // 2, width // 2
        y, x = np.ogrid[:height, :width]

        # Simple circular mask
        radius = min(height, width) // 3
        mask = ((x - center_x)**2 + (y - center_y)**2) <= radius**2
        return mask.astype(np.float32)

    with patch('cosmicbiomass.features.rasterize', side_effect=mock_rasterize):
        yield


@pytest.fixture
def caplog_debug(caplog):
    """Capture debug logs for testing."""
    caplog.set_level(logging.DEBUG, logger="cosmicbiomass")
    return caplog


@pytest.fixture
def temp_config():
    """Create a temporary configuration for testing."""
    original_config = cosmicbiomass.config

    # Create test config with faster settings
    test_config = cosmicbiomass.CosmicBiomassConfig(
        default_upsample_factor=2,  # Faster for testing
        edge_size_buffer=1.2,       # Smaller buffer
        n_jobs=1,                   # Single threaded for deterministic tests
    )

    # Replace global config
    cosmicbiomass.config = test_config

    yield test_config

    # Restore original config
    cosmicbiomass.config = original_config


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    # Clear any existing handlers from previous tests
    logger = logging.getLogger("cosmicbiomass")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    yield

    # Clean up after test
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)


# Pytest markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.mock = pytest.mark.mock


# Session-scoped fixtures for expensive setup
@pytest.fixture(scope="session")
def test_data_dir():
    """Directory for test data files."""
    return Path(__file__).parent / "data"


