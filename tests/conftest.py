"""
Pytest configuration and shared fixtures for cosmicbiomass tests.

This module provides common fixtures and configuration for all tests,
following modern pytest best practices and supporting both unit and
integration testing scenarios.
"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Any

import numpy as np
import pytest
import xarray as xr
from shapely.geometry import Point

# Import the package for testing
import cosmicbiomass


@pytest.fixture(scope="session")
def sample_coordinates():
    """Sample coordinates for testing - location in Germany with forest coverage."""
    return {
        "lat": 51.1657,  # Dresden, Germany
        "lon": 13.7882,
        "footprint_radius": 220.0,
    }


@pytest.fixture(scope="session")
def edge_coordinates():
    """Edge case coordinates for testing validation."""
    return [
        {"lat": 90.0, "lon": 0.0, "footprint_radius": 100.0},  # North Pole
        {"lat": -90.0, "lon": 180.0, "footprint_radius": 50.0},  # South Pole
        {"lat": 0.0, "lon": -180.0, "footprint_radius": 300.0},  # Equator
    ]


@pytest.fixture(scope="session")
def invalid_coordinates():
    """Invalid coordinates for testing error handling.""" 
    return [
        {"lat": 91.0, "lon": 0.0, "footprint_radius": 100.0},  # Invalid lat
        {"lat": 0.0, "lon": 181.0, "footprint_radius": 100.0},  # Invalid lon
        {"lat": 50.0, "lon": 10.0, "footprint_radius": -100.0},  # Invalid radius
        {"lat": 50.0, "lon": 10.0, "footprint_radius": 0.0},  # Zero radius
    ]


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


# Import pandas here for the mock_biomass_cube fixture
import pandas as pd
