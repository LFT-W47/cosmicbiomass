"""
Test utilities and helpers for cosmicbiomass tests.

This module provides common utilities, mock factories, and test data generators
that are used across multiple test modules.
"""

from typing import Any
from unittest.mock import Mock

import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import Point, Polygon

import cosmicbiomass


class MockDataFactory:
    """Factory for creating mock test data."""

    @staticmethod
    def create_biomass_cube(
        lat: float = 51.0,
        lon: float = 13.0,
        width: int = 20,
        height: int = 20,
        resolution: float = 10.0,  # meters
        biomass_range: tuple[float, float] = (50.0, 300.0),
        add_temporal: bool = True,
        add_noise: bool = True,
        seed: int = 42
    ) -> xr.Dataset:
        """
        Create a synthetic biomass data cube for testing.

        Args:
            lat: Center latitude
            lon: Center longitude
            width: Number of pixels in x direction
            height: Number of pixels in y direction
            resolution: Pixel resolution in meters
            biomass_range: (min, max) biomass values in Mg/ha
            add_temporal: Whether to add temporal dimension
            add_noise: Whether to add spatial noise
            seed: Random seed for reproducibility

        Returns:
            xr.Dataset: Synthetic biomass data cube
        """
        np.random.seed(seed)

        # Calculate coordinate arrays
        # Convert resolution from meters to degrees (approximate)
        deg_per_meter = 1.0 / 111000  # Rough conversion
        x_extent = width * resolution * deg_per_meter / 2
        y_extent = height * resolution * deg_per_meter / 2

        x_coords = np.linspace(lon - x_extent, lon + x_extent, width)
        y_coords = np.linspace(lat - y_extent, lat + y_extent, height)

        # Create base biomass pattern
        min_biomass, max_biomass = biomass_range

        if add_noise:
            # Create spatially correlated biomass pattern
            y_grid, x_grid = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')

            # Radial pattern from center
            center_y, center_x = height // 2, width // 2
            distance = np.sqrt((x_grid - center_x)**2 + (y_grid - center_y)**2)

            # Higher biomass in center, lower at edges
            normalized_distance = distance / np.max(distance)
            base_pattern = max_biomass * (1 - 0.5 * normalized_distance)

            # Add random noise
            noise = np.random.normal(0, (max_biomass - min_biomass) * 0.1, (height, width))
            biomass_data = base_pattern + noise
        else:
            # Uniform biomass
            mean_biomass = (min_biomass + max_biomass) / 2
            biomass_data = np.full((height, width), mean_biomass)

        # Clip to valid range
        biomass_data = np.clip(biomass_data, min_biomass, max_biomass)

        # Create temporal dimension if requested
        if add_temporal:
            time_coords = pd.to_datetime(['2020-01-01', '2021-01-01', '2022-01-01'])
            # Add slight temporal variation
            temporal_data = np.stack([
                biomass_data * (1 + 0.05 * np.random.normal(0, 1, biomass_data.shape))
                for _ in time_coords
            ])
            data_dims = ["time", "y", "x"]
            coords = {"x": x_coords, "y": y_coords, "time": time_coords}
        else:
            temporal_data = biomass_data
            data_dims = ["y", "x"]
            coords = {"x": x_coords, "y": y_coords}

        # Create dataset
        ds = xr.Dataset(
            {
                "agbd": (data_dims, temporal_data, {
                    "units": "Mg/ha",
                    "long_name": "Above-ground biomass density",
                    "description": f"Synthetic test data (seed={seed})"
                })
            },
            coords=coords,
            attrs={
                "source": "MockDataFactory",
                "crs": "EPSG:4326",
                "resolution_m": resolution,
                "created_for": "cosmicbiomass testing"
            }
        )

        return ds

    @staticmethod
    def create_circular_weights(
        size: int = 20,
        center: tuple[int, int] = None,
        max_radius: float = None,
        falloff: str = "linear"
    ) -> np.ndarray:
        """
        Create circular fractional coverage weights.

        Args:
            size: Grid size (assumes square grid)
            center: (y, x) center coordinates, defaults to grid center
            max_radius: Maximum radius in pixels, defaults to size/3
            falloff: Type of falloff ("linear", "gaussian", "step")

        Returns:
            np.ndarray: 2D weight array with values in [0, 1]
        """
        if center is None:
            center = (size // 2, size // 2)
        if max_radius is None:
            max_radius = size / 3.0

        center_y, center_x = center
        y, x = np.ogrid[:size, :size]

        # Calculate distance from center
        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)

        if falloff == "linear":
            weights = np.maximum(0, 1 - distance / max_radius)
        elif falloff == "gaussian":
            sigma = max_radius / 3.0
            weights = np.exp(-(distance**2) / (2 * sigma**2))
        elif falloff == "step":
            weights = (distance <= max_radius).astype(float)
        else:
            raise ValueError(f"Unknown falloff type: {falloff}")

        return weights.astype(np.float32)

    @staticmethod
    def create_mock_dlr_source(**kwargs) -> Mock:
        """Create a mock DLR biomass source with realistic behavior."""
        source = Mock(spec=cosmicbiomass.DLRBiomassSource)

        # Set default attributes
        source.stac_url = kwargs.get("stac_url", "https://test.stac.url")
        source.collection = kwargs.get("collection", "TEST_COLLECTION")
        source.start_date = kwargs.get("start_date", "2020-01-01")
        source.end_date = kwargs.get("end_date", "2023-12-31")
        source.resolution = kwargs.get("resolution", 10)

        # Mock extract_cube method
        def mock_extract_cube(lat, lon, edge_size, **extract_kwargs):
            # Calculate grid size based on edge_size and resolution
            grid_size = max(10, int(edge_size / source.resolution))
            return MockDataFactory.create_biomass_cube(
                lat=lat, lon=lon, width=grid_size, height=grid_size,
                resolution=source.resolution
            )

        source.extract_cube.side_effect = mock_extract_cube

        # Mock get_source_info method
        source.get_source_info.return_value = {
            "name": "Mock DLR Forest Structure AGBD",
            "provider": "Mock German Aerospace Center (DLR)",
            "stac_url": source.stac_url,
            "collection": source.collection,
            "temporal_range": f"{source.start_date} to {source.end_date}",
            "resolution_m": source.resolution,
            "units": "Mg/ha",
            "description": "Mock above-ground biomass density for testing"
        }

        return source


