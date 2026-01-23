"""
Comprehensive unit tests for the core module.
"""

from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from cosmicbiomass.config import FootprintConfig
from cosmicbiomass.core import (
    get_average_biomass,
    get_average_biomass_timeseries,
    list_available_datasets,
    validate_coordinates,
)
from cosmicbiomass.processing import BiomassStatistics


class TestValidateCoordinates:
    """Test coordinate validation function."""

    def test_valid_coordinates(self):
        """Test validation of valid coordinates."""
        assert validate_coordinates(52.09, 11.226) is True
        assert validate_coordinates(0.0, 0.0) is True
        assert validate_coordinates(-90.0, -180.0) is True
        assert validate_coordinates(90.0, 180.0) is True

    def test_invalid_latitude(self):
        """Test validation of invalid latitude."""
        assert validate_coordinates(91.0, 11.226) is False
        assert validate_coordinates(-91.0, 11.226) is False

    def test_invalid_longitude(self):
        """Test validation of invalid longitude."""
        assert validate_coordinates(52.09, 181.0) is False
        assert validate_coordinates(52.09, -181.0) is False


class TestParameterValidation:
    """Test parameter validation."""

    def test_invalid_radius(self):
        """Test that invalid radius values are rejected."""
        with pytest.raises(ValueError):
            FootprintConfig(radius=-100.0)

        with pytest.raises(ValueError):
            FootprintConfig(radius=0.0)

    def test_invalid_footprint_shape(self):
        """Test that invalid footprint shapes are rejected."""
        with pytest.raises(ValueError, match="Footprint shape must be"):
            FootprintConfig(radius=100.0, shape="invalid")


