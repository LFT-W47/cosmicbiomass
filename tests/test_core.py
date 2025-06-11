"""
Unit tests for cosmicbiomass package core functionality.

These tests focus on individual functions and classes in isolation,
using mocks to avoid external dependencies and ensure fast execution.
"""

import logging
from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pytest
import xarray as xr
from shapely.geometry import Point

import cosmicbiomass


class TestCosmicBiomassConfig:
    """Test the Pydantic configuration model."""
    
    @pytest.mark.unit
    def test_default_config_creation(self):
        """Test that default configuration is created correctly."""
        config = cosmicbiomass.CosmicBiomassConfig()
        
        assert config.default_stac_url == "https://geoservice.dlr.de/eoc/ogc/stac/v1"
        assert config.default_collection == "FOREST_STRUCTURE_DE_AGBD_P1Y"
        assert config.default_resolution == 10
        assert config.default_upsample_factor == 10
        assert config.edge_size_buffer == 1.5
        assert config.n_jobs == -1
    
    @pytest.mark.unit
    def test_config_validation(self):
        """Test configuration validation with invalid values."""
        # Test negative resolution
        with pytest.raises(ValueError):
            cosmicbiomass.CosmicBiomassConfig(default_resolution=-1)
        
        # Test zero upsample factor
        with pytest.raises(ValueError):
            cosmicbiomass.CosmicBiomassConfig(default_upsample_factor=0)
        
        # Test edge size buffer less than 1
        with pytest.raises(ValueError):
            cosmicbiomass.CosmicBiomassConfig(edge_size_buffer=0.5)
    
    @pytest.mark.unit
    def test_config_modification(self):
        """Test that configuration can be modified."""
        config = cosmicbiomass.CosmicBiomassConfig()
        config.default_resolution = 20
        config.n_jobs = 4
        
        assert config.default_resolution == 20
        assert config.n_jobs == 4


class TestDLRBiomassSource:
    """Test the DLR biomass data source implementation."""
    
    @pytest.mark.unit
    def test_initialization_with_defaults(self):
        """Test DLR source initialization with default values."""
        source = cosmicbiomass.DLRBiomassSource()
        
        assert source.stac_url == cosmicbiomass.config.default_stac_url
        assert source.collection == cosmicbiomass.config.default_collection
        assert source.resolution == cosmicbiomass.config.default_resolution
    
    @pytest.mark.unit
    def test_initialization_with_custom_values(self):
        """Test DLR source initialization with custom values."""
        custom_params = {
            "stac_url": "https://custom.stac.url",
            "collection": "CUSTOM_COLLECTION",
            "start_date": "2020-01-01",
            "end_date": "2022-12-31",
            "resolution": 20,
        }
        
        source = cosmicbiomass.DLRBiomassSource(**custom_params)
        
        assert source.stac_url == custom_params["stac_url"]
        assert source.collection == custom_params["collection"]
        assert source.start_date == custom_params["start_date"]
        assert source.end_date == custom_params["end_date"]
        assert source.resolution == custom_params["resolution"]
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_extract_cube_success(self, mock_cubo_create, mock_biomass_cube):
        """Test successful cube extraction."""
        source = cosmicbiomass.DLRBiomassSource()
        
        result = source.extract_cube(lat=51.0, lon=13.0, edge_size=1000)
        
        assert result is mock_biomass_cube
        mock_cubo_create.assert_called_once()
        
        # Verify cubo.create was called with correct parameters
        call_args = mock_cubo_create.call_args[1]
        assert call_args["lat"] == 51.0
        assert call_args["lon"] == 13.0
        assert call_args["edge_size"] == 1000
        assert call_args["gee"] is False
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_extract_cube_failure(self):
        """Test cube extraction failure handling."""
        source = cosmicbiomass.DLRBiomassSource()
        
        with patch('cosmicbiomass.cubo.create') as mock_create:
            mock_create.side_effect = Exception("STAC connection failed")
            
            with pytest.raises(RuntimeError, match="DLR cube extraction failed"):
                source.extract_cube(lat=51.0, lon=13.0, edge_size=1000)
    
    @pytest.mark.unit
    def test_get_source_info(self):
        """Test source information retrieval."""
        source = cosmicbiomass.DLRBiomassSource()
        info = source.get_source_info()
        
        assert isinstance(info, dict)
        assert "name" in info
        assert "provider" in info
        assert "units" in info
        assert "description" in info
        assert info["units"] == "Mg/ha"


