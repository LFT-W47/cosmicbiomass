"""
Example tests demonstrating cosmicbiomass package usage.

These tests serve as both validation and documentation, showing how to use
the package API in realistic scenarios. They're designed to be readable
and serve as examples for users.
"""

import pytest
from unittest.mock import patch

import cosmicbiomass
from tests.test_utils import MockDataFactory, ValidationHelpers


class TestUsageExamples:
    """Example tests demonstrating typical package usage."""
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_basic_usage_example(self, mock_cubo_create, mock_rasterio_features):
        """Example: Basic usage of get_average_biomass function."""
        # Setup mock data
        mock_cube = MockDataFactory.create_biomass_cube(
            lat=51.1657, lon=13.7882,  # Dresden, Germany
            biomass_range=(100.0, 200.0)
        )
        mock_cubo_create.return_value = mock_cube
        
        # Example usage as shown in the original request
        neutrons = 1234
        lat = 51.1657  # Dresden, Germany latitude
        lon = 13.7882  # Dresden, Germany longitude
        footprint_radius = 220  # meters
        
        # Extract biomass data
        site_agb, site_agb_err = cosmicbiomass.get_average_biomass(
            lat, lon, footprint_radius
        )
        
        # Apply neutron correction
        neutrons_corrected = neutrons * 1/(1+0.009*site_agb)
        
        # Validate results
        assert ValidationHelpers.validate_biomass_result((site_agb, site_agb_err))
        assert isinstance(neutrons_corrected, (int, float))
        assert 0 < neutrons_corrected < neutrons  # Should reduce neutron count
        
        print(f"Original biomass: {site_agb:.2f} ± {site_agb_err:.2f} Mg/ha")
        print(f"Neutron correction factor: {1/(1+0.009*site_agb):.4f}")
        print(f"Corrected neutrons: {neutrons_corrected:.0f}")
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_custom_data_source_parameters(self, mock_cubo_create, mock_rasterio_features):
        """Example: Using custom data source parameters."""
        mock_cube = MockDataFactory.create_biomass_cube()
        mock_cubo_create.return_value = mock_cube
        
        # Use custom parameters for data extraction
        site_agb, site_agb_err = cosmicbiomass.get_average_biomass(
            lat=45.0,
            lon=8.0,
            footprint_radius=300,
            # Custom DLR source parameters
            collection="CUSTOM_FOREST_STRUCTURE",
            resolution=20,  # 20m resolution instead of default 10m
            start_date="2021-01-01",
            end_date="2022-12-31"
        )
        
        assert ValidationHelpers.validate_biomass_result((site_agb, site_agb_err))
        
        # Verify custom parameters were used
        call_kwargs = mock_cubo_create.call_args[1]
        assert call_kwargs["collection"] == "CUSTOM_FOREST_STRUCTURE"
        assert call_kwargs["resolution"] == 20
        assert call_kwargs["start_date"] == "2021-01-01"
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_multiple_locations_comparison(self, mock_cubo_create, mock_rasterio_features):
        """Example: Comparing biomass across multiple locations."""
        # Define test locations with different expected biomass levels
        locations = {
            "temperate_forest": {
                "lat": 51.0, "lon": 13.0, "expected_range": (80, 250)
            },
            "tropical_forest": {
                "lat": -3.0, "lon": -60.0, "expected_range": (200, 450)
            },
            "sparse_vegetation": {
                "lat": 35.0, "lon": -110.0, "expected_range": (5, 50)
            }
        }
        
        results = {}
        
        for location_name, location_data in locations.items():
            # Create appropriate mock data for each location type
            expected_min, expected_max = location_data["expected_range"]
            mock_cube = MockDataFactory.create_biomass_cube(
                lat=location_data["lat"],
                lon=location_data["lon"],
                biomass_range=(expected_min, expected_max)
            )
            mock_cubo_create.return_value = mock_cube
            
            # Extract biomass
            agb, agb_err = cosmicbiomass.get_average_biomass(
                lat=location_data["lat"],
                lon=location_data["lon"],
                footprint_radius=200
            )
            
            results[location_name] = {"biomass": agb, "uncertainty": agb_err}
            
            # Validate result is in expected range
            assert expected_min <= agb <= expected_max
            assert agb_err >= 0
        
        # Compare results
        tropical_biomass = results["tropical_forest"]["biomass"]
        temperate_biomass = results["temperate_forest"]["biomass"]
        sparse_biomass = results["sparse_vegetation"]["biomass"]
        
        # Tropical should have highest biomass, sparse should have lowest
        assert tropical_biomass > temperate_biomass > sparse_biomass
        
        print("Biomass comparison across locations:")
        for name, data in results.items():
            print(f"  {name}: {data['biomass']:.1f} ± {data['uncertainty']:.1f} Mg/ha")
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_footprint_size_sensitivity(self, mock_cubo_create, mock_rasterio_features):
        """Example: Testing sensitivity to footprint size."""
        mock_cube = MockDataFactory.create_biomass_cube(
            biomass_range=(100, 200), add_noise=True
        )
        mock_cubo_create.return_value = mock_cube
        
        footprint_sizes = [50, 100, 200, 500]  # meters
        results = []
        
        lat, lon = 51.0, 13.0
        
        for radius in footprint_sizes:
            agb, agb_err = cosmicbiomass.get_average_biomass(
                lat=lat, lon=lon, footprint_radius=radius
            )
            
            results.append({
                "radius": radius,
                "biomass": agb,
                "uncertainty": agb_err
            })
            
            assert ValidationHelpers.validate_biomass_result((agb, agb_err))
        
        print("Footprint size sensitivity analysis:")
        for result in results:
            print(f"  {result['radius']}m radius: "
                  f"{result['biomass']:.1f} ± {result['uncertainty']:.1f} Mg/ha")
        
        # All results should be reasonable and similar (with synthetic uniform-ish data)
        biomass_values = [r["biomass"] for r in results]
        biomass_std = np.std(biomass_values)
        
        # With our synthetic data, variation should be relatively small
        assert biomass_std < 50, f"Unexpected variation across footprint sizes: {biomass_std}"
    
    @pytest.mark.unit
    def test_configuration_customization_example(self):
        """Example: Customizing package configuration."""
        # Create custom configuration for high-precision analysis
        high_precision_config = cosmicbiomass.CosmicBiomassConfig(
            default_upsample_factor=20,  # Higher precision footprint
            edge_size_buffer=2.0,         # Larger data buffer
            n_jobs=4,                     # Parallel processing
            default_resolution=5          # Higher resolution data
        )
        
        # Verify configuration
        assert high_precision_config.default_upsample_factor == 20
        assert high_precision_config.edge_size_buffer == 2.0
        assert high_precision_config.n_jobs == 4
        assert high_precision_config.default_resolution == 5
        
        # Configuration validation should work
        assert high_precision_config.default_upsample_factor >= 1
        assert high_precision_config.edge_size_buffer >= 1.0
        
        print("Custom configuration created:")
        print(f"  Upsample factor: {high_precision_config.default_upsample_factor}")
        print(f"  Edge buffer: {high_precision_config.edge_size_buffer}")
        print(f"  Parallel jobs: {high_precision_config.n_jobs}")
    
    @pytest.mark.unit
    def test_source_registry_example(self):
        """Example: Working with the data source registry."""
        # Get available sources
        available_sources = cosmicbiomass.source_registry.list_sources()
        print(f"Available data sources: {available_sources}")
        
        # Get information about a source
        dlr_info = cosmicbiomass.source_registry.get_source_info("dlr")
        print("DLR source information:")
        for key, value in dlr_info.items():
            print(f"  {key}: {value}")
        
        # Verify basic functionality
        assert "dlr" in available_sources
        assert isinstance(dlr_info, dict)
        assert "name" in dlr_info
        assert "units" in dlr_info
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_error_handling_example(self, mock_cubo_create):
        """Example: Proper error handling."""
        # Test with invalid coordinates
        with pytest.raises(ValueError, match="Latitude must be between"):
            cosmicbiomass.get_average_biomass(lat=95.0, lon=0.0, footprint_radius=100)
        
        with pytest.raises(ValueError, match="Longitude must be between"):
            cosmicbiomass.get_average_biomass(lat=0.0, lon=185.0, footprint_radius=100)
        
        with pytest.raises(ValueError, match="Footprint radius must be positive"):
            cosmicbiomass.get_average_biomass(lat=0.0, lon=0.0, footprint_radius=-100)
        
        # Test with data extraction failure
        mock_cubo_create.side_effect = ConnectionError("Network unavailable")
        
        with pytest.raises(RuntimeError, match="Biomass extraction failed"):
            cosmicbiomass.get_average_biomass(lat=51.0, lon=13.0, footprint_radius=200)
        
        print("Error handling examples completed - all errors properly caught")


