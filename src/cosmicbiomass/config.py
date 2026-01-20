"""
Configuration models for CosmicBiomass package.

This module contains Pydantic models for package configuration,
providing validation and type safety following modern Python best practices.
"""

import logging

from pydantic import BaseModel, ConfigDict, Field

# Configure logging for this module
logger = logging.getLogger(__name__)


class BiomassConfig(BaseModel):
    """
    Configuration model for biomass data sources and processing settings.

    This provides validation and type safety for package configuration,
    following modern Python best practices.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
        frozen=False,
    )

    # Data directory settings
    data_dir: str = Field(
        default="data",
        description="Directory containing biomass data files"
    )

    # Processing settings
    n_jobs: int = Field(
        default=-1,
        description="Number of parallel jobs (-1 for all CPUs)"
    )


class FootprintConfig(BaseModel):
    """
    Configuration for footprint analysis parameters.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
    )

    radius: float = Field(
        gt=0,
        description="Footprint radius in meters"
    )

    shape: str = Field(
        default="crns",
        description="Footprint shape ('circular', 'gaussian', or 'crns')"
    )

    def __init__(self, **kwargs):
        if 'shape' in kwargs and kwargs['shape'] not in ['circular', 'gaussian', 'crns']:
            raise ValueError("Footprint shape must be 'circular', 'gaussian', or 'crns'")
        super().__init__(**kwargs)


# Legacy compatibility
CosmicBiomassConfig = BiomassConfig
