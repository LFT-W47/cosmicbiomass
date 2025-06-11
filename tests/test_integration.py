"""
Integration tests for cosmicbiomass package.

These tests verify that different components work together correctly,
including end-to-end workflows and interactions with external services.
Some tests are marked as 'slow' as they may require network access.
"""

import numpy as np
import pytest
import xarray as xr
from unittest.mock import patch

import cosmicbiomass


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_complete_workflow_mocked(self, sample_coordinates, mock_cubo_create,
                                      mock_biomass_cube, mock_rasterio_features,
                                      caplog_debug):
        """Test complete workflow with mocked external dependencies."""
        lat = sample_coordinates["lat"]
        lon = sample_coordinates["lon"]
        radius = sample_coordinates["footprint_radius"]
        
        # Execute the complete workflow
        mean_biomass, uncertainty = cosmicbiomass.get_average_biomass(
            lat=lat, lon=lon, footprint_radius=radius
        )
        
        # Verify results are reasonable
        assert isinstance(mean_biomass, float)
        assert isinstance(uncertainty, float)
        assert 0 <= mean_biomass <= 1000  # Reasonable biomass range
        assert 0 <= uncertainty <= 500    # Reasonable uncertainty range
        
        # Verify logging captured the workflow steps
        log_messages = [record.message for record in caplog_debug.records]
        workflow_steps = [
            "Starting biomass extraction",
            "Extracting data cube",
            "Computing footprint weights",
            "Computing weighted biomass statistics", 
            "Biomass extraction completed"
        ]
        
        for step in workflow_steps:
            assert any(step in msg for msg in log_messages), f"Missing log: {step}"
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_workflow_with_custom_source_params(self, sample_coordinates,
                                                 mock_cubo_create, mock_biomass_cube,
                                                 mock_rasterio_features):
        """Test workflow with custom data source parameters.""" 
        custom_params = {
            "collection": "CUSTOM_COLLECTION",
            "resolution": 20,
            "start_date": "2020-01-01",
        }
        
        result = cosmicbiomass.get_average_biomass(
            **sample_coordinates, **custom_params
        )
        
        assert len(result) == 2
        
        # Verify cubo was called with custom parameters
        call_kwargs = mock_cubo_create.call_args[1]
        assert call_kwargs["collection"] == "CUSTOM_COLLECTION"
        assert call_kwargs["resolution"] == 20
        assert call_kwargs["start_date"] == "2020-01-01"
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_workflow_different_footprint_sizes(self, mock_cubo_create,
                                                 mock_biomass_cube, 
                                                 mock_rasterio_features):
        """Test workflow with different footprint sizes."""
        lat, lon = 51.0, 13.0
        footprint_sizes = [50, 100, 200, 500]  # meters
        
        results = []
        for radius in footprint_sizes:
            mean_biomass, uncertainty = cosmicbiomass.get_average_biomass(
                lat=lat, lon=lon, footprint_radius=radius
            )
            results.append((mean_biomass, uncertainty))
        
        # All results should be valid
        for mean, unc in results:
            assert isinstance(mean, float)
            assert isinstance(unc, float)
            assert not np.isnan(mean)
            assert not np.isnan(unc)
        
        # Verify that edge_size changes with footprint radius
        edge_sizes = [call[1]["edge_size"] for call in mock_cubo_create.call_args_list]
        assert len(set(edge_sizes)) > 1, "Edge sizes should vary with footprint radius"


class TestDataSourceIntegration:
    """Test integration between different data sources and the main API."""
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_dlr_source_integration(self, sample_coordinates, mock_cubo_create,
                                    mock_biomass_cube, mock_rasterio_features):
        """Test integration with DLR data source."""
        result = cosmicbiomass.get_average_biomass(
            **sample_coordinates, data_source="dlr"
        )
        
        assert len(result) == 2
        mock_cubo_create.assert_called_once()
    
    @pytest.mark.integration
    def test_custom_source_registration_and_usage(self, sample_coordinates):
        """Test registering and using a custom data source."""
        
        class MockCustomSource:
            """Mock custom biomass source for testing."""
            
            def __init__(self, **kwargs):
                self.params = kwargs
            
            def extract_cube(self, lat, lon, edge_size, **kwargs):
                """Return a simple mock cube."""
                x_coords = np.linspace(lon - 0.01, lon + 0.01, 10)
                y_coords = np.linspace(lat - 0.01, lat + 0.01, 10)
                
                biomass_data = np.full((10, 10), 100.0)  # Constant biomass
                
                return xr.Dataset(
                    {"biomass": (["y", "x"], biomass_data)},
                    coords={"x": x_coords, "y": y_coords}
                )
            
            def get_source_info(self):
                return {
                    "name": "Mock Custom Source",
                    "provider": "Test Provider",
                    "units": "Mg/ha",
                    "description": "Custom source for testing"
                }
        
        # Register the custom source
        cosmicbiomass.source_registry.register_source("custom", MockCustomSource)
        
        try:
            # Use the custom source
            with patch('cosmicbiomass._compute_fractional_coverage_mask') as mock_mask:
                mock_mask.return_value = np.ones((10, 10)) * 0.5  # Uniform weights
                
                result = cosmicbiomass.get_average_biomass(
                    **sample_coordinates, data_source="custom"
                )
                
                assert len(result) == 2
                mean_biomass, uncertainty = result
                
                # With constant biomass and uniform weights, mean should be 100
                assert abs(mean_biomass - 100.0) < 1e-6
                # With constant values, uncertainty should be 0
                assert abs(uncertainty) < 1e-6
        
        finally:
            # Clean up: remove the custom source (would need to add this method)
            # For now, we'll leave it as the registry persists across tests
            pass


