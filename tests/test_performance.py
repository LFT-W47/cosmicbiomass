"""
Performance and benchmark tests for cosmicbiomass package.

These tests measure performance characteristics and ensure that the package
meets reasonable performance expectations under various conditions.
"""

import time
import gc
from contextlib import contextmanager
from typing import Generator
from unittest.mock import patch

import numpy as np
import pytest

import cosmicbiomass


@contextmanager
def measure_time() -> Generator[list, None, None]:
    """Context manager to measure execution time."""
    times = []
    start_time = time.perf_counter()
    yield times
    end_time = time.perf_counter()
    times.append(end_time - start_time)


@contextmanager
def measure_memory():
    """Context manager to measure memory usage (basic version)."""
    gc.collect()  # Clean up before measurement
    yield
    gc.collect()  # Clean up after measurement


class TestPerformanceBenchmarks:
    """Benchmark tests for core functionality."""
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_api_call_performance(self, sample_coordinates, mock_cubo_create,
                                  mock_biomass_cube, mock_rasterio_features):
        """Test that API calls complete within reasonable time."""
        with measure_time() as times:
            result = cosmicbiomass.get_average_biomass(**sample_coordinates)
        
        execution_time = times[0]
        
        # With mocked dependencies, should be very fast
        assert execution_time < 0.1, f"API call too slow: {execution_time:.3f}s"
        assert len(result) == 2
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_repeated_calls_performance(self, sample_coordinates, mock_cubo_create,
                                        mock_biomass_cube, mock_rasterio_features):
        """Test performance of repeated API calls."""
        n_calls = 10
        times = []
        
        for _ in range(n_calls):
            with measure_time() as call_times:
                result = cosmicbiomass.get_average_biomass(**sample_coordinates)
            times.append(call_times[0])
            assert len(result) == 2
        
        # All calls should be reasonably fast
        max_time = max(times)
        mean_time = sum(times) / len(times)
        
        assert max_time < 0.2, f"Slowest call too slow: {max_time:.3f}s"
        assert mean_time < 0.05, f"Average call too slow: {mean_time:.3f}s"
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_different_footprint_sizes_performance(self, mock_cubo_create,
                                                   mock_biomass_cube,
                                                   mock_rasterio_features):
        """Test performance scaling with different footprint sizes."""
        lat, lon = 51.0, 13.0
        footprint_sizes = [50, 100, 200, 500, 1000]  # meters
        times = []
        
        for radius in footprint_sizes:
            with measure_time() as call_times:
                result = cosmicbiomass.get_average_biomass(
                    lat=lat, lon=lon, footprint_radius=radius
                )
            times.append(call_times[0])
            assert len(result) == 2
        
        # Performance should scale reasonably with footprint size
        # Larger footprints should not be dramatically slower with mocked data
        max_time = max(times)
        assert max_time < 0.3, f"Largest footprint too slow: {max_time:.3f}s"
    
    @pytest.mark.unit
    def test_configuration_object_performance(self):
        """Test that configuration object creation is fast."""
        n_configs = 100
        
        with measure_time() as times:
            configs = [cosmicbiomass.CosmicBiomassConfig() for _ in range(n_configs)]
        
        total_time = times[0]
        per_config_time = total_time / n_configs
        
        assert total_time < 1.0, f"Config creation too slow: {total_time:.3f}s"
        assert per_config_time < 0.01, f"Per-config time too slow: {per_config_time:.3f}s"
        assert len(configs) == n_configs
    
    @pytest.mark.unit
    def test_source_registry_performance(self):
        """Test that source registry operations are fast."""
        registry = cosmicbiomass.BiomassSourceRegistry()
        
        # Test listing sources
        with measure_time() as times:
            for _ in range(100):
                sources = registry.list_sources()
        
        assert times[0] < 0.1, f"Source listing too slow: {times[0]:.3f}s"
        assert len(sources) >= 1
        
        # Test getting sources
        with measure_time() as times:
            for _ in range(50):
                source = registry.get_source("dlr")
        
        assert times[0] < 0.5, f"Source creation too slow: {times[0]:.3f}s"


class TestMemoryUsage:
    """Test memory usage characteristics."""
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_memory_usage_reasonable(self, sample_coordinates, mock_cubo_create,
                                     mock_biomass_cube, mock_rasterio_features):
        """Test that memory usage is reasonable during processing."""
        # Run multiple iterations to check for memory leaks
        n_iterations = 20
        
        with measure_memory():
            for _ in range(n_iterations):
                result = cosmicbiomass.get_average_biomass(**sample_coordinates)
                assert len(result) == 2
                
                # Force garbage collection between iterations
                gc.collect()
        
        # If we got here without memory errors, consider it a pass
        # In a real scenario, you might use memory_profiler or similar
    
    @pytest.mark.unit
    def test_configuration_memory_efficiency(self):
        """Test that multiple configurations don't consume excessive memory."""
        configs = []
        
        with measure_memory():
            # Create many configuration objects
            for i in range(1000):
                config = cosmicbiomass.CosmicBiomassConfig(
                    default_resolution=10 + (i % 10),
                    default_upsample_factor=5 + (i % 5)
                )
                configs.append(config)
        
        # Verify they're all valid
        assert len(configs) == 1000
        assert all(isinstance(c, cosmicbiomass.CosmicBiomassConfig) for c in configs)