class TestDatasets:
    """Pre-defined test datasets for common scenarios."""

    @staticmethod
    def forest_biomass_cube() -> xr.Dataset:
        """Typical forest biomass data cube."""
        return MockDataFactory.create_biomass_cube(
            lat=51.1657,  # Dresden, Germany
            lon=13.7882,
            width=30,
            height=30,
            biomass_range=(80.0, 250.0),  # Typical temperate forest
            seed=123
        )

    @staticmethod
    def sparse_biomass_cube() -> xr.Dataset:
        """Sparse vegetation biomass data cube."""
        return MockDataFactory.create_biomass_cube(
            lat=45.0,  # Generic location
            lon=10.0,
            width=25,
            height=25,
            biomass_range=(5.0, 50.0),  # Sparse vegetation
            seed=456
        )

    @staticmethod
    def high_biomass_cube() -> xr.Dataset:
        """High biomass data cube (tropical forest)."""
        return MockDataFactory.create_biomass_cube(
            lat=-5.0,  # Tropical location
            lon=-60.0,
            width=35,
            height=35,
            biomass_range=(200.0, 450.0),  # High tropical biomass
            seed=789
        )


class GeometryHelpers:
    """Utilities for geometric test data."""

    @staticmethod
    def create_test_geometries() -> dict[str, Any]:
        """Create various test geometries for footprint testing."""
        return {
            "small_circle": Point(0, 0).buffer(50),   # 50m radius
            "medium_circle": Point(0, 0).buffer(200), # 200m radius
            "large_circle": Point(0, 0).buffer(500),  # 500m radius
            "rectangle": Polygon([(-100, -50), (100, -50), (100, 50), (-100, 50)]),
            "complex_shape": Point(0, 0).buffer(100).difference(
                Point(50, 50).buffer(30)
            )  # Circle with hole
        }

    @staticmethod
    def create_coordinate_test_cases() -> dict[str, dict[str, float]]:
        """Create coordinate test cases for various locations."""
        return {
            "temperate_forest": {"lat": 51.1657, "lon": 13.7882},  # Dresden
            "tropical_forest": {"lat": -3.4653, "lon": -62.2159},  # Amazon
            "boreal_forest": {"lat": 64.0685, "lon": -21.0457},    # Iceland
            "mediterranean": {"lat": 41.9028, "lon": 12.4964},     # Rome
            "polar": {"lat": 78.2232, "lon": 15.6267},             # Svalbard
            "equator": {"lat": 0.0, "lon": 0.0},                   # Equator/Prime Meridian
        }


