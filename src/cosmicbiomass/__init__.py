"""
CosmicBiomass: A modern Python package for cosmic biomass analysis and modeling.

This package provides tools for extracting and analyzing biomass data from various sources,
with built-in support for footprint weighting and neutron correction calculations.
"""

import logging
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field
import numpy as np
import xarray as xr
from shapely.geometry import Point
import geopandas as gpd
from rasterio import features
from rasterio.transform import from_origin
from joblib import Parallel, delayed
import cubo
from abc import ABC, abstractmethod

# Package metadata
__version__ = "0.0.1"
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
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class CosmicBiomassConfig(BaseModel):
    """
    Pydantic configuration model for CosmicBiomass package settings.
    
    This provides validation and type safety for package configuration,
    following modern Python best practices.
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
        frozen=False,
    )
    
    # Default data source settings
    default_stac_url: str = Field(
        default="https://geoservice.dlr.de/eoc/ogc/stac/v1",
        description="Default STAC catalog URL for DLR data"
    )
    default_collection: str = Field(
        default="FOREST_STRUCTURE_DE_AGBD_P1Y",
        description="Default collection for biomass data"
    )
    default_start_date: str = Field(
        default="2017-01-01",
        description="Default start date for data queries"
    )
    default_end_date: str = Field(
        default="2023-12-31", 
        description="Default end date for data queries"
    )
    default_resolution: int = Field(
        default=10,
        ge=1,
        description="Default resolution in meters"
    )
    
    # Footprint calculation settings
    default_upsample_factor: int = Field(
        default=10,
        ge=1,
        description="Default upsampling factor for fractional coverage"
    )
    edge_size_buffer: float = Field(
        default=1.5,
        ge=1.0,
        description="Buffer multiplier for cube edge size relative to footprint radius"
    )
    
    # Parallel processing settings
    n_jobs: int = Field(
        default=-1,
        description="Number of parallel jobs (-1 for all CPUs)"
    )


# Global configuration instance
config = CosmicBiomassConfig()

# Global source registry instance (will be populated after class definitions)
source_registry = None

# Package exports - will be populated as we add functionality
__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "logger",
    "config",
    "CosmicBiomassConfig",
    "get_average_biomass",
]


@runtime_checkable
class BiomassDataSource(Protocol):
    """
    Protocol defining the interface for biomass data sources.
    
    This enables duck typing and makes it easy to add new data sources
    without modifying existing code. Any class implementing these methods
    can be used as a biomass data source.
    """
    
    def extract_cube(
        self,
        lat: float,
        lon: float,
        edge_size: int,
        **kwargs
    ) -> xr.Dataset:
        """
        Extract biomass data cube for given location and size.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            edge_size: Cube edge size in meters
            **kwargs: Source-specific parameters
            
        Returns:
            xr.Dataset: Biomass data cube
        """
        ...
    
    def get_source_info(self) -> dict[str, Any]:
        """
        Get metadata about the data source.
        
        Returns:
            dict: Source information including name, version, units, etc.
        """
        ...


class DLRBiomassSource:
    """
    DLR STAC-based biomass data source implementation.
    
    This class implements the BiomassDataSource protocol for accessing
    biomass data from the DLR STAC catalog using the cubo package.
    """
    
    def __init__(
        self,
        stac_url: str | None = None,
        collection: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        resolution: int | None = None,
    ):
        """
        Initialize DLR biomass data source.
        
        Args:
            stac_url: STAC catalog URL (uses config default if None)
            collection: Collection name (uses config default if None)
            start_date: Start date (uses config default if None)
            end_date: End date (uses config default if None)
            resolution: Resolution in meters (uses config default if None)
        """
        self.stac_url = stac_url or config.default_stac_url
        self.collection = collection or config.default_collection
        self.start_date = start_date or config.default_start_date
        self.end_date = end_date or config.default_end_date
        self.resolution = resolution or config.default_resolution
        
        logger.info("Initialized DLR source: collection=%s, resolution=%s", 
                   self.collection, self.resolution)
    
    def extract_cube(
        self,
        lat: float,
        lon: float,
        edge_size: int,
        **kwargs
    ) -> xr.Dataset:
        """
        Extract biomass data cube from DLR STAC catalog.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            edge_size: Cube edge size in meters
            **kwargs: Additional cubo parameters
            
        Returns:
            xr.Dataset: Biomass data cube from DLR
        """
        logger.info("Extracting DLR cube: lat=%s, lon=%s, edge_size=%s", 
                   lat, lon, edge_size)
        
        # Merge kwargs with instance defaults
        cube_params = {
            "lat": lat,
            "lon": lon,
            "stac": self.stac_url,
            "collection": self.collection,
            "gee": False,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "edge_size": edge_size,
            "units": "m",
            "resolution": self.resolution,
            # Remove bands filter to get all available bands
        } | kwargs  # Modern dict merge syntax
        
        try:
            biomass_cube = cubo.create(**cube_params)
            logger.info("Successfully created DLR cube with shape %s", 
                       biomass_cube.dims)
            
            # Debug: log cube details
            logger.info("Cube coordinates: %s", list(biomass_cube.coords.keys()))
            if hasattr(biomass_cube, 'data_vars'):
                logger.info("Cube data variables: %s", list(biomass_cube.data_vars.keys()))
            else:
                logger.info("Cube is a DataArray with name: %s", getattr(biomass_cube, 'name', 'unnamed'))
            if hasattr(biomass_cube, 'dims'):
                logger.info("Cube dimensions: %s", biomass_cube.dims)
            
            # Debug: log coordinate system and spatial extents
            if 'epsg' in biomass_cube.coords:
                logger.info("Data CRS (EPSG): %s", biomass_cube.coords['epsg'].values)
            if 'x' in biomass_cube.coords and 'y' in biomass_cube.coords:
                x_coords = biomass_cube.coords['x'].values
                y_coords = biomass_cube.coords['y'].values
                logger.info("X coordinate range: %s to %s", x_coords.min(), x_coords.max())
                logger.info("Y coordinate range: %s to %s", y_coords.min(), y_coords.max())
                logger.info("Input coordinates (EPSG:4326): lat=%s, lon=%s", lat, lon)
            
            return biomass_cube
            
        except Exception as e:
            logger.error("Failed to create DLR cube: %s", str(e))
            raise RuntimeError(f"DLR cube extraction failed: {e}") from e
    
    def get_source_info(self) -> dict[str, Any]:
        """
        Get metadata about the DLR data source.
        
        Returns:
            dict: DLR source information
        """
        return {
            "name": "DLR Forest Structure AGBD",
            "provider": "German Aerospace Center (DLR)",
            "stac_url": self.stac_url,
            "collection": self.collection,
            "temporal_range": f"{self.start_date} to {self.end_date}",
            "resolution_m": self.resolution,
            "units": "Mg/ha",  # Typical units for AGBD
            "description": "Above-ground biomass density from DLR Forest Structure dataset"
        }


class BiomassSourceRegistry:
    """
    Registry for managing different biomass data sources.
    
    This provides a clean way to register, discover, and instantiate
    different data sources while maintaining extensibility.
    """
    
    def __init__(self):
        """Initialize the source registry with built-in sources."""
        self._sources: dict[str, type] = {}
        self._instances: dict[str, BiomassDataSource] = {}
        
        # Register built-in sources
        self.register_source("dlr", DLRBiomassSource)
        logger.info("Initialized biomass source registry with %s sources", 
                   len(self._sources))
    
    def register_source(self, name: str, source_class: type):
        """
        Register a new biomass data source.
        
        Args:
            name: Unique identifier for the source
            source_class: Class implementing BiomassDataSource protocol
            
        Raises:
            ValueError: If source name already exists or class doesn't implement protocol
        """
        if name in self._sources:
            raise ValueError(f"Source '{name}' already registered")
        
        # Check if class implements the protocol (duck typing validation)
        if not hasattr(source_class, 'extract_cube') or not hasattr(source_class, 'get_source_info'):
            raise ValueError(f"Source class must implement BiomassDataSource protocol")
        
        self._sources[name] = source_class
        logger.info("Registered biomass source: %s", name)
    
    def get_source(self, name: str, **kwargs) -> BiomassDataSource:
        """
        Get or create an instance of a biomass data source.
        
        Args:
            name: Source identifier
            **kwargs: Parameters passed to source constructor
            
        Returns:
            BiomassDataSource: Source instance
            
        Raises:
            ValueError: If source name not found
        """
        if name not in self._sources:
            available = ", ".join(self._sources.keys())
            raise ValueError(f"Unknown source '{name}'. Available: {available}")
        
        # Create instance with provided parameters
        source_class = self._sources[name]
        return source_class(**kwargs)
    
    def list_sources(self) -> list[str]:
        """
        List all registered source names.
        
        Returns:
            list: Available source identifiers
        """
        return list(self._sources.keys())
    
    def get_source_info(self, name: str) -> dict[str, Any]:
        """
        Get information about a registered source.
        
        Args:
            name: Source identifier
            
        Returns:
            dict: Source metadata
        """
        source = self.get_source(name)
        return source.get_source_info()


# Initialize the global source registry after all classes are defined
source_registry = BiomassSourceRegistry()

# Update package exports to include all new functionality
__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "logger",
    "config",
    "CosmicBiomassConfig",
    "get_average_biomass",
    "BiomassDataSource",
    "DLRBiomassSource", 
    "BiomassSourceRegistry",
    "source_registry",
]


def get_average_biomass(
    lat: float, 
    lon: float, 
    footprint_radius: float,
    data_source: str = "dlr",
    **kwargs
) -> tuple[float, float]:
    """
    Extract and compute weighted average biomass for a given location and footprint.
    
    This is the main API function that handles the complete workflow:
    1. Creates a data cube around the location with sufficient buffer
    2. Generates footprint geometry and fractional coverage mask
    3. Computes weighted average biomass and uncertainty
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees  
        footprint_radius: Footprint radius in meters
        data_source: Data source identifier (default: "dlr")
        **kwargs: Additional parameters passed to data source
        
    Returns:
        tuple: (mean_biomass, biomass_uncertainty) in appropriate units
        
    Raises:
        ValueError: If coordinates are invalid or footprint radius <= 0
        RuntimeError: If data extraction or processing fails
        
    Author: LFT-W47
    """
    logger.info("Starting biomass extraction for lat=%s, lon=%s, radius=%s", 
                lat, lon, footprint_radius)
    
    # Input validation
    if not (-90 <= lat <= 90):
        raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
    if not (-180 <= lon <= 180):
        raise ValueError(f"Longitude must be between -180 and 180, got {lon}")
    if footprint_radius <= 0:
        raise ValueError(f"Footprint radius must be positive, got {footprint_radius}")
    
    try:
        # Extract biomass data cube with appropriate buffer
        biomass_cube = _extract_biomass_cube(lat, lon, footprint_radius, data_source, **kwargs)
        
        # Create footprint geometry and compute fractional coverage
        footprint_weights = _compute_footprint_weights(
            lat, lon, footprint_radius, biomass_cube
        )
        
        # Compute weighted statistics
        mean_biomass, biomass_uncertainty = _compute_weighted_stats(
            biomass_cube, footprint_weights
        )
        
        logger.info("Biomass extraction completed: mean=%s, uncertainty=%s", 
                   mean_biomass, biomass_uncertainty)
        
        return mean_biomass, biomass_uncertainty
        
    except Exception as e:
        logger.error("Failed to extract biomass data: %s", str(e))
        raise RuntimeError(f"Biomass extraction failed: {e}") from e


def _extract_biomass_cube(
    lat: float, 
    lon: float, 
    footprint_radius: float, 
    data_source: str,
    **kwargs
) -> xr.Dataset:
    """
    Extract biomass data cube with appropriate spatial buffer.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        footprint_radius: Footprint radius in meters
        data_source: Data source identifier
        **kwargs: Additional parameters for data source
        
    Returns:
        xr.Dataset: Biomass data cube
    """
    # Calculate required edge size with buffer
    edge_size = int(footprint_radius * 2 * config.edge_size_buffer)
    
    logger.info("Extracting data cube with edge_size=%s meters using source=%s", 
                edge_size, data_source)
    
    # Use the registry to get and use the appropriate data source
    try:
        source = source_registry.get_source(data_source, **kwargs)
        return source.extract_cube(lat, lon, edge_size)
    except Exception as e:
        logger.error("Failed to extract cube from source %s: %s", data_source, str(e))
        raise


def _extract_dlr_cube(
    lat: float, 
    lon: float, 
    edge_size: int,
    stac_url: str | None = None,
    collection: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    resolution: int | None = None,
) -> xr.Dataset:
    """
    Extract biomass data from DLR STAC catalog using cubo.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        edge_size: Cube edge size in meters
        stac_url: STAC catalog URL (uses config default if None)
        collection: Collection name (uses config default if None)
        start_date: Start date (uses config default if None)
        end_date: End date (uses config default if None)
        resolution: Resolution in meters (uses config default if None)
        
    Returns:
        xr.Dataset: Biomass data cube from DLR
    """
    # Use config defaults if parameters not provided
    stac_url = stac_url or config.default_stac_url
    collection = collection or config.default_collection
    start_date = start_date or config.default_start_date
    end_date = end_date or config.default_end_date
    resolution = resolution or config.default_resolution
    
    logger.info("Creating cubo cube from DLR STAC: collection=%s, resolution=%s", 
                collection, resolution)
    
    try:
        biomass_cube = cubo.create(
            lat=lat,
            lon=lon,
            stac=stac_url,
            collection=collection,
            gee=False,
            start_date=start_date,
            end_date=end_date,
            edge_size=edge_size,
            units="m",
            resolution=resolution,
        )
        
        logger.info("Successfully created biomass cube with shape %s", 
                   biomass_cube.dims)
        return biomass_cube
        
    except Exception as e:
        logger.error("Failed to create cubo cube: %s", str(e))
        raise


def _compute_footprint_weights(
    lat: float, 
    lon: float, 
    footprint_radius: float, 
    biomass_cube: xr.Dataset
) -> np.ndarray:
    """
    Compute fractional coverage weights for the footprint.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        footprint_radius: Footprint radius in meters
        biomass_cube: Biomass data cube
        
    Returns:
        np.ndarray: 2D fractional coverage mask [0, 1]
    """
    logger.info("Computing footprint weights for radius=%s meters", footprint_radius)
    
    # Get raster coordinates from cube
    # Handle both Dataset and DataArray objects
    if hasattr(biomass_cube, 'data_vars'):
        # It's a Dataset - get the first data variable
        data_vars = list(biomass_cube.data_vars)
        if not data_vars:
            raise ValueError("No data variables found in biomass cube")
        main_var = biomass_cube[data_vars[0]]
    else:
        # It's a DataArray - use it directly
        main_var = biomass_cube
    
    raster_x = main_var.x.values
    raster_y = main_var.y.values
    
    # Get the CRS of the data cube
    data_crs = None
    if 'epsg' in biomass_cube.coords:
        epsg_code = int(biomass_cube.coords['epsg'].values)
        data_crs = f"EPSG:{epsg_code}"
        logger.info("Data CRS detected: %s", data_crs)
    else:
        # Try to infer CRS from coordinate ranges
        if np.all(np.abs(raster_x) > 180) or np.all(np.abs(raster_y) > 90):
            logger.warning("No CRS information found, but coordinates suggest projected system")
            # For this specific DLR dataset, we know it's UTM Zone 32N
            data_crs = "EPSG:32632"
            logger.info("Assuming UTM Zone 32N (EPSG:32632) for DLR data")
        else:
            logger.warning("Assuming geographic coordinates (EPSG:4326)")
            data_crs = "EPSG:4326"
    
    # Transform input coordinates to match data CRS if needed
    if data_crs != "EPSG:4326":
        from pyproj import Transformer
        # Create transformer from WGS84 (EPSG:4326) to data CRS
        transformer = Transformer.from_crs("EPSG:4326", data_crs, always_xy=True)
        transformed_x, transformed_y = transformer.transform(lon, lat)
        logger.info("Transformed coordinates: (%s, %s) -> (%s, %s)", 
                   lon, lat, transformed_x, transformed_y)
    else:
        # No transformation needed
        transformed_x, transformed_y = lon, lat
        logger.info("Using original coordinates: (%s, %s)", lon, lat)
    
    # Create point geometry and buffer in the correct CRS
    point = Point(transformed_x, transformed_y)
    footprint_geom = point.buffer(footprint_radius)
    
    # Debug: log geometry and raster info
    logger.info("Footprint geometry bounds: %s", footprint_geom.bounds)
    logger.info("Raster X range: [%s, %s], resolution: %s", 
                raster_x.min(), raster_x.max(), raster_x[1] - raster_x[0])
    logger.info("Raster Y range: [%s, %s], resolution: %s", 
                raster_y.min(), raster_y.max(), raster_y[1] - raster_y[0])
    
    # Compute fractional coverage mask
    weights = _compute_fractional_coverage_mask(
        footprint_geom, 
        raster_x, 
        raster_y, 
        upsample=config.default_upsample_factor
    )
    
    logger.info("Computed footprint weights with coverage area=%s pixels", 
                np.sum(weights > 0))
    
    return weights


def _compute_weighted_stats(
    biomass_cube: xr.Dataset, 
    weights: np.ndarray
) -> tuple[float, float]:
    """
    Compute weighted statistics from biomass data and footprint weights.
    
    Args:
        biomass_cube: Biomass data cube
        weights: 2D fractional coverage weights
        
    Returns:
        tuple: (weighted_mean, weighted_uncertainty)
    """
    logger.info("Computing weighted biomass statistics")
    
    # Get the main biomass variable
    # Handle both Dataset and DataArray objects
    if hasattr(biomass_cube, 'data_vars'):
        # It's a Dataset - get the first data variable
        data_vars = list(biomass_cube.data_vars)
        if not data_vars:
            raise ValueError("No data variables found in biomass cube")
        main_var = biomass_cube[data_vars[0]]
        
        # If it has a band dimension, select the AGBD band specifically
        if 'band' in main_var.dims:
            logger.info("Available bands: %s", list(main_var.band.values))
            logger.info("Band dtype: %s", main_var.band.dtype)
            try:
                main_var = main_var.sel(band="agbd_cog")
                logger.info("Selected agbd_cog band from data cube")
            except (KeyError, ValueError):
                # Fallback to first band if agbd_cog not found or wrong type
                available_bands = list(main_var.band.values)
                logger.warning("agbd_cog band selection failed, available bands: %s", available_bands)
                main_var = main_var.isel(band=0)
                logger.info("Using first available band: %s", main_var.band.values)
    else:
        # It's a DataArray - use it directly
        main_var = biomass_cube
        
        # If it has a band dimension, select the AGBD band specifically  
        if 'band' in main_var.dims:
            logger.info("Available bands: %s", list(main_var.band.values))
            logger.info("Band dtype: %s", main_var.band.dtype)
            try:
                main_var = main_var.sel(band="agbd_cog")
                logger.info("Selected agbd_cog band from data array")
            except (KeyError, ValueError):
                # Fallback to first band if agbd_cog not found or wrong type
                available_bands = list(main_var.band.values)
                logger.warning("agbd_cog band selection failed, available bands: %s", available_bands)
                main_var = main_var.isel(band=0)
                logger.info("Using first available band: %s", main_var.band.values)
    
    # Handle temporal dimension if present
    if 'time' in main_var.dims:
        # Use the most recent time slice or compute temporal mean
        biomass_data = main_var.isel(time=-1).values
    else:
        biomass_data = main_var.values
    
    # Ensure 2D data
    if biomass_data.ndim > 2:
        biomass_data = biomass_data.squeeze()
    
    # Create mask for valid data
    valid_mask = ~np.isnan(biomass_data) & (weights > 0)
    
    if not np.any(valid_mask):
        logger.warning("No valid biomass data within footprint")
        return np.nan, np.nan
    
    # Extract valid data and weights
    valid_biomass = biomass_data[valid_mask]
    valid_weights = weights[valid_mask]
    
    # Compute weighted statistics
    weighted_mean = np.average(valid_biomass, weights=valid_weights)
    
    # Estimate uncertainty as weighted standard deviation
    weighted_var = np.average(
        (valid_biomass - weighted_mean) ** 2, 
        weights=valid_weights
    )
    weighted_uncertainty = np.sqrt(weighted_var)
    
    logger.info("Weighted stats: mean=%s, uncertainty=%s, n_pixels=%s", 
                weighted_mean, weighted_uncertainty, len(valid_biomass))
    
    return float(weighted_mean), float(weighted_uncertainty)


def _compute_fractional_coverage_mask(
    buffer_geom, 
    raster_x: np.ndarray, 
    raster_y: np.ndarray, 
    upsample: int = 10
) -> np.ndarray:
    """
    Compute a fractional coverage mask for a single buffer geometry.
    
    This function uses upsampling to achieve sub-pixel accuracy for fractional
    coverage computation, following the pattern from your rasterio example.
    
    Args:
        buffer_geom: Shapely geometry (buffer polygon)
        raster_x: 1D array of x coordinates (pixel centers)
        raster_y: 1D array of y coordinates (pixel centers) 
        upsample: Upsampling factor for sub-pixel accuracy (default 10)
        
    Returns:
        np.ndarray: 2D mask with values in [0,1] representing fraction of 
                   pixel covered by buffer geometry
                   
    Author: LFT-W47
    """
    logger.debug("Computing fractional coverage with upsample=%s", upsample)
    logger.debug("Buffer geometry bounds: %s", buffer_geom.bounds)
    logger.debug("Raster X: min=%s, max=%s, count=%s", raster_x.min(), raster_x.max(), len(raster_x))
    logger.debug("Raster Y: min=%s, max=%s, count=%s", raster_y.min(), raster_y.max(), len(raster_y))
    
    # Get raster grid parameters
    xres = float(raster_x[1] - raster_x[0])
    yres = float(raster_y[1] - raster_y[0])
    width = len(raster_x)
    height = len(raster_y)
    
    logger.debug("Grid resolution: xres=%s, yres=%s", xres, yres)
    logger.debug("Grid dimensions: width=%s, height=%s", width, height)
    
    # Handle negative Y resolution (common in GIS data)
    if yres < 0:
        # Y coordinates are in descending order (top to bottom)
        y_origin = float(raster_y.max())
        yres = abs(yres)
        logger.debug("Detected descending Y coordinates, using y_origin=%s, abs(yres)=%s", y_origin, yres)
    else:
        # Y coordinates are in ascending order (bottom to top)
        y_origin = float(raster_y.max())
        logger.debug("Detected ascending Y coordinates, using y_origin=%s", y_origin)
    
    # Create transform for rasterization
    transform = from_origin(
        float(raster_x.min()), 
        y_origin, 
        xres, 
        yres
    )
    
    logger.debug("Transform: %s", transform)
    
    # Calculate upsampled grid parameters
    up_width = width * upsample
    up_height = height * upsample
    up_xres = xres / upsample
    up_yres = yres / upsample
    up_transform = from_origin(
        float(raster_x.min()), 
        y_origin, 
        up_xres, 
        up_yres
    )
    
    logger.debug("Upsampled grid: %sx%s pixels (original: %sx%s)", 
                up_width, up_height, width, height)
    logger.debug("Upsampled transform: %s", up_transform)
    
    try:
        # Rasterize at high resolution (1 = inside, 0 = outside)
        up_mask = features.rasterize(
            [(buffer_geom, 1)],
            out_shape=(up_height, up_width),
            transform=up_transform,
            fill=0,
            all_touched=False,
            dtype="float32"
        )
        
        logger.debug("Upsampled mask created with %s pixels inside geometry", 
                    np.sum(up_mask))
        
        if np.sum(up_mask) == 0:
            logger.warning("No pixels found inside geometry - checking overlap")
            logger.warning("Geometry bounds: %s", buffer_geom.bounds)
            logger.warning("Raster bounds: x=[%s, %s], y=[%s, %s]", 
                          raster_x.min(), raster_x.max(), raster_y.min(), raster_y.max())
        
        # Downsample by averaging blocks to get fractional coverage per original pixel
        mask = up_mask.reshape(height, upsample, width, upsample).mean(axis=(1, 3))
        
        logger.debug("Downsampled mask has %s pixels with partial coverage", 
                    np.sum((mask > 0) & (mask < 1)))
        
        return mask
        
    except Exception as e:
        logger.error("Failed to compute fractional coverage: %s", str(e))
        logger.error("Grid params: width=%s, height=%s, upsample=%s", 
                    width, height, upsample)
        raise RuntimeError(f"Fractional coverage computation failed: {e}") from e