class TestGetAverageBiomass:
    """Comprehensive tests for get_average_biomass function."""

    def create_mock_biomass_data(self, shape=(10, 10), add_uncertainty=False):
        """Create mock biomass data for testing."""
        # Create coordinates
        lat_coords = np.linspace(52.0, 52.1, shape[0])
        lon_coords = np.linspace(11.0, 11.1, shape[1])

        # Create biomass data with realistic values
        biomass_values = np.random.uniform(50, 200, shape)

        if add_uncertainty:
            # Create data with uncertainty band
            uncertainty_values = biomass_values * 0.1  # 10% uncertainty
            data = xr.Dataset({
                'agbd_cog': (('lat', 'lon'), biomass_values),
                'uncertainty': (('lat', 'lon'), uncertainty_values)
            }, coords={'lat': lat_coords, 'lon': lon_coords})
        else:
            # Create data without uncertainty
            data = xr.Dataset({
                'agbd_cog': (('lat', 'lon'), biomass_values)
            }, coords={'lat': lat_coords, 'lon': lon_coords})

        return data

    def create_mock_statistics(self, mean=150.0, std=25.0, count=100, uncertainty_mean=None):
        """Create mock BiomassStatistics object."""
        return BiomassStatistics(
            mean=mean,
            std=std,
            median=mean,  # Added missing median field
            min=mean - 2*std,
            max=mean + 2*std,
            count=count,
            uncertainty_mean=uncertainty_mean,
            uncertainty_std=uncertainty_mean * 0.1 if uncertainty_mean else None
        )

    @patch('cosmicbiomass.core.get_source')
    @patch('cosmicbiomass.core.FootprintProcessor')
    @patch('cosmicbiomass.core.StatisticsProcessor')
    @patch('cosmicbiomass.core.validate_footprint_coverage')
    def test_basic_biomass_calculation(self, mock_validate, mock_stats_proc, mock_footprint_proc, mock_get_source):
        """Test basic biomass calculation with mocked components."""
        # Setup mocks
        mock_data_source = Mock()
        mock_biomass_data = self.create_mock_biomass_data()
        mock_data_source.load_data.return_value = mock_biomass_data
        mock_data_source.get_metadata.return_value = {
            'dataset_info': {
                'units': 'Mg/ha',
                'spatial_resolution': '100m',
                'temporal_coverage': '2021'
            }
        }
        mock_get_source.return_value = mock_data_source

        # Mock footprint processor
        mock_fp_instance = Mock()
        mock_weights = np.ones((10, 10))
        mock_fp_instance.compute_footprint_weights.return_value = mock_weights
        mock_footprint_proc.return_value = mock_fp_instance

        # Mock statistics processor
        mock_stats_instance = Mock()
        mock_stats = self.create_mock_statistics()
        mock_stats_instance.compute_weighted_statistics.return_value = mock_stats
        mock_stats_proc.return_value = mock_stats_instance

        mock_validate.return_value = True

        # Execute function
        result = get_average_biomass(52.09, 11.226, radius=500.0)

        # Verify calls
        mock_get_source.assert_called_once()
        mock_data_source.load_data.assert_called_once()
        mock_fp_instance.compute_footprint_weights.assert_called_once_with(mock_biomass_data, 52.09, 11.226)
        mock_stats_instance.compute_weighted_statistics.assert_called_once()

        # Verify result structure
        assert isinstance(result, pd.DataFrame)
        assert 'mean_biomass_Mg_ha' in result.columns
        assert 'std_biomass_Mg_ha' in result.columns
        assert 'pixel_count' in result.columns
        assert 'dataset' in result.columns
        assert 'source' in result.columns

        # Verify location data
        assert result.iloc[0]['latitude'] == 52.09
        assert result.iloc[0]['longitude'] == 11.226
        assert result.iloc[0]['radius_m'] == 500.0

        # Verify summary data
        assert result.iloc[0]['mean_biomass_Mg_ha'] == 150.0
        assert result.iloc[0]['std_biomass_Mg_ha'] == 25.0
        assert result.iloc[0]['pixel_count'] == 100

        # Verify full result payload preserved
        assert 'result' in result.attrs
        assert 'biomass_statistics' in result.attrs['result']
        assert 'location' in result.attrs['result']
        assert 'footprint' in result.attrs['result']
        assert 'data_info' in result.attrs['result']
        assert 'processing' in result.attrs['result']
        assert 'summary' in result.attrs['result']

    @patch('cosmicbiomass.core.get_source')
    @patch('cosmicbiomass.core.FootprintProcessor')
    @patch('cosmicbiomass.core.StatisticsProcessor')
    @patch('cosmicbiomass.core.validate_footprint_coverage')
    def test_biomass_with_uncertainty_band(self, mock_validate, mock_stats_proc, mock_footprint_proc, mock_get_source):
        """Test biomass calculation with separate uncertainty band."""
        # Setup mocks with uncertainty data
        mock_data_source = Mock()
        mock_biomass_data = self.create_mock_biomass_data(add_uncertainty=True)
        mock_data_source.load_data.return_value = mock_biomass_data
        mock_data_source.get_metadata.return_value = {'dataset_info': {}}
        mock_get_source.return_value = mock_data_source

        # Mock processors
        mock_fp_instance = Mock()
        mock_weights = np.ones((10, 10))
        mock_fp_instance.compute_footprint_weights.return_value = mock_weights
        mock_footprint_proc.return_value = mock_fp_instance

        mock_stats_instance = Mock()
        mock_stats = self.create_mock_statistics(uncertainty_mean=15.0)
        mock_stats_instance.compute_weighted_statistics.return_value = mock_stats
        mock_stats_proc.return_value = mock_stats_instance

        mock_validate.return_value = True

        # Execute function
        result = get_average_biomass(52.09, 11.226, include_uncertainty=True)

        # Verify uncertainty in result
        assert result.iloc[0]['uncertainty_Mg_ha'] == 15.0
        assert result.iloc[0]['uncertainty_source'] == 'uncertainty_band'
        assert result.attrs['result']['summary']['uncertainty_Mg_ha'] == 15.0
        assert result.attrs['result']['summary']['uncertainty_source'] == 'uncertainty_band'

    @patch('cosmicbiomass.core.get_source')
    @patch('cosmicbiomass.core.FootprintProcessor')
    @patch('cosmicbiomass.core.StatisticsProcessor')
    @patch('cosmicbiomass.core.validate_footprint_coverage')
    def test_biomass_without_uncertainty_band(self, mock_validate, mock_stats_proc, mock_footprint_proc, mock_get_source):
        """Test biomass calculation without uncertainty band (uses std)."""
        # Setup mocks without uncertainty data
        mock_data_source = Mock()
        mock_biomass_data = self.create_mock_biomass_data(add_uncertainty=False)
        mock_data_source.load_data.return_value = mock_biomass_data
        mock_data_source.get_metadata.return_value = {'dataset_info': {}}
        mock_get_source.return_value = mock_data_source

        # Mock processors
        mock_fp_instance = Mock()
        mock_weights = np.ones((10, 10))
        mock_fp_instance.compute_footprint_weights.return_value = mock_weights
        mock_footprint_proc.return_value = mock_fp_instance

        mock_stats_instance = Mock()
        mock_stats = self.create_mock_statistics(uncertainty_mean=None)  # No uncertainty band
        mock_stats_instance.compute_weighted_statistics.return_value = mock_stats
        mock_stats_proc.return_value = mock_stats_instance

        mock_validate.return_value = True

        # Execute function
        result = get_average_biomass(52.09, 11.226, include_uncertainty=True)

        # Verify uncertainty uses std
        assert result.iloc[0]['uncertainty_Mg_ha'] == 25.0  # Same as std
        assert result.iloc[0]['uncertainty_source'] == 'data_spread'
        assert result.attrs['result']['summary']['uncertainty_Mg_ha'] == 25.0
        assert result.attrs['result']['summary']['uncertainty_source'] == 'data_spread'

    @patch('cosmicbiomass.core.get_source')
    def test_data_loading_error(self, mock_get_source):
        """Test handling of data loading errors."""
        mock_data_source = Mock()
        mock_data_source.load_data.side_effect = Exception("Data loading failed")
        mock_get_source.return_value = mock_data_source

        with pytest.raises(Exception, match="Data loading failed"):
            get_average_biomass(52.09, 11.226)

    @patch('cosmicbiomass.core.get_source')
    @patch('cosmicbiomass.core.FootprintProcessor')
    def test_footprint_computation_error(self, mock_footprint_proc, mock_get_source):
        """Test handling of footprint computation errors."""
        # Setup data source mock
        mock_data_source = Mock()
        mock_data_source.load_data.return_value = self.create_mock_biomass_data()
        mock_get_source.return_value = mock_data_source

        # Mock footprint processor to raise error
        mock_fp_instance = Mock()
        mock_fp_instance.compute_footprint_weights.side_effect = Exception("Footprint computation failed")
        mock_footprint_proc.return_value = mock_fp_instance

        with pytest.raises(Exception, match="Footprint computation failed"):
            get_average_biomass(52.09, 11.226)

    @patch('cosmicbiomass.core.get_source')
    @patch('cosmicbiomass.core.FootprintProcessor')
    @patch('cosmicbiomass.core.StatisticsProcessor')
    def test_statistics_computation_error(self, mock_stats_proc, mock_footprint_proc, mock_get_source):
        """Test handling of statistics computation errors."""
        # Setup data source and footprint processor mocks
        mock_data_source = Mock()
        mock_data_source.load_data.return_value = self.create_mock_biomass_data()
        mock_get_source.return_value = mock_data_source

        mock_fp_instance = Mock()
        mock_fp_instance.compute_footprint_weights.return_value = np.ones((10, 10))
        mock_footprint_proc.return_value = mock_fp_instance

        # Mock statistics processor to raise error
        mock_stats_instance = Mock()
        mock_stats_instance.compute_weighted_statistics.side_effect = Exception("Statistics computation failed")
        mock_stats_proc.return_value = mock_stats_instance

        with pytest.raises(Exception, match="Statistics computation failed"):
            get_average_biomass(52.09, 11.226)

    @patch('cosmicbiomass.core.get_source')
    @patch('cosmicbiomass.core.FootprintProcessor')
    @patch('cosmicbiomass.core.StatisticsProcessor')
    @patch('cosmicbiomass.core.validate_footprint_coverage')
    def test_custom_parameters(self, mock_validate, mock_stats_proc, mock_footprint_proc, mock_get_source):
        """Test biomass calculation with custom parameters."""
        # Setup mocks
        mock_data_source = Mock()
        mock_biomass_data = self.create_mock_biomass_data()
        mock_data_source.load_data.return_value = mock_biomass_data
        mock_data_source.get_metadata.return_value = {'dataset_info': {}}
        mock_get_source.return_value = mock_data_source

        mock_fp_instance = Mock()
        mock_fp_instance.compute_footprint_weights.return_value = np.ones((10, 10))
        mock_footprint_proc.return_value = mock_fp_instance

        mock_stats_instance = Mock()
        mock_stats = self.create_mock_statistics()
        mock_stats_instance.compute_weighted_statistics.return_value = mock_stats
        mock_stats_proc.return_value = mock_stats_instance

        mock_validate.return_value = True

        # Execute with custom parameters
        result = get_average_biomass(
            52.09, 11.226,
            radius=1000.0,
            source="custom_source",
            dataset="custom_dataset",
            footprint_shape="gaussian",
            outlier_method="iqr",
            include_uncertainty=False
        )

        # Verify custom parameters are used
        assert result.iloc[0]['radius_m'] == 1000.0
        assert result.iloc[0]['source'] == "custom_source"
        assert result.iloc[0]['dataset'] == "custom_dataset"
        assert result.attrs['result']['processing']['outlier_method'] == "iqr"
        assert result.attrs['result']['processing']['include_uncertainty'] is False