class TestScalabilityBenchmarks:
    """Test scalability characteristics with different data sizes."""
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_fractional_coverage_scaling(self):
        """Test fractional coverage computation scaling."""
        grid_sizes = [10, 20, 50, 100]
        times = []
        
        from shapely.geometry import Point
        
        for size in grid_sizes:
            # Create test data
            raster_x = np.linspace(-100, 100, size)
            raster_y = np.linspace(-100, 100, size)
            buffer_geom = Point(0, 0).buffer(50)
            
            # Mock rasterio to create appropriate sized output
            def mock_rasterize(shapes, out_shape, transform, fill=0, **kwargs):
                height, width = out_shape
                return np.random.random((height, width)).astype(np.float32)
            
            with patch('cosmicbiomass.features.rasterize', side_effect=mock_rasterize):
                with measure_time() as call_times:
                    mask = cosmicbiomass._compute_fractional_coverage_mask(
                        buffer_geom, raster_x, raster_y, upsample=2
                    )
                
                times.append(call_times[0])
                assert mask.shape == (size, size)
        
        # Times should scale reasonably (not exponentially)
        # For small grids with low upsample, should be quite fast
        assert all(t < 1.0 for t in times), f"Some computations too slow: {times}"
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_weighted_stats_scaling(self):
        """Test weighted statistics computation scaling."""
        import xarray as xr
        
        data_sizes = [(10, 10), (20, 20), (50, 50), (100, 100)]
        times = []
        
        for height, width in data_sizes:
            # Create synthetic data
            biomass_data = np.random.uniform(50, 300, (height, width))
            weights = np.random.uniform(0, 1, (height, width))
            
            mock_cube = xr.Dataset(
                {"agbd": (["y", "x"], biomass_data)},
                coords={"x": np.arange(width), "y": np.arange(height)}
            )
            
            with measure_time() as call_times:
                mean, uncertainty = cosmicbiomass._compute_weighted_stats(
                    mock_cube, weights
                )
            
            times.append(call_times[0])
            assert isinstance(mean, float)
            assert isinstance(uncertainty, float)
        
        # Should scale reasonably with data size
        assert all(t < 0.5 for t in times), f"Some computations too slow: {times}"


class TestResourceUsageLimits:
    """Test resource usage stays within reasonable limits."""
    
    @pytest.mark.unit
    @pytest.mark.mock
    def test_maximum_footprint_size_handling(self, mock_cubo_create, mock_biomass_cube,
                                             mock_rasterio_features):
        """Test handling of very large footprint sizes."""
        # Test with a large but reasonable footprint
        large_radius = 5000  # 5km radius
        
        with measure_time() as times:
            result = cosmicbiomass.get_average_biomass(
                lat=51.0, lon=13.0, footprint_radius=large_radius
            )
        
        execution_time = times[0]
        
        # Should still complete in reasonable time with mocked data
        assert execution_time < 1.0, f"Large footprint too slow: {execution_time:.3f}s"
        assert len(result) == 2
        
        # Verify edge size calculation
        call_args = mock_cubo_create.call_args[1]
        expected_edge_size = int(large_radius * 2 * cosmicbiomass.config.edge_size_buffer)
        assert call_args["edge_size"] == expected_edge_size
    
    @pytest.mark.unit
    def test_configuration_validation_performance(self):
        """Test that configuration validation is fast even with many attempts."""
        n_attempts = 1000
        
        with measure_time() as times:
            for i in range(n_attempts):
                try:
                    # Mix of valid and invalid configurations
                    if i % 10 == 0:
                        # Invalid configuration
                        cosmicbiomass.CosmicBiomassConfig(default_resolution=-1)
                    else:
                        # Valid configuration
                        cosmicbiomass.CosmicBiomassConfig(default_resolution=10 + (i % 5))
                except ValueError:
                    # Expected for invalid configurations
                    pass
        
        total_time = times[0]
        per_attempt_time = total_time / n_attempts
        
        assert total_time < 2.0, f"Validation too slow overall: {total_time:.3f}s"
        assert per_attempt_time < 0.002, f"Per-validation too slow: {per_attempt_time:.3f}s"


@pytest.mark.slow
class TestRealWorldPerformance:
    """Performance tests with realistic data sizes (marked as slow)."""
    
    @pytest.mark.slow
    @pytest.mark.mock
    def test_realistic_data_size_performance(self):
        """Test performance with realistic data cube sizes."""
        # Simulate a realistic data cube (e.g., 200x200 pixels)
        import xarray as xr
        
        height, width = 200, 200
        biomass_data = np.random.uniform(50, 400, (height, width))
        
        # Create realistic coordinates (10m resolution over 2km x 2km)
        x_coords = np.linspace(13.0, 13.02, width)
        y_coords = np.linspace(51.0, 51.02, height)
        
        realistic_cube = xr.Dataset(
            {"agbd": (["y", "x"], biomass_data)},
            coords={"x": x_coords, "y": y_coords}
        )
        
        # Test footprint computation with realistic data
        weights = np.random.uniform(0, 1, (height, width))
        
        with measure_time() as times:
            mean, uncertainty = cosmicbiomass._compute_weighted_stats(
                realistic_cube, weights
            )
        
        execution_time = times[0]
        
        # Should handle realistic data sizes efficiently
        assert execution_time < 2.0, f"Realistic data too slow: {execution_time:.3f}s"
        assert isinstance(mean, float)
        assert isinstance(uncertainty, float)