class TestBiomassSourceRegistry:
    """Test the biomass source registry."""
    
    @pytest.mark.unit
    def test_registry_initialization(self):
        """Test registry initialization with built-in sources."""
        registry = cosmicbiomass.BiomassSourceRegistry()
        
        assert "dlr" in registry.list_sources()
        assert len(registry.list_sources()) == 1
    
    @pytest.mark.unit
    def test_register_new_source(self):
        """Test registering a new source."""
        registry = cosmicbiomass.BiomassSourceRegistry()
        
        # Create mock source class
        class MockSource:
            def extract_cube(self, lat, lon, edge_size, **kwargs):
                pass
            
            def get_source_info(self):
                return {"name": "Mock Source"}
        
        registry.register_source("mock", MockSource)
        
        assert "mock" in registry.list_sources()
        assert len(registry.list_sources()) == 2
    
    @pytest.mark.unit
    def test_register_duplicate_source(self):
        """Test registering a source with existing name."""
        registry = cosmicbiomass.BiomassSourceRegistry()
        
        class MockSource:
            def extract_cube(self, lat, lon, edge_size, **kwargs):
                pass
            
            def get_source_info(self):
                return {}
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register_source("dlr", MockSource)
    
    @pytest.mark.unit
    def test_register_invalid_source(self):
        """Test registering source without required methods."""
        registry = cosmicbiomass.BiomassSourceRegistry()
        
        class InvalidSource:
            pass  # Missing required methods
        
        with pytest.raises(ValueError, match="implement BiomassDataSource protocol"):
            registry.register_source("invalid", InvalidSource)
    
    @pytest.mark.unit
    def test_get_source(self):
        """Test getting source instance."""
        registry = cosmicbiomass.BiomassSourceRegistry()
        source = registry.get_source("dlr")
        
        assert isinstance(source, cosmicbiomass.DLRBiomassSource)
    
    @pytest.mark.unit
    def test_get_unknown_source(self):
        """Test getting unknown source."""
        registry = cosmicbiomass.BiomassSourceRegistry()
        
        with pytest.raises(ValueError, match="Unknown source"):
            registry.get_source("unknown")


class TestMainAPI:
    """Test the main get_average_biomass API function."""
    
    @pytest.mark.unit
    def test_input_validation_success(self, sample_coordinates):
        """Test that valid inputs pass validation."""
        # This should not raise any exceptions during validation
        lat = sample_coordinates["lat"]
        lon = sample_coordinates["lon"]
        radius = sample_coordinates["footprint_radius"]
        
        # We'll mock the actual processing to test only validation
        with patch('cosmicbiomass._extract_biomass_cube'), \
             patch('cosmicbiomass._compute_footprint_weights'), \
             patch('cosmicbiomass._compute_weighted_stats', return_value=(150.0, 25.0)):
            
            result = cosmicbiomass.get_average_biomass(lat, lon, radius)
            assert len(result) == 2
            assert all(isinstance(x, float) for x in result)
    
    @pytest.mark.unit
    @pytest.mark.parametrize("invalid_coords", [
        {"lat": 91.0, "lon": 0.0, "footprint_radius": 100.0},   # Invalid lat
        {"lat": -91.0, "lon": 0.0, "footprint_radius": 100.0},  # Invalid lat
        {"lat": 0.0, "lon": 181.0, "footprint_radius": 100.0},  # Invalid lon
        {"lat": 0.0, "lon": -181.0, "footprint_radius": 100.0}, # Invalid lon
        {"lat": 50.0, "lon": 10.0, "footprint_radius": -100.0}, # Negative radius
        {"lat": 50.0, "lon": 10.0, "footprint_radius": 0.0},    # Zero radius
    ])
    def test_input_validation_failures(self, invalid_coords):
        """Test that invalid inputs raise appropriate errors."""
        with pytest.raises(ValueError):
            cosmicbiomass.get_average_biomass(**invalid_coords)
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_successful_execution(self, sample_coordinates, mock_cubo_create, 
                                  mock_biomass_cube, mock_rasterio_features):
        """Test successful execution of the complete workflow."""
        result = cosmicbiomass.get_average_biomass(**sample_coordinates)
        
        assert len(result) == 2
        mean_biomass, uncertainty = result
        
        assert isinstance(mean_biomass, float)
        assert isinstance(uncertainty, float)
        assert mean_biomass >= 0  # Biomass should be non-negative
        assert uncertainty >= 0   # Uncertainty should be non-negative
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_error_propagation(self, sample_coordinates):
        """Test that errors in processing are properly propagated."""
        with patch('cosmicbiomass._extract_biomass_cube') as mock_extract:
            mock_extract.side_effect = Exception("Data extraction failed")
            
            with pytest.raises(RuntimeError, match="Biomass extraction failed"):
                cosmicbiomass.get_average_biomass(**sample_coordinates)


