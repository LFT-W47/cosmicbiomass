"""Registry for managing biomass data sources."""

import logging

from .config import BiomassConfig
from .sources.base import BiomassDataSource
from .sources.dlr import DLRBiomassSource

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Registry for managing available biomass data sources."""

    def __init__(self):
        self._sources: dict[str, type[BiomassDataSource]] = {}
        self._instances: dict[str, BiomassDataSource] = {}

        # Register built-in sources
        self.register_source("dlr", DLRBiomassSource)

    def register_source(self, name: str, source_class: type[BiomassDataSource]):
        """Register a new data source class."""
        if not issubclass(source_class, BiomassDataSource):
            raise ValueError("Source class must inherit from BiomassDataSource")

        self._sources[name.lower()] = source_class
        logger.debug(f"Registered data source: {name}")

    def get_source(self, name: str, config: BiomassConfig) -> BiomassDataSource:
        """Get an instance of a data source."""
        name_lower = name.lower()

        if name_lower not in self._sources:
            available = list(self._sources.keys())
            raise ValueError(f"Unknown data source: {name}. Available: {available}")

        # Return cached instance if available and config matches
        if name_lower in self._instances:
            instance = self._instances[name_lower]
            if instance.config == config:
                return instance

        # Create new instance
        source_class = self._sources[name_lower]
        instance = source_class(config)
        self._instances[name_lower] = instance

        logger.debug(f"Created data source instance: {name}")
        return instance

    def list_sources(self) -> list[str]:
        """List all registered data source names."""
        return list(self._sources.keys())

    def clear_cache(self):
        """Clear cached source instances."""
        self._instances.clear()
        logger.debug("Cleared source instance cache")


# Global registry instance
_global_registry = SourceRegistry()


def get_source(name: str, config: BiomassConfig) -> BiomassDataSource:
    """Get a data source instance from the global registry."""
    return _global_registry.get_source(name, config)


def register_source(name: str, source_class: type[BiomassDataSource]):
    """Register a new data source in the global registry."""
    _global_registry.register_source(name, source_class)


def list_available_sources() -> list[str]:
    """List all available data sources."""
    return _global_registry.list_sources()


def clear_source_cache():
    """Clear the source instance cache."""
    _global_registry.clear_cache()