class ValidationHelpers:
    """Utilities for validating test results."""

    @staticmethod
    def validate_biomass_result(result: tuple[float, float],
                                expected_range: tuple[float, float] = (0.0, 1000.0)) -> bool:
        """
        Validate that a biomass result is reasonable.

        Args:
            result: (mean_biomass, uncertainty) tuple
            expected_range: (min, max) expected biomass range

        Returns:
            bool: True if result is valid
        """
        mean_biomass, uncertainty = result
        min_biomass, max_biomass = expected_range

        # Check types
        if not isinstance(mean_biomass, int | float) or not isinstance(uncertainty, int | float):
            return False

        # Check for NaN/inf
        if np.isnan(mean_biomass) or np.isnan(uncertainty):
            return False
        if np.isinf(mean_biomass) or np.isinf(uncertainty):
            return False

        # Check ranges
        if not (min_biomass <= mean_biomass <= max_biomass):
            return False
        if uncertainty < 0:
            return False

        return True

    @staticmethod
    def validate_fractional_weights(weights: np.ndarray) -> bool:
        """
        Validate fractional coverage weights.

        Args:
            weights: 2D array of fractional weights

        Returns:
            bool: True if weights are valid
        """
        # Check type and shape
        if not isinstance(weights, np.ndarray):
            return False
        if weights.ndim != 2:
            return False

        # Check value range
        if np.any(weights < 0) or np.any(weights > 1):
            return False

        # Check for NaN/inf
        if np.any(np.isnan(weights)) or np.any(np.isinf(weights)):
            return False

        return True

    @staticmethod
    def validate_biomass_cube(cube: xr.Dataset) -> bool:
        """
        Validate a biomass data cube.

        Args:
            cube: xarray Dataset representing biomass data

        Returns:
            bool: True if cube is valid
        """
        # Check that it's a Dataset
        if not isinstance(cube, xr.Dataset):
            return False

        # Check that it has data variables
        if len(cube.data_vars) == 0:
            return False

        # Check coordinate dimensions
        main_var = cube[list(cube.data_vars)[0]]
        if 'x' not in main_var.coords or 'y' not in main_var.coords:
            return False

        # Check data validity
        if np.any(np.isnan(main_var.values)):
            # Some NaN values might be acceptable, but not all
            if np.all(np.isnan(main_var.values)):
                return False

        return True


class LoggingHelpers:
    """Utilities for testing logging behavior."""

    @staticmethod
    def extract_log_messages(caplog, level: str = "INFO") -> list:
        """Extract log messages of specific level from caplog."""
        return [
            record.message for record in caplog.records
            if record.levelname == level
        ]

    @staticmethod
    def check_expected_logs(caplog, expected_patterns: list) -> bool:
        """Check if expected log patterns are present."""
        log_messages = [record.message for record in caplog.records]
        all_text = " ".join(log_messages)

        for pattern in expected_patterns:
            if pattern not in all_text:
                return False
        return True