class TestUtilityFunctions:
    """Test utility functions for biomass processing."""
    
    @pytest.mark.unit
    def test_compute_fractional_coverage_mask(self, mock_rasterio_features):
        """Test fractional coverage mask computation."""
        # Create test geometry and coordinates
        point = Point(0, 0)
        buffer_geom = point.buffer(100)  # 100 meter radius
        
        raster_x = np.linspace(-200, 200, 20)
        raster_y = np.linspace(-200, 200, 20)
        
        mask = cosmicbiomass._compute_fractional_coverage_mask(
            buffer_geom, raster_x, raster_y, upsample=2
        )
        
        assert mask.shape == (20, 20)
        assert mask.dtype == np.float32
        assert 0 <= mask.min() <= mask.max() <= 1
        assert np.any(mask > 0)  # Should have some coverage
    
    @pytest.mark.unit
    def test_compute_weighted_stats(self, mock_biomass_cube, mock_fractional_weights):
        """Test weighted statistics computation."""
        mean, uncertainty = cosmicbiomass._compute_weighted_stats(
            mock_biomass_cube, mock_fractional_weights
        )
        
        assert isinstance(mean, float)
        assert isinstance(uncertainty, float)
        assert mean >= 0
        assert uncertainty >= 0
    
    @pytest.mark.unit
    def test_compute_weighted_stats_no_valid_data(self, mock_biomass_cube):
        """Test weighted statistics with no valid data."""
        # Create weights with all zeros
        zero_weights = np.zeros((20, 20))
        
        mean, uncertainty = cosmicbiomass._compute_weighted_stats(
            mock_biomass_cube, zero_weights
        )
        
        assert np.isnan(mean)
        assert np.isnan(uncertainty)


class TestLogging:
    """Test logging configuration and behavior."""
    
    @pytest.mark.unit
    def test_logger_exists(self):
        """Test that package logger is properly configured."""
        assert cosmicbiomass.logger.name == "cosmicbiomass"
        assert cosmicbiomass.logger.level == logging.INFO
    
    @pytest.mark.unit
    def test_logging_during_operation(self, caplog_debug, sample_coordinates,
                                      mock_cubo_create, mock_biomass_cube,
                                      mock_rasterio_features):
        """Test that appropriate log messages are generated."""
        cosmicbiomass.get_average_biomass(**sample_coordinates)
        
        # Check that key log messages were generated
        log_messages = [record.message for record in caplog_debug.records]
        
        # Should log the start of extraction
        assert any("Starting biomass extraction" in msg for msg in log_messages)
        # Should log completion
        assert any("Biomass extraction completed" in msg for msg in log_messages)


class TestGlobalConfig:
    """Test global configuration management."""
    
    @pytest.mark.unit
    def test_global_config_exists(self):
        """Test that global config instance exists and is accessible."""
        assert cosmicbiomass.config is not None
        assert isinstance(cosmicbiomass.config, cosmicbiomass.CosmicBiomassConfig)
    
    @pytest.mark.unit
    def test_global_registry_exists(self):
        """Test that global source registry exists and is initialized."""
        assert cosmicbiomass.source_registry is not None
        assert isinstance(cosmicbiomass.source_registry, cosmicbiomass.BiomassSourceRegistry)
        assert len(cosmicbiomass.source_registry.list_sources()) >= 1