class TestErrorHandlingIntegration:
    """Test error handling across integrated components."""
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_data_extraction_failure_propagation(self, sample_coordinates):
        """Test that data extraction failures are properly handled."""
        with patch('cosmicbiomass.cubo.create') as mock_create:
            mock_create.side_effect = ConnectionError("Network unavailable")
            
            with pytest.raises(RuntimeError, match="Biomass extraction failed"):
                cosmicbiomass.get_average_biomass(**sample_coordinates)
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_footprint_computation_failure_propagation(self, sample_coordinates,
                                                       mock_cubo_create, 
                                                       mock_biomass_cube):
        """Test that footprint computation failures are properly handled."""
        with patch('cosmicbiomass._compute_fractional_coverage_mask') as mock_mask:
            mock_mask.side_effect = ValueError("Invalid geometry")
            
            with pytest.raises(RuntimeError, match="Biomass extraction failed"):
                cosmicbiomass.get_average_biomass(**sample_coordinates)
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_statistics_computation_failure_propagation(self, sample_coordinates,
                                                        mock_cubo_create,
                                                        mock_biomass_cube,
                                                        mock_rasterio_features):
        """Test that statistics computation failures are properly handled."""
        with patch('cosmicbiomass._compute_weighted_stats') as mock_stats:
            mock_stats.side_effect = ValueError("Invalid weights")
            
            with pytest.raises(RuntimeError, match="Biomass extraction failed"):
                cosmicbiomass.get_average_biomass(**sample_coordinates)


class TestConfigurationIntegration:
    """Test how configuration affects integrated workflows."""
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_edge_size_buffer_effect(self, sample_coordinates, mock_cubo_create,
                                     mock_biomass_cube, mock_rasterio_features,
                                     temp_config):
        """Test that edge_size_buffer configuration affects cube size."""
        # Test with different buffer values
        buffer_values = [1.2, 1.5, 2.0]
        edge_sizes = []
        
        for buffer in buffer_values:
            temp_config.edge_size_buffer = buffer
            
            cosmicbiomass.get_average_biomass(**sample_coordinates)
            
            # Get the edge_size used in the last call
            edge_size = mock_cubo_create.call_args[1]["edge_size"]
            edge_sizes.append(edge_size)
        
        # Edge sizes should increase with buffer values
        assert edge_sizes[0] < edge_sizes[1] < edge_sizes[2]
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_upsample_factor_effect(self, sample_coordinates, mock_cubo_create,
                                    mock_biomass_cube, temp_config):
        """Test that upsample_factor affects fractional coverage computation."""
        upsample_values = [2, 5, 10]
        
        with patch('cosmicbiomass._compute_fractional_coverage_mask') as mock_mask:
            mock_mask.return_value = np.ones((20, 20)) * 0.5
            
            for upsample in upsample_values:
                temp_config.default_upsample_factor = upsample
                
                cosmicbiomass.get_average_biomass(**sample_coordinates)
                
                # Verify upsample parameter was passed correctly
                call_kwargs = mock_mask.call_args[1]
                assert call_kwargs["upsample"] == upsample


@pytest.mark.slow
class TestNetworkIntegration:
    """
    Tests that require network access to external services.
    
    These tests are marked as 'slow' and can be skipped in fast test runs.
    They test actual integration with STAC catalogs and data services.
    """
    
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires network access and real STAC catalog")
    def test_real_dlr_stac_connection(self):
        """Test actual connection to DLR STAC catalog."""
        # This test would check if the DLR STAC catalog is accessible
        # and returns valid metadata. Skip by default to avoid network deps.
        
        source = cosmicbiomass.DLRBiomassSource()
        
        # Test just the connection and metadata, not full data download
        try:
            # This would require a method to test catalog connectivity
            # source.test_connection()  # Hypothetical method
            pass
        except Exception as e:
            pytest.skip(f"STAC catalog not accessible: {e}")
    
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires network access and may download large data")
    def test_real_data_extraction_small_area(self):
        """Test actual data extraction for a very small area."""
        # This test would extract real data for a tiny area to verify
        # the complete workflow with actual external services.
        
        # Use a very small footprint to minimize data download
        result = cosmicbiomass.get_average_biomass(
            lat=51.1657,   # Dresden, Germany
            lon=13.7882,
            footprint_radius=50  # Very small 50m radius
        )
        
        assert len(result) == 2
        mean_biomass, uncertainty = result
        
        # Verify results are in reasonable ranges for forest areas
        assert 0 <= mean_biomass <= 500  # Reasonable for temperate forest
        assert 0 <= uncertainty <= 200   # Reasonable uncertainty


class TestPerformanceIntegration:
    """Test performance characteristics of integrated workflows."""
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_workflow_timing(self, sample_coordinates, mock_cubo_create,
                            mock_biomass_cube, mock_rasterio_features):
        """Test that workflow completes in reasonable time."""
        import time
        
        start_time = time.time()
        result = cosmicbiomass.get_average_biomass(**sample_coordinates)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # With mocked dependencies, should complete very quickly
        assert execution_time < 1.0, f"Workflow too slow: {execution_time:.2f}s"
        assert len(result) == 2
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_memory_usage_reasonable(self, sample_coordinates, mock_cubo_create,
                                     mock_biomass_cube, mock_rasterio_features):
        """Test that memory usage stays reasonable during processing."""
        # This is a basic check - for more detailed memory profiling,
        # you would use tools like memory_profiler
        
        import gc
        
        # Force garbage collection before test
        gc.collect()
        
        # Run the workflow multiple times
        for _ in range(5):
            result = cosmicbiomass.get_average_biomass(**sample_coordinates)
            assert len(result) == 2
        
        # Force garbage collection after test
        gc.collect()
        
        # If we got here without memory errors, consider it a pass
        # In practice, you might want to monitor actual memory usage
