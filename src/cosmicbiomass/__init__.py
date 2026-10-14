"""
CosmicBiomass: A modern Python package for cosmic biomass analysis and modeling.

This package provides tools for extracting and analyzing biomass data from various sources,
with built-in support for footprint weighting and neutron correction calculations.
"""

import logging
import warnings

# Import main API functions
from .config import BiomassConfig, FootprintConfig
from .core import (
    get_average_biomass,
    get_average_biomass_timeseries,
    get_seasonal_biomass_timeseries,
    list_available_datasets,
    validate_coordinates,
)
from .processing import BiomassStatistics, FootprintProcessor, StatisticsProcessor
from .registry import list_available_sources, register_source
from .sources import BiomassDataSource, DLRBiomassSource

#: Shown once per session on import. A FutureWarning rather than a
#: DeprecationWarning: the audience is scientists running scripts and notebooks,
#: and a DeprecationWarning raised during import is attributed to the import
#: machinery, so Python's default filters would hide it from exactly them.
DEPRECATION_MESSAGE = (
    "cosmicbiomass is deprecated and no longer maintained; 0.2.4 is its final "
    "release. Its functionality continues in neptoon's remote-sensing module "
    '(pip install "neptoon[geo]"), which serves footprint-weighted biomass from '
    "the DLR (Germany, 10 m) and ESA CCI (global, 100 m) maps with coverage "
    "checks and provenance. Note that neptoon reports biomass in kg/m2, not "
    "Mg/ha (1 kg/m2 = 10 Mg/ha). Migration: "
    "https://codebase.helmholtz.cloud/louis-ferdinand.trinkle/cosmicbiomass#deprecated"
)
warnings.warn(DEPRECATION_MESSAGE, FutureWarning, stacklevel=2)

# Package metadata
__version__ = "0.2.4"
__author__ = "LFT-W47"
__email__ = "louis.trinkle@gmail.com"

# Configure package-wide logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler if none exists
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Modern logging format with timestamp and level
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Public API
__all__ = [
    # Main functions
    "get_average_biomass",
    "get_average_biomass_timeseries",
    "get_seasonal_biomass_timeseries",
    "list_available_datasets",
    "validate_coordinates",
    "list_available_sources",
    # Configuration
    "BiomassConfig",
    "FootprintConfig",
    # Extension points
    "register_source",
    "BiomassDataSource",
    "DLRBiomassSource",
    # Processing classes
    "BiomassStatistics",
    "FootprintProcessor",
    "StatisticsProcessor",
    # Legacy compatibility (deprecated)
    "CosmicBiomassConfig",
]


# Legacy compatibility - deprecated, use BiomassConfig instead
class CosmicBiomassConfig(BiomassConfig):
    """
    Legacy configuration class - DEPRECATED.

    Please use BiomassConfig instead for new code.
    This class is maintained for backward compatibility only.
    """

    def __init__(self, **kwargs):
        warnings.warn(
            "CosmicBiomassConfig is deprecated. Use BiomassConfig instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**kwargs)
