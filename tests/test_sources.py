"""
Unit tests for the sources module.

Tests the data source base classes and DLR implementation.
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest
import xarray as xr

from cosmicbiomass.config import BiomassConfig
from cosmicbiomass.sources.base import DatasetInfo
from cosmicbiomass.sources.dlr import DLRBiomassSource


class TestDatasetInfo:
    """Test the DatasetInfo model."""

    def test_dataset_info_creation(self):
        """Test creating a DatasetInfo instance."""
        info = DatasetInfo(
            id="test_id",
            name="Test Dataset",
            description="A test dataset",
            spatial_resolution=100.0,
            temporal_coverage="2021",
            units="Mg/ha"
        )

        assert info.id == "test_id"
        assert info.name == "Test Dataset"
        assert info.spatial_resolution == 100.0
        assert info.units == "Mg/ha"
        assert info.uncertainty_available is False  # Default
        assert info.crs == "EPSG:4326"  # Default

    def test_dataset_info_with_uncertainty(self):
        """Test DatasetInfo with uncertainty available."""
        info = DatasetInfo(
            id="test_id",
            name="Test Dataset",
            description="A test dataset",
            spatial_resolution=100.0,
            temporal_coverage="2021",
            units="Mg/ha",
            uncertainty_available=True,
            crs="EPSG:32632"
        )

        assert info.uncertainty_available is True
        assert info.crs == "EPSG:32632"


class TestDLRBiomassSource:
    """Comprehensive tests for the DLR biomass data source."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = BiomassConfig(data_dir="test_data", n_jobs=1)
        self.source = DLRBiomassSource(self.config)

    def test_initialization_with_stac_client(self):
        """Test initialization with STAC client."""
        source = DLRBiomassSource(self.config)

        assert source.config == self.config
        assert source.stac_url == "https://geoservice.dlr.de/eoc/ogc/stac/v1"
        assert source.collection == "FOREST_STRUCTURE_DE_AGBD_P1Y"
        assert source.resolution == 10
        assert source.source_name == "DLR"

    def test_get_available_datasets(self):
        """Test getting available datasets from DLR."""
        source = DLRBiomassSource(self.config)
        datasets = source.get_available_datasets()

        # Should have the three hardcoded datasets
        assert "agbd_2017" in datasets
        assert "agbd_2020" in datasets
        assert "agbd_2021" in datasets

        # Check dataset info structure
        dataset_info = datasets["agbd_2021"]
        assert dataset_info.name == "AGBD 2021"
        assert dataset_info.spatial_resolution == 10.0
        assert dataset_info.units == "Mg/ha"
        assert dataset_info.uncertainty_available is True
        assert dataset_info.crs == "EPSG:32632"

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_load_data_success(self, mock_cubo_create):
        """Test successful data loading from STAC."""
        # Mock xarray dataset
        mock_data = xr.Dataset({
            'agbd': xr.DataArray(
                np.random.rand(100, 100),
                dims=['y', 'x'],
                coords={
                    'x': np.linspace(10.0, 12.0, 100),
                    'y': np.linspace(51.0, 53.0, 100)
                }
            )
        })
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        result = source.load_data("agbd_2021", bbox=(10.0, 51.0, 12.0, 53.0))

        assert isinstance(result, xr.Dataset)
        mock_cubo_create.assert_called_once()

        # Check that cubo was called with correct parameters
        call_kwargs = mock_cubo_create.call_args[1]
        assert call_kwargs['collection'] == "FOREST_STRUCTURE_DE_AGBD_P1Y"
        assert call_kwargs['start_date'] == "2021-01-01"
        assert call_kwargs['end_date'] == "2021-12-31"

    def test_load_data_invalid_dataset(self):
        """Test handling of invalid dataset names."""
        source = DLRBiomassSource(self.config)

        with pytest.raises(ValueError, match="Dataset invalid_dataset not available"):
            source.load_data("invalid_dataset", bbox=(10.0, 51.0, 12.0, 53.0))

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_load_data_cubo_error(self, mock_cubo_create):
        """Test handling of cubo errors."""
        mock_cubo_create.side_effect = Exception("STAC service unavailable")

        source = DLRBiomassSource(self.config)

        with pytest.raises(Exception, match="STAC service unavailable"):
            source.load_data("agbd_2021", bbox=(10.0, 51.0, 12.0, 53.0))

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_load_data_no_bbox(self, mock_cubo_create):
        """Test loading data without bbox (using defaults)."""
        mock_data = xr.Dataset({
            'agbd': xr.DataArray(
                np.random.rand(200, 200),
                dims=['y', 'x']
            )
        })
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        result = source.load_data("agbd_2020")  # No bbox

        assert isinstance(result, xr.Dataset)

        # Check default values were used
        call_kwargs = mock_cubo_create.call_args[1]
        assert call_kwargs['lat'] == 52.09  # Default Hohes Holz
        assert call_kwargs['lon'] == 11.226
        assert call_kwargs['edge_size'] == 2000  # Default 2km

    @patch('pyproj.Transformer')
    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_bbox_transformation(self, mock_cubo_create, mock_transformer_class):
        """Test bbox transformation to edge_size calculation."""
        # Mock transformer
        mock_transformer = Mock()
        mock_transformer.transform.side_effect = [
            (1000000, 6000000),  # x1, y1 in meters
            (1010000, 6010000)   # x2, y2 in meters
        ]
        mock_transformer_class.from_crs.return_value = mock_transformer

        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(100, 100), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        source.load_data("agbd_2021", bbox=(10.0, 51.0, 12.0, 53.0))

        # Check transformer was used correctly
        mock_transformer_class.from_crs.assert_called_once_with("EPSG:4326", "EPSG:3857", always_xy=True)

        # Check bbox corners were transformed
        assert mock_transformer.transform.call_count == 2
        mock_transformer.transform.assert_any_call(10.0, 51.0)  # Min corner
        mock_transformer.transform.assert_any_call(12.0, 53.0)  # Max corner

        # Check edge_size calculation (max of width/height difference)
        call_kwargs = mock_cubo_create.call_args[1]
        expected_edge_size = max(abs(1010000 - 1000000), abs(6010000 - 6000000))
        assert call_kwargs['edge_size'] == expected_edge_size

    def test_get_metadata_success(self):
        """Test successful metadata retrieval."""
        source = DLRBiomassSource(self.config)
        metadata = source.get_metadata("agbd_2021")

        assert metadata["source"] == "DLR"
        assert metadata["dataset_info"]["name"] == "AGBD 2021"
        assert metadata["dataset_info"]["spatial_resolution"] == 10.0
        assert metadata["dataset_info"]["units"] == "Mg/ha"
        assert metadata["data_format"] == "GeoTIFF COG"
        assert metadata["coordinate_system"] == "EPSG:32632"

    def test_get_metadata_invalid_dataset(self):
        """Test handling when dataset is not found."""
        source = DLRBiomassSource(self.config)

        with pytest.raises(ValueError, match="Dataset nonexistent not available"):
            source.get_metadata("nonexistent")

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_dataset_attributes(self, mock_cubo_create):
        """Test that dataset attributes are properly set."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        result = source.load_data("agbd_2017")

        # Check attributes were added
        assert result.attrs['source'] == 'DLR'
        assert result.attrs['dataset_id'] == 'agbd_2017'
        assert result.attrs['units'] == 'Mg/ha'
        assert result.attrs['spatial_resolution'] == 10.0

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_different_years(self, mock_cubo_create):
        """Test loading different years calls cubo with correct dates."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)

        # Test 2017 dataset
        source.load_data("agbd_2017")
        call_kwargs_2017 = mock_cubo_create.call_args[1]
        assert call_kwargs_2017['start_date'] == "2017-01-01"
        assert call_kwargs_2017['end_date'] == "2017-12-31"

        # Test 2020 dataset
        source.load_data("agbd_2020")
        call_kwargs_2020 = mock_cubo_create.call_args[1]
        assert call_kwargs_2020['start_date'] == "2020-01-01"
        assert call_kwargs_2020['end_date'] == "2020-12-31"

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_cubo_parameters(self, mock_cubo_create):
        """Test that all cubo parameters are set correctly."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        source.load_data("agbd_2021", bbox=(11.0, 52.0, 11.5, 52.5))

        call_kwargs = mock_cubo_create.call_args[1]

        # Check all required parameters
        assert 'lat' in call_kwargs
        assert 'lon' in call_kwargs
        assert call_kwargs['stac'] == "https://geoservice.dlr.de/eoc/ogc/stac/v1"
        assert call_kwargs['collection'] == "FOREST_STRUCTURE_DE_AGBD_P1Y"
        assert call_kwargs['gee'] is False
        assert call_kwargs['units'] == "m"
        assert call_kwargs['resolution'] == 10

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_edge_case_small_bbox(self, mock_cubo_create):
        """Test handling of very small bounding boxes."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(10, 10), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)

        # Very small bbox (0.001 degrees ≈ 100m)
        result = source.load_data("agbd_2021", bbox=(11.0, 52.0, 11.001, 52.001))

        assert isinstance(result, xr.Dataset)
        mock_cubo_create.assert_called_once()

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_edge_case_large_bbox(self, mock_cubo_create):
        """Test handling of very large bounding boxes."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(1000, 1000), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)

        # Large bbox (10 degrees ≈ 1000km)
        result = source.load_data("agbd_2021", bbox=(5.0, 47.0, 15.0, 57.0))

        assert isinstance(result, xr.Dataset)
        mock_cubo_create.assert_called_once()

    def test_dataset_info_completeness(self):
        """Test that all dataset info fields are properly populated."""
        source = DLRBiomassSource(self.config)
        datasets = source.get_available_datasets()

        for dataset_id, info in datasets.items():
            assert info.id == dataset_id
            assert len(info.name) > 0
            assert len(info.description) > 0
            assert info.spatial_resolution > 0
            assert "/" in info.temporal_coverage  # Should be date range
            assert info.units == "Mg/ha"
            assert info.uncertainty_available is True
            assert info.crs == "EPSG:32632"

    def test_source_properties(self):
        """Test source property methods."""
        source = DLRBiomassSource(self.config)

        assert source.source_name == "DLR"
        assert hasattr(source, 'stac_url')
        assert hasattr(source, 'collection')
        assert hasattr(source, 'resolution')

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_stac_service_timeout(self, mock_cubo_create):
        """Test handling of STAC service timeout."""
        mock_cubo_create.side_effect = TimeoutError("STAC service timeout")

        source = DLRBiomassSource(self.config)

        with pytest.raises(TimeoutError, match="STAC service timeout"):
            source.load_data("agbd_2021", bbox=(10.0, 51.0, 12.0, 53.0))

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_invalid_stac_response(self, mock_cubo_create):
        """Test handling of invalid STAC response."""
        mock_cubo_create.side_effect = ValueError("Invalid STAC collection")

        source = DLRBiomassSource(self.config)

        with pytest.raises(ValueError, match="Invalid STAC collection"):
            source.load_data("agbd_2020")

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_empty_dataset_response(self, mock_cubo_create):
        """Test handling of empty dataset response."""
        # Return empty dataset
        mock_data = xr.Dataset()
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        result = source.load_data("agbd_2021")

        assert isinstance(result, xr.Dataset)
        assert len(result.data_vars) == 0

    @patch('pyproj.Transformer')
    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_coordinate_transformation_error(self, mock_cubo_create, mock_transformer_class):
        """Test handling of coordinate transformation errors."""
        # Mock transformer to raise error
        mock_transformer_class.from_crs.side_effect = Exception("Projection error")

        source = DLRBiomassSource(self.config)

        with pytest.raises(Exception, match="Projection error"):
            source.load_data("agbd_2021", bbox=(10.0, 51.0, 12.0, 53.0))

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_load_data_with_center_calculation(self, mock_cubo_create):
        """Test that center coordinates are calculated correctly from bbox."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        source.load_data("agbd_2021", bbox=(10.0, 50.0, 12.0, 52.0))

        call_kwargs = mock_cubo_create.call_args[1]

        # Check center coordinates
        expected_center_lon = (10.0 + 12.0) / 2  # 11.0
        expected_center_lat = (50.0 + 52.0) / 2  # 51.0

        assert call_kwargs['lat'] == expected_center_lat
        assert call_kwargs['lon'] == expected_center_lon

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_dataset_attributes_comprehensive(self, mock_cubo_create):
        """Test comprehensive dataset attribute setting."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        result = source.load_data("agbd_2021")

        # Check all attributes are properly set
        expected_attrs = {
            'source': 'DLR',
            'dataset_id': 'agbd_2021',
            'units': 'Mg/ha',
            'spatial_resolution': 10.0,
            'temporal_coverage': '2021-01-01/2021-12-31'
        }

        for key, expected_value in expected_attrs.items():
            assert result.attrs[key] == expected_value

    def test_get_metadata_comprehensive_fields(self):
        """Test that metadata contains all required fields."""
        source = DLRBiomassSource(self.config)
        metadata = source.get_metadata("agbd_2020")

        # Check top-level fields
        assert metadata["source"] == "DLR"
        assert metadata["data_format"] == "GeoTIFF COG"
        assert metadata["coordinate_system"] == "EPSG:32632"
        assert metadata["processing_level"] == "L3"
        assert metadata["quality_flags"] == "Available in uncertainty band"

        # Check dataset_info structure
        dataset_info = metadata["dataset_info"]
        assert dataset_info["id"] == "agbd_2020"
        assert dataset_info["name"] == "AGBD 2020"
        assert dataset_info["description"] == "DLR Global Aboveground Biomass Density 2020"
        assert dataset_info["spatial_resolution"] == 10.0
        assert dataset_info["temporal_coverage"] == "2020-01-01/2020-12-31"
        assert dataset_info["units"] == "Mg/ha"
        assert dataset_info["uncertainty_available"] is True
        assert dataset_info["crs"] == "EPSG:32632"

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_cubo_logging_parameters(self, mock_cubo_create):
        """Test that cubo parameters are logged correctly."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)

        with patch('cosmicbiomass.sources.dlr.logger') as mock_logger:
            source.load_data("agbd_2017", bbox=(11.0, 52.0, 11.5, 52.5))

            # Check logging calls
            mock_logger.info.assert_any_call("Loading DLR dataset agbd_2017 via STAC")
            mock_logger.debug.assert_called()  # Should have debug call for parameters

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_successful_loading_logging(self, mock_cubo_create):
        """Test logging of successful data loading."""
        mock_data = xr.Dataset({
            'agbd': xr.DataArray(np.random.rand(100, 100), dims=['y', 'x'])
        })
        # Mock the sizes property to return the expected dict
        mock_data = Mock(spec=xr.Dataset)
        mock_data.sizes = {'y': 100, 'x': 100}
        mock_data.attrs = {}
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)

        with patch('cosmicbiomass.sources.dlr.logger') as mock_logger:
            source.load_data("agbd_2021")

            # Check success logging
            mock_logger.info.assert_any_call("Successfully loaded dataset with shape: {'y': 100, 'x': 100}")

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_error_logging(self, mock_cubo_create):
        """Test error logging when STAC fails."""
        mock_cubo_create.side_effect = Exception("STAC network error")

        source = DLRBiomassSource(self.config)

        with patch('cosmicbiomass.sources.dlr.logger') as mock_logger:
            with pytest.raises(Exception, match="STAC network error"):
                source.load_data("agbd_2021")

            # Check error logging
            mock_logger.error.assert_called_with("Failed to load via STAC: STAC network error")

    def test_dataset_year_extraction(self):
        """Test that year is correctly extracted from dataset_id."""
        source = DLRBiomassSource(self.config)

        # Mock cubo to capture the parameters
        with patch('cosmicbiomass.sources.dlr.cubo.create') as mock_cubo_create:
            mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
            mock_cubo_create.return_value = mock_data

            # Test each year
            for dataset_id, expected_year in [("agbd_2017", "2017"), ("agbd_2020", "2020"), ("agbd_2021", "2021")]:
                source.load_data(dataset_id)

                call_kwargs = mock_cubo_create.call_args[1]
                assert call_kwargs['start_date'] == f"{expected_year}-01-01"
                assert call_kwargs['end_date'] == f"{expected_year}-12-31"

    @patch('pyproj.Transformer')
    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_bbox_edge_size_calculation_precision(self, mock_cubo_create, mock_transformer_class):
        """Test precise edge size calculation from bbox."""
        # Mock transformer with specific values
        mock_transformer = Mock()
        mock_transformer.transform.side_effect = [
            (500000, 5800000),   # x1, y1 in meters
            (520000, 5830000)    # x2, y2 in meters
        ]
        mock_transformer_class.from_crs.return_value = mock_transformer

        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        source.load_data("agbd_2021", bbox=(10.0, 51.0, 12.0, 53.0))

        call_kwargs = mock_cubo_create.call_args[1]

        # Expected edge_size is max of width and height differences
        width_diff = abs(520000 - 500000)  # 20000
        height_diff = abs(5830000 - 5800000)  # 30000
        expected_edge_size = max(width_diff, height_diff)  # 30000

        assert call_kwargs['edge_size'] == expected_edge_size

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_configuration_inheritance(self, mock_cubo_create):
        """Test that source properly inherits from BiomassDataSource."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(10, 10), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        # Test with different config
        config = BiomassConfig(data_dir="/custom/path", n_jobs=4)
        source = DLRBiomassSource(config)

        assert source.config == config
        assert source.config.data_dir == "/custom/path"
        assert source.config.n_jobs == 4

        # Ensure source can still load data
        result = source.load_data("agbd_2021")
        assert isinstance(result, xr.Dataset)

    def test_stac_configuration_constants(self):
        """Test that STAC configuration constants are correct."""
        source = DLRBiomassSource(self.config)

        assert source.stac_url == "https://geoservice.dlr.de/eoc/ogc/stac/v1"
        assert source.collection == "FOREST_STRUCTURE_DE_AGBD_P1Y"
        assert source.resolution == 10
        assert isinstance(source.stac_url, str)
        assert isinstance(source.collection, str)
        assert isinstance(source.resolution, int)

    @patch('cosmicbiomass.sources.dlr.cubo.create')
    def test_all_cubo_parameters_set(self, mock_cubo_create):
        """Test that all required cubo parameters are set correctly."""
        mock_data = xr.Dataset({'agbd': xr.DataArray(np.random.rand(50, 50), dims=['y', 'x'])})
        mock_cubo_create.return_value = mock_data

        source = DLRBiomassSource(self.config)
        source.load_data("agbd_2021", bbox=(11.0, 52.0, 11.5, 52.5))

        call_kwargs = mock_cubo_create.call_args[1]

        # Verify all expected parameters are present
        required_params = ['lat', 'lon', 'stac', 'collection', 'gee',
                          'start_date', 'end_date', 'edge_size', 'units', 'resolution']

        for param in required_params:
            assert param in call_kwargs, f"Missing parameter: {param}"

        # Verify specific values
        assert call_kwargs['stac'] == "https://geoservice.dlr.de/eoc/ogc/stac/v1"
        assert call_kwargs['collection'] == "FOREST_STRUCTURE_DE_AGBD_P1Y"
        assert call_kwargs['gee'] is False
        assert call_kwargs['units'] == "m"
        assert call_kwargs['resolution'] == 10
