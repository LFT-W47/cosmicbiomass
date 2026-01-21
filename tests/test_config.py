"""
Unit tests for the config module.

Tests the Pydantic-based configuration classes used throughout the package.
"""

import pytest
from pydantic import ValidationError

from cosmicbiomass.config import BiomassConfig, FootprintConfig


class TestBiomassConfig:
    """Test the BiomassConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BiomassConfig()

        assert config.data_dir == "data"
        assert config.n_jobs == -1

    def test_custom_config(self):
        """Test configuration with custom values."""
        config = BiomassConfig(
            data_dir="/custom/path",
            n_jobs=4
        )

        assert config.data_dir == "/custom/path"
        assert config.n_jobs == 4

    def test_config_validation(self):
        """Test configuration validation."""
        # Test valid configs
        config = BiomassConfig(data_dir="test", n_jobs=1)
        assert config.data_dir == "test"
        assert config.n_jobs == 1

        # Currently BiomassConfig doesn't have strict validation rules
        # but we can test basic functionality
        config = BiomassConfig(n_jobs=0)
        assert config.n_jobs == 0

    def test_config_equality(self):
        """Test configuration equality comparison."""
        config1 = BiomassConfig(data_dir="test", n_jobs=4)
        config2 = BiomassConfig(data_dir="test", n_jobs=4)
        config3 = BiomassConfig(data_dir="different", n_jobs=4)

        assert config1 == config2
        assert config1 != config3


class TestFootprintConfig:
    """Test the FootprintConfig class."""

    def test_default_footprint_config(self):
        """Test default footprint configuration with required radius."""
        config = FootprintConfig(radius=500.0)

        assert config.radius == 500.0
        assert config.shape == "crns"

    def test_custom_footprint_config(self):
        """Test custom footprint configuration."""
        config = FootprintConfig(
            radius=240.0,
            shape="gaussian"
        )

        assert config.radius == 240.0
        assert config.shape == "gaussian"

    def test_footprint_validation(self):
        """Test footprint configuration validation."""
        # Test invalid shape - this should raise ValueError from __init__
        with pytest.raises(ValueError, match="Footprint shape must be"):
            FootprintConfig(radius=100.0, shape="invalid_shape")

        # Test negative radius - this should raise ValidationError from Pydantic
        with pytest.raises(ValidationError):
            FootprintConfig(radius=-100)

        # Test zero radius - this should raise ValidationError from Pydantic
        with pytest.raises(ValidationError):
            FootprintConfig(radius=0)

    def test_radius_constraints(self):
        """Test radius constraint validation."""
        # Test minimum valid radius
        config = FootprintConfig(radius=1.0)
        assert config.radius == 1.0

        # Test large radius
        config = FootprintConfig(radius=10000.0)
        assert config.radius == 10000.0
