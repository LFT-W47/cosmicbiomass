"""
Property-based tests for cosmicbiomass package.

These tests use the hypothesis library to generate a wide range of test inputs
and verify that the code behaves correctly across many scenarios. This helps
catch edge cases that might not be covered by traditional example-based tests.
"""

import numpy as np
import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.extra.numpy import arrays

import cosmicbiomass
from unittest.mock import patch


class TestPropertyBasedValidation:
    """Property-based tests for input validation."""
    
    @given(
        lat=st.floats(min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False),
        lon=st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False),
        radius=st.floats(min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @pytest.mark.unit
    @settings(max_examples=50)
    def test_valid_coordinates_accepted(self, lat, lon, radius):
        """Test that all valid coordinate combinations are accepted."""
        # Mock the actual processing to test only validation
        with patch('cosmicbiomass._extract_biomass_cube'), \
             patch('cosmicbiomass._compute_footprint_weights'), \
             patch('cosmicbiomass._compute_weighted_stats', return_value=(100.0, 20.0)):
            
            # Should not raise any validation errors
            result = cosmicbiomass.get_average_biomass(lat, lon, radius)
            assert len(result) == 2
            assert all(isinstance(x, float) for x in result)
    
    @given(
        lat=st.one_of(
            st.floats(max_value=-90.1, allow_nan=False, allow_infinity=False),
            st.floats(min_value=90.1, allow_nan=False, allow_infinity=False),
            st.just(float('nan')),
            st.just(float('inf')),
            st.just(float('-inf'))
        )
    )
    @pytest.mark.unit
    @settings(max_examples=20)
    def test_invalid_latitude_rejected(self, lat):
        """Test that invalid latitudes are rejected."""
        with pytest.raises((ValueError, OverflowError)):
            cosmicbiomass.get_average_biomass(lat, 0.0, 100.0)
    
    @given(
        lon=st.one_of(
            st.floats(max_value=-180.1, allow_nan=False, allow_infinity=False),
            st.floats(min_value=180.1, allow_nan=False, allow_infinity=False),
            st.just(float('nan')),
            st.just(float('inf')),
            st.just(float('-inf'))
        )
    )
    @pytest.mark.unit
    @settings(max_examples=20)
    def test_invalid_longitude_rejected(self, lon):
        """Test that invalid longitudes are rejected."""
        with pytest.raises((ValueError, OverflowError)):
            cosmicbiomass.get_average_biomass(0.0, lon, 100.0)
    
    @given(
        radius=st.one_of(
            st.floats(max_value=0.0, allow_nan=False, allow_infinity=False),
            st.just(float('nan')),
            st.just(float('inf')),
            st.just(float('-inf'))
        )
    )
    @pytest.mark.unit
    @settings(max_examples=20)
    def test_invalid_radius_rejected(self, radius):
        """Test that invalid radii are rejected."""
        with pytest.raises((ValueError, OverflowError, RuntimeError)):
            cosmicbiomass.get_average_biomass(0.0, 0.0, radius)


class TestPropertyBasedConfiguration:
    """Property-based tests for configuration validation."""
    
    @given(
        resolution=st.integers(min_value=1, max_value=1000),
        upsample_factor=st.integers(min_value=1, max_value=50),
        edge_size_buffer=st.floats(min_value=1.0, max_value=10.0, allow_nan=False),
        n_jobs=st.integers(min_value=-1, max_value=16)
    )
    @pytest.mark.unit
    @settings(max_examples=30)
    def test_valid_config_parameters(self, resolution, upsample_factor, edge_size_buffer, n_jobs):
        """Test that valid configuration parameters are accepted."""
        config = cosmicbiomass.CosmicBiomassConfig(
            default_resolution=resolution,
            default_upsample_factor=upsample_factor,
            edge_size_buffer=edge_size_buffer,
            n_jobs=n_jobs
        )
        
        assert config.default_resolution == resolution
        assert config.default_upsample_factor == upsample_factor
        assert config.edge_size_buffer == edge_size_buffer
        assert config.n_jobs == n_jobs
    
    @given(
        resolution=st.integers(max_value=0)
    )
    @pytest.mark.unit
    @settings(max_examples=10)
    def test_invalid_resolution_rejected(self, resolution):
        """Test that invalid resolutions are rejected."""
        with pytest.raises(ValueError):
            cosmicbiomass.CosmicBiomassConfig(default_resolution=resolution)
    
    @given(
        upsample_factor=st.integers(max_value=0)
    )
    @pytest.mark.unit
    @settings(max_examples=10)
    def test_invalid_upsample_factor_rejected(self, upsample_factor):
        """Test that invalid upsample factors are rejected."""
        with pytest.raises(ValueError):
            cosmicbiomass.CosmicBiomassConfig(default_upsample_factor=upsample_factor)
    
    @given(
        edge_size_buffer=st.floats(max_value=0.99, allow_nan=False, allow_infinity=False)
    )
    @pytest.mark.unit
    @settings(max_examples=10)
    def test_invalid_edge_size_buffer_rejected(self, edge_size_buffer):
        """Test that invalid edge size buffers are rejected."""
        with pytest.raises(ValueError):
            cosmicbiomass.CosmicBiomassConfig(edge_size_buffer=edge_size_buffer)


class TestPropertyBasedFractionalCoverage:
    """Property-based tests for fractional coverage computation."""
    
    @given(
        grid_size=st.integers(min_value=5, max_value=50),
        upsample=st.integers(min_value=1, max_value=10),
        radius_fraction=st.floats(min_value=0.1, max_value=0.8, allow_nan=False)
    )
    @pytest.mark.unit
    @pytest.mark.mock
    @settings(max_examples=20)
    def test_fractional_coverage_properties(self, grid_size, upsample, radius_fraction):
        """Test properties of fractional coverage computation."""
        from shapely.geometry import Point
        
        # Create test grid
        extent = 100.0  # meters
        raster_x = np.linspace(-extent, extent, grid_size)
        raster_y = np.linspace(-extent, extent, grid_size)
        
        # Create circular geometry at center
        center_point = Point(0, 0)
        radius = extent * radius_fraction
        buffer_geom = center_point.buffer(radius)
        
        # Mock rasterio to create a reasonable circular mask
        def mock_rasterize(shapes, out_shape, transform, fill=0, **kwargs):
            height, width = out_shape
            center_y, center_x = height // 2, width // 2
            y, x = np.ogrid[:height, :width]
            
            # Simple circular mask based on distance
            mask_radius = min(height, width) * radius_fraction / 2
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            mask = (distance <= mask_radius).astype(np.float32)
            return mask
        
        with patch('cosmicbiomass.features.rasterize', side_effect=mock_rasterize):
            mask = cosmicbiomass._compute_fractional_coverage_mask(
                buffer_geom, raster_x, raster_y, upsample=upsample
            )
        
        # Verify basic properties
        assert mask.shape == (grid_size, grid_size)
        assert mask.dtype == np.float32
        assert 0 <= mask.min() <= mask.max() <= 1
        
        # Should have some coverage for reasonable radius
        if radius_fraction > 0.2:
            assert np.any(mask > 0), "Should have some coverage for reasonable radius"
        
        # Center pixels should have higher coverage than edge pixels
        center_idx = grid_size // 2
        center_coverage = mask[center_idx, center_idx]
        edge_coverage = mask[0, 0]
        
        if radius_fraction < 0.7:  # For smaller radii
            assert center_coverage >= edge_coverage


class TestPropertyBasedWeightedStats:
    """Property-based tests for weighted statistics computation."""
    
    @given(
        data_shape=st.tuples(
            st.integers(min_value=5, max_value=30),
            st.integers(min_value=5, max_value=30)
        ),
        biomass_range=st.tuples(
            st.floats(min_value=0, max_value=100, allow_nan=False),
            st.floats(min_value=100, max_value=500, allow_nan=False)
        )
    )
    @pytest.mark.unit
    @settings(max_examples=15)
    def test_weighted_stats_properties(self, data_shape, biomass_range):
        """Test properties of weighted statistics computation."""
        height, width = data_shape
        min_biomass, max_biomass = biomass_range
        assume(min_biomass < max_biomass)
        
        # Create synthetic biomass data
        np.random.seed(42)  # For reproducible tests
        biomass_data = np.random.uniform(min_biomass, max_biomass, (height, width))
        
        # Create mock dataset
        import xarray as xr
        x_coords = np.linspace(0, width-1, width)
        y_coords = np.linspace(0, height-1, height)
        
        mock_cube = xr.Dataset(
            {"agbd": (["y", "x"], biomass_data)},
            coords={"x": x_coords, "y": y_coords}
        )
        
        # Create random weights
        weights = np.random.uniform(0, 1, (height, width))
        
        mean, uncertainty = cosmicbiomass._compute_weighted_stats(mock_cube, weights)
        
        # Basic properties
        assert isinstance(mean, float)
        assert isinstance(uncertainty, float)
        assert not np.isnan(mean)
        assert not np.isnan(uncertainty)
        assert uncertainty >= 0
        
        # Mean should be within data range
        assert min_biomass <= mean <= max_biomass
    
    @given(
        constant_value=st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    @pytest.mark.unit
    @settings(max_examples=10)
    def test_constant_data_zero_uncertainty(self, constant_value):
        """Test that constant data results in zero uncertainty."""
        import xarray as xr
        
        # Create constant biomass data
        biomass_data = np.full((10, 10), constant_value)
        
        mock_cube = xr.Dataset(
            {"agbd": (["y", "x"], biomass_data)},
            coords={"x": np.arange(10), "y": np.arange(10)}
        )
        
        # Uniform weights
        weights = np.ones((10, 10))
        
        mean, uncertainty = cosmicbiomass._compute_weighted_stats(mock_cube, weights)
        
        # Mean should equal the constant value
        assert abs(mean - constant_value) < 1e-10
        # Uncertainty should be zero (or very close due to floating point)
        assert uncertainty < 1e-10


class TestPropertyBasedEdgeCases:
    """Property-based tests for edge cases and boundary conditions."""
    
    @given(
        footprint_radius=st.floats(min_value=1.0, max_value=50000.0, allow_nan=False)
    )
    @pytest.mark.unit
    @settings(max_examples=20)
    def test_edge_size_calculation_properties(self, footprint_radius):
        """Test properties of edge size calculation."""
        # Test the edge size calculation logic
        config = cosmicbiomass.CosmicBiomassConfig()
        expected_edge_size = int(footprint_radius * 2 * config.edge_size_buffer)
        
        # Mock the extraction to get the edge size
        with patch('cosmicbiomass.source_registry.get_source') as mock_get_source:
            from unittest.mock import Mock
            mock_source = Mock()
            mock_source.extract_cube.return_value = Mock()
            mock_get_source.return_value = mock_source
            
            with patch('cosmicbiomass._compute_footprint_weights'), \
                 patch('cosmicbiomass._compute_weighted_stats', return_value=(100.0, 20.0)):
                
                cosmicbiomass.get_average_biomass(0.0, 0.0, footprint_radius)
                
                # Verify edge size was calculated correctly
                call_args = mock_source.extract_cube.call_args
                actual_edge_size = call_args[0][2]  # Third positional argument
                
                assert actual_edge_size == expected_edge_size
    
    @given(
        lat=st.floats(min_value=-89.9, max_value=89.9, allow_nan=False),
        lon=st.floats(min_value=-179.9, max_value=179.9, allow_nan=False)
    )
    @pytest.mark.unit
    @settings(max_examples=20)
    def test_coordinate_edge_cases(self, lat, lon):
        """Test coordinate handling near valid boundaries."""
        # Test coordinates very close to valid boundaries
        with patch('cosmicbiomass._extract_biomass_cube'), \
             patch('cosmicbiomass._compute_footprint_weights'), \
             patch('cosmicbiomass._compute_weighted_stats', return_value=(100.0, 20.0)):
            
            # Should handle coordinates near boundaries without issues
            result = cosmicbiomass.get_average_biomass(lat, lon, 100.0)
            assert len(result) == 2