class TestGetAverageBiomassTimeseries:
    """Tests for get_average_biomass_timeseries function."""

    @patch('cosmicbiomass.core.get_average_biomass')
    def test_timeseries_dataframe_structure(self, mock_get_average):
        """Test timeseries DataFrame columns and metadata."""
        mock_get_average.return_value = {
            "summary": {
                "mean_biomass_Mg_ha": 100.0,
                "std_biomass_Mg_ha": 12.0,
                "uncertainty_Mg_ha": 10.0,
                "uncertainty_source": "data_spread",
                "pixel_count": 25,
            }
        }

        df = get_average_biomass_timeseries(
            lat=52.0,
            lon=11.0,
            dataset="agbd_{year}",
            start_time=2020,
            end_time=2021,
        )

        assert isinstance(df, pd.DataFrame)
        assert "year" not in df.columns
        assert "dataset" not in df.columns
        assert "mean_biomass_Mg_ha" in df.columns
        assert "std_biomass_Mg_ha" in df.columns
        assert "uncertainty_Mg_ha" in df.columns
        assert "uncertainty_source" in df.columns
        assert "pixel_count" in df.columns
        assert isinstance(df.index, pd.PeriodIndex)
        assert df.index.name == "year"
        assert df.attrs["source"] == "dlr"
        assert df.attrs["dataset_template"] == "agbd_{year}"
        assert df.attrs["datasets"] == {2020: "agbd_2020", 2021: "agbd_2021"}
        assert len(df.attrs["series"]) == 2


class TestListAvailableDatasets:
    """Test the list_available_datasets function."""

    @patch('cosmicbiomass.core.get_source')
    def test_list_datasets(self, mock_get_source):
        """Test listing available datasets."""
        # Setup mock data source
        mock_data_source = Mock()
        mock_datasets = {
            'agbd_2021': Mock(),
            'agbd_2020': Mock()
        }
        # Make the mock objects have a dict() method
        for dataset in mock_datasets.values():
            dataset.dict.return_value = {
                'name': 'test_dataset',
                'units': 'Mg/ha',
                'description': 'Test dataset'
            }

        mock_data_source.get_available_datasets.return_value = mock_datasets
        mock_get_source.return_value = mock_data_source

        # Execute function
        result = list_available_datasets(source="dlr")

        # Verify result
        assert result['source'] == "dlr"
        assert 'datasets' in result
        assert 'agbd_2021' in result['datasets']
        assert 'agbd_2020' in result['datasets']

        # Verify calls
        mock_get_source.assert_called_once()
        mock_data_source.get_available_datasets.assert_called_once()
