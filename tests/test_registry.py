"""
Unit tests for the registry module.

Tests the data source registry and source management functionality.
"""

from unittest.mock import Mock

import pytest

from cosmicbiomass.config import BiomassConfig
from cosmicbiomass.registry import (
    SourceRegistry,
    clear_source_cache,
    get_source,
    list_available_sources,
    register_source,
)
from cosmicbiomass.sources.base import BiomassDataSource
from cosmicbiomass.sources.dlr import DLRBiomassSource


class MockDataSource(BiomassDataSource):
    """Mock data source for testing."""

    @property
    def source_name(self):
        return "mock"

    def get_available_datasets(self):
        return {"test_dataset": {"id": "test", "name": "Test Dataset"}}

    def load_data(self, dataset_id, bbox=None):
        return Mock()

    def get_metadata(self, dataset_id):
        return {"source": "mock", "dataset_id": dataset_id}


class TestSourceRegistry:
    """Test the SourceRegistry class."""

    def test_registry_initialization(self):
        """Test registry is initialized with built-in sources."""
        registry = SourceRegistry()

        # Should have DLR source registered by default
        sources = registry.list_sources()
        assert "dlr" in sources

    def test_register_source(self):
        """Test registering a new data source."""
        registry = SourceRegistry()

        # Register mock source
        registry.register_source("mock", MockDataSource)

        sources = registry.list_sources()
        assert "mock" in sources

    def test_register_invalid_source(self):
        """Test registering an invalid data source raises error."""
        registry = SourceRegistry()

        # Try to register a class that doesn't inherit from BiomassDataSource
        with pytest.raises(ValueError, match="Source class must inherit from BiomassDataSource"):
            registry.register_source("invalid", str)

    def test_get_source(self):
        """Test getting a source instance."""
        registry = SourceRegistry()
        config = BiomassConfig()

        # Get DLR source
        source = registry.get_source("dlr", config)
        assert isinstance(source, DLRBiomassSource)
        assert source.config == config

    def test_get_unknown_source(self):
        """Test getting an unknown source raises error."""
        registry = SourceRegistry()
        config = BiomassConfig()

        with pytest.raises(ValueError, match="Unknown data source: unknown"):
            registry.get_source("unknown", config)

    def test_source_caching(self):
        """Test that source instances are cached."""
        registry = SourceRegistry()
        config = BiomassConfig()

        # Get same source twice
        source1 = registry.get_source("dlr", config)
        source2 = registry.get_source("dlr", config)

        # Should be the same instance
        assert source1 is source2

    def test_cache_invalidation_on_config_change(self):
        """Test that cache is invalidated when config changes."""
        registry = SourceRegistry()
        config1 = BiomassConfig(data_dir="data1")
        config2 = BiomassConfig(data_dir="data2")

        # Get source with first config
        source1 = registry.get_source("dlr", config1)

        # Get source with different config
        source2 = registry.get_source("dlr", config2)

        # Should be different instances due to different configs
        assert source1 is not source2
        assert source1.config != source2.config

    def test_clear_cache(self):
        """Test clearing the source cache."""
        registry = SourceRegistry()
        config = BiomassConfig()

        # Get source to populate cache
        source1 = registry.get_source("dlr", config)

        # Clear cache
        registry.clear_cache()

        # Get source again - should be new instance
        source2 = registry.get_source("dlr", config)
        assert source1 is not source2


class TestGlobalRegistryFunctions:
    """Test the global registry functions."""

    def test_get_source_global(self):
        """Test global get_source function."""
        config = BiomassConfig()
        source = get_source("dlr", config)

        assert isinstance(source, DLRBiomassSource)

    def test_register_source_global(self):
        """Test global register_source function."""
        # Register mock source globally
        register_source("mock", MockDataSource)

        # Should be available in global registry
        sources = list_available_sources()
        assert "mock" in sources

        # Should be able to get it
        config = BiomassConfig()
        source = get_source("mock", config)
        assert isinstance(source, MockDataSource)

    def test_list_available_sources(self):
        """Test listing available sources."""
        sources = list_available_sources()

        assert isinstance(sources, list)
        assert "dlr" in sources

    def test_clear_source_cache_global(self):
        """Test global cache clearing."""
        config = BiomassConfig()

        # Get source to populate cache
        get_source("dlr", config)

        # Clear cache globally
        clear_source_cache()

        # Get source again - might be new instance (depends on implementation)
        get_source("dlr", config)
        # Note: This test mainly ensures no errors occur

    def test_register_source_global_cleanup(self):
        """Test that global registration can be cleaned up."""
        # Register a temporary source
        register_source("temp", MockDataSource)

        # Verify it's registered
        sources = list_available_sources()
        assert "temp" in sources

        # Clear cache to clean up
        clear_source_cache()


