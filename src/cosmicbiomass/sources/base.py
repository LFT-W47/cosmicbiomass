"""Base classes for biomass data sources."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import xarray as xr
from pydantic import BaseModel

from ..config import BiomassConfig


class BiomassDataSource(ABC):
    """Abstract base class for biomass data sources."""
    
    def __init__(self, config: BiomassConfig):
        self.config = config
    
    @abstractmethod
    def get_available_datasets(self) -> Dict[str, Any]:
        """Get information about available datasets."""
        pass
    
    @abstractmethod
    def load_data(self, dataset_id: str, bbox: Optional[Tuple[float, float, float, float]] = None) -> xr.Dataset:
        """Load biomass data for the specified dataset and bounding box."""
        pass
    
    @abstractmethod
    def get_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """Get metadata for a specific dataset."""
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source."""
        pass


class DatasetInfo(BaseModel):
    """Information about a biomass dataset."""
    id: str
    name: str
    description: str
    spatial_resolution: float
    temporal_coverage: str
    units: str
    uncertainty_available: bool = False
    crs: str = "EPSG:4326"