class TestRealWorldScenarios:
    """Examples based on real-world usage scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.mock
    def test_research_station_monitoring(self, mock_cubo_create, mock_rasterio_features):
        """Example: Monitoring biomass around research stations."""
        # Simulate multiple research stations
        stations = [
            {"name": "Alpine Station", "lat": 46.5, "lon": 8.0, "radius": 150},
            {"name": "Forest Station", "lat": 52.0, "lon": 12.0, "radius": 200},
            {"name": "Coastal Station", "lat": 54.0, "lon": 10.0, "radius": 100},
        ]
        
        monitoring_results = []
        
        for station in stations:
            # Create appropriate biomass data for each station type
            if "Alpine" in station["name"]:
                biomass_range = (20, 80)  # Lower alpine biomass
            elif "Forest" in station["name"]:
                biomass_range = (100, 250)  # Forest biomass
            else:
                biomass_range = (30, 120)  # Coastal vegetation
            
            mock_cube = MockDataFactory.create_biomass_cube(
                lat=station["lat"], lon=station["lon"],
                biomass_range=biomass_range
            )
            mock_cubo_create.return_value = mock_cube
            
            # Monitor biomass
            agb, agb_err = cosmicbiomass.get_average_biomass(
                lat=station["lat"],
                lon=station["lon"],
                footprint_radius=station["radius"]
            )
            
            monitoring_results.append({
                "station": station["name"],
                "biomass": agb,
                "uncertainty": agb_err,
                "coordinates": (station["lat"], station["lon"])
            })
        
        # Validate all results
        for result in monitoring_results:
            assert ValidationHelpers.validate_biomass_result(
                (result["biomass"], result["uncertainty"])
            )
        
        print("Research station monitoring results:")
        for result in monitoring_results:
            print(f"  {result['station']}: "
                  f"{result['biomass']:.1f} ± {result['uncertainty']:.1f} Mg/ha "
                  f"at {result['coordinates']}")
        
        # Forest station should have highest biomass
        forest_result = next(r for r in monitoring_results if "Forest" in r["station"])
        alpine_result = next(r for r in monitoring_results if "Alpine" in r["station"])
        
        assert forest_result["biomass"] > alpine_result["biomass"]
    
    @pytest.mark.integration
    @pytest.mark.mock  
    def test_neutron_correction_workflow(self, mock_cubo_create, mock_rasterio_features):
        """Example: Complete neutron correction workflow."""
        # Setup realistic biomass data
        mock_cube = MockDataFactory.create_biomass_cube(
            lat=51.1657, lon=13.7882,  # Dresden
            biomass_range=(120, 180),   # Moderate forest biomass
            add_noise=True
        )
        mock_cubo_create.return_value = mock_cube
        
        # Simulated neutron measurements at different locations
        measurements = [
            {"location": "Site A", "lat": 51.16, "lon": 13.78, "neutrons": 1250, "radius": 220},
            {"location": "Site B", "lat": 51.17, "lon": 13.79, "neutrons": 1180, "radius": 220},
            {"location": "Site C", "lat": 51.15, "lon": 13.77, "neutrons": 1320, "radius": 220},
        ]
        
        corrected_measurements = []
        
        for measurement in measurements:
            # Get biomass data for the measurement location
            site_agb, site_agb_err = cosmicbiomass.get_average_biomass(
                lat=measurement["lat"],
                lon=measurement["lon"],
                footprint_radius=measurement["radius"]
            )
            
            # Apply neutron correction (from original request)
            correction_factor = 1 / (1 + 0.009 * site_agb)
            neutrons_corrected = measurement["neutrons"] * correction_factor
            
            corrected_measurements.append({
                "location": measurement["location"],
                "original_neutrons": measurement["neutrons"],
                "biomass": site_agb,
                "biomass_uncertainty": site_agb_err,
                "correction_factor": correction_factor,
                "corrected_neutrons": neutrons_corrected
            })
        
        print("Neutron correction workflow results:")
        print("Location | Original | Biomass (Mg/ha) | Correction | Corrected")
        print("-" * 65)
        
        for result in corrected_measurements:
            print(f"{result['location']:8} | "
                  f"{result['original_neutrons']:8.0f} | "
                  f"{result['biomass']:6.1f} ± {result['biomass_uncertainty']:4.1f} | "
                  f"{result['correction_factor']:10.4f} | "
                  f"{result['corrected_neutrons']:9.0f}")
        
        # Validate all corrections
        for result in corrected_measurements:
            assert result["corrected_neutrons"] < result["original_neutrons"]
            assert 0.3 < result["correction_factor"] < 1.0  # Adjusted range for realistic biomass values
            assert ValidationHelpers.validate_biomass_result(
                (result["biomass"], result["biomass_uncertainty"])
            )


# Import numpy for the examples
import numpy as np