class TestRegistryEdgeCases:
    """Test edge cases and error conditions for the registry."""

    def test_case_insensitive_source_names(self):
        """Test that source names are case insensitive."""
        registry = SourceRegistry()
        config = BiomassConfig()

        # Register with uppercase
        registry.register_source("TEST", MockDataSource)

        # Should be able to get with lowercase
        source = registry.get_source("test", config)
        assert isinstance(source, MockDataSource)

        # Should also work with mixed case
        source2 = registry.get_source("TeSt", config)
        assert source is source2  # Should be same cached instance

    def test_source_registration_overwrite(self):
        """Test that registering the same source name overwrites previous."""
        registry = SourceRegistry()

        # Register first source
        registry.register_source("test", MockDataSource)
        sources = registry.list_sources()
        assert "test" in sources

        # Register different source with same name
        class AnotherMockSource(BiomassDataSource):
            @property
            def source_name(self):
                return "another"
            def get_available_datasets(self):
                return {}
            def load_data(self, dataset_id, bbox=None):
                return Mock()
            def get_metadata(self, dataset_id):
                return {}

        registry.register_source("test", AnotherMockSource)

        # Should use new source class
        config = BiomassConfig()
        source = registry.get_source("test", config)
        assert isinstance(source, AnotherMockSource)

    def test_cache_key_generation(self):
        """Test that cache keys are generated correctly."""
        registry = SourceRegistry()

        # Create configs with different parameters
        config1 = BiomassConfig(data_dir="dir1", n_jobs=1)
        config2 = BiomassConfig(data_dir="dir2", n_jobs=1)
        config3 = BiomassConfig(data_dir="dir1", n_jobs=2)

        # Get sources with different configs
        source1 = registry.get_source("dlr", config1)
        source2 = registry.get_source("dlr", config2)
        source3 = registry.get_source("dlr", config3)

        # Should all be different instances due to different configs
        assert source1 is not source2
        assert source1 is not source3
        assert source2 is not source3

    def test_registry_state_isolation(self):
        """Test that multiple registry instances are isolated."""
        registry1 = SourceRegistry()
        registry2 = SourceRegistry()

        # Register source in first registry only
        registry1.register_source("test1", MockDataSource)

        # Should not affect second registry
        sources1 = registry1.list_sources()
        sources2 = registry2.list_sources()

        assert "test1" in sources1
        assert "test1" not in sources2
        assert "dlr" in sources1  # Built-in source
        assert "dlr" in sources2  # Built-in source

    def test_invalid_source_error_message(self):
        """Test that error messages include available sources."""
        registry = SourceRegistry()
        config = BiomassConfig()

        # Try to get non-existent source
        with pytest.raises(ValueError) as exc_info:
            registry.get_source("nonexistent", config)

        error_msg = str(exc_info.value)
        assert "Unknown data source: nonexistent" in error_msg
        assert "Available:" in error_msg
        assert "dlr" in error_msg  # Should list available sources

    def test_config_equality_caching(self):
        """Test that config equality affects caching correctly."""
        registry = SourceRegistry()

        # Create identical configs
        config1 = BiomassConfig(data_dir="test", n_jobs=1)
        config2 = BiomassConfig(data_dir="test", n_jobs=1)

        # Should be equal but different objects
        assert config1 == config2
        assert config1 is not config2

        # Get sources with equal configs
        source1 = registry.get_source("dlr", config1)
        source2 = registry.get_source("dlr", config2)

        # Should return same cached instance due to config equality
        assert source1 is source2

    def test_multiple_source_types_caching(self):
        """Test caching with multiple different source types."""
        registry = SourceRegistry()
        registry.register_source("mock", MockDataSource)

        config = BiomassConfig()

        # Get different source types
        dlr_source = registry.get_source("dlr", config)
        mock_source = registry.get_source("mock", config)

        # Should be different instances of different types
        assert isinstance(dlr_source, DLRBiomassSource)
        assert isinstance(mock_source, MockDataSource)
        assert dlr_source is not mock_source

        # Getting same sources again should return cached instances
        dlr_source2 = registry.get_source("dlr", config)
        mock_source2 = registry.get_source("mock", config)

        assert dlr_source is dlr_source2
        assert mock_source is mock_source2

    def test_cache_clearing_selective(self):
        """Test that cache clearing affects all cached instances."""
        registry = SourceRegistry()
        registry.register_source("mock", MockDataSource)

        config = BiomassConfig()

        # Get multiple sources to populate cache
        dlr_source1 = registry.get_source("dlr", config)
        mock_source1 = registry.get_source("mock", config)

        # Clear cache
        registry.clear_cache()

        # Get sources again - should be new instances
        dlr_source2 = registry.get_source("dlr", config)
        mock_source2 = registry.get_source("mock", config)

        # Instances should be different after cache clear
        assert dlr_source1 is not dlr_source2
        assert mock_source1 is not mock_source2

    def test_registry_logging(self):
        """Test that registry operations are logged correctly."""
        from unittest.mock import patch
        registry = SourceRegistry()

        with patch('cosmicbiomass.registry.logger') as mock_logger:
            # Test source registration logging
            registry.register_source("test", MockDataSource)
            mock_logger.debug.assert_any_call("Registered data source: test")

            # Test source creation logging
            config = BiomassConfig()
            registry.get_source("test", config)
            mock_logger.debug.assert_any_call("Created data source instance: test")

            # Test cache clearing logging
            registry.clear_cache()
            mock_logger.debug.assert_any_call("Cleared source instance cache")

    def test_source_inheritance_validation_strict(self):
        """Test strict validation of source class inheritance."""
        registry = SourceRegistry()

        # Test with class that doesn't inherit from BiomassDataSource
        class NotADataSource:
            pass

        with pytest.raises(ValueError, match="Source class must inherit from BiomassDataSource"):
            registry.register_source("invalid", NotADataSource)

        # Test with valid subclass (should work)
        registry.register_source("valid", MockDataSource)
        sources = registry.list_sources()
        assert "valid" in sources

    def test_global_registry_singleton_behavior(self):
        """Test that global registry functions use the same instance."""
        # Get source using global function
        config = BiomassConfig()
        get_source("dlr", config)

        # Register new source globally
        register_source("global_test", MockDataSource)

        # Should be available through list function
        sources = list_available_sources()
        assert "global_test" in sources

        # Should be available through get function
        source2 = get_source("global_test", config)
        assert isinstance(source2, MockDataSource)

        # Clear cache globally
        clear_source_cache()

        # Get source again - should work (may or may not be same instance)
        source3 = get_source("dlr", config)
        assert isinstance(source3, DLRBiomassSource)
