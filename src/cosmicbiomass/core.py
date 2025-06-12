"""Core API functions for biomass analysis."""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np

from .config import BiomassConfig, FootprintConfig
from .registry import get_source
from .processing import FootprintProcessor, StatisticsProcessor, BiomassStatistics, validate_footprint_coverage

logger = logging.getLogger(__name__)


def get_average_biomass(
    lat: float,
    lon: float,
    radius: float = 500.0,
    source: str = "dlr",
    dataset: str = "agbd_2021",
    data_dir: str = "data",
    footprint_shape: str = "circular",
    include_uncertainty: bool = True,
    outlier_method: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Get average biomass for a circular footprint around specified coordinates.
    
    Args:
        lat: Center latitude in WGS84 decimal degrees
        lon: Center longitude in WGS84 decimal degrees  
        radius: Footprint radius in meters (default: 500)
        source: Data source name (default: "dlr")
        dataset: Dataset identifier (default: "agbd_2021")
        data_dir: Directory containing biomass data files
        footprint_shape: Shape of footprint ("circular" or "gaussian")
        include_uncertainty: Whether to include uncertainty statistics
        outlier_method: Outlier detection method ("iqr", "zscore", or None)
        **kwargs: Additional configuration parameters
        
    Returns:
        Dictionary containing biomass statistics and metadata
    """
    logger.info(f"Computing average biomass at ({lat}, {lon}) with {radius}m radius")
    
    # Create configuration objects
    config = BiomassConfig(data_dir=data_dir, **kwargs)
    footprint_config = FootprintConfig(radius=radius, shape=footprint_shape)
    
    # Get data source
    data_source = get_source(source, config)
    
    # Compute bounding box for data loading (add buffer)
    # Rough conversion: 1 degree ≈ 111 km at equator
    buffer_deg = (radius * 2) / 111000  # Convert radius to degrees with buffer
    bbox = (lon - buffer_deg, lat - buffer_deg, lon + buffer_deg, lat + buffer_deg)
    
    logger.debug(f"Loading data with bbox: {bbox}")
    
    # Load biomass data
    try:
        biomass_data = data_source.load_data(dataset, bbox=bbox)
    except Exception as e:
        logger.error(f"Failed to load biomass data: {e}")
        raise
    
    # Initialize processors
    footprint_processor = FootprintProcessor(footprint_config)
    stats_processor = StatisticsProcessor(
        mask_invalid=True,
        outlier_method=outlier_method
    )
    
    # Compute footprint weights
    try:
        weights = footprint_processor.compute_footprint_weights(
            biomass_data, lat, lon
        )
    except Exception as e:
        logger.error(f"Failed to compute footprint weights: {e}")
        raise
    
    # Validate footprint coverage
    if not validate_footprint_coverage(weights, min_coverage=0.01):
        logger.warning("Low footprint coverage - results may be unreliable")
    
    # Determine variable names and check what's available
    logger.debug(f"Biomass data dimensions: {biomass_data.dims}")
    logger.debug(f"Biomass data coordinates: {list(biomass_data.coords.keys())}")
    
    if hasattr(biomass_data, 'data_vars'):
        logger.debug(f"Data variables: {list(biomass_data.data_vars.keys())}")
    
    if 'band' in biomass_data.dims:
        logger.debug(f"Available bands: {biomass_data.band.values}")
    
    primary_var = "agbd_cog"
    uncertainty_var = None
    
    # Check for uncertainty bands if requested
    if include_uncertainty:
        # Try different possible uncertainty variable names
        possible_uncertainty_vars = [
            "agbd_cog_uncertainty", 
            "uncertainty", 
            "std",
            "stderr"
        ]
        
        if 'band' in biomass_data.dims:
            available_bands = [str(b) for b in biomass_data.band.values]
            logger.info(f"Available bands: {available_bands}")
            
            for var in possible_uncertainty_vars:
                if var in available_bands:
                    uncertainty_var = var
                    logger.info(f"Found uncertainty variable: {var}")
                    break
            
            # Don't use non-uncertainty bands like 'overview' or 'thumbnail'
            if uncertainty_var is None:
                logger.warning("No proper uncertainty band found in STAC data. Uncertainty will be estimated from data spread.")
        
        if uncertainty_var is None:
            logger.info("No uncertainty variable found, will use data spread for uncertainty estimation")
    
    # Compute statistics
    try:
        stats = stats_processor.compute_weighted_statistics(
            biomass_data,
            weights,
            variable=primary_var,
            uncertainty_variable=uncertainty_var
        )
    except Exception as e:
        logger.error(f"Failed to compute statistics: {e}")
        raise
    
    # Get metadata
    metadata = data_source.get_metadata(dataset)
    
    # Prepare result
    result = {
        'biomass_statistics': stats.to_dict(),
        'location': {
            'latitude': lat,
            'longitude': lon,
            'radius_m': radius
        },
        'footprint': {
            'shape': footprint_shape,
            'total_weight': float(np.sum(weights)),
            'effective_pixels': int(np.sum(weights > 0.01 * np.max(weights)))
        },
        'data_info': {
            'source': source,
            'dataset': dataset,
            'units': metadata.get('dataset_info', {}).get('units', 'unknown'),
            'spatial_resolution': metadata.get('dataset_info', {}).get('spatial_resolution', 'unknown'),
            'temporal_coverage': metadata.get('dataset_info', {}).get('temporal_coverage', 'unknown')
        },
        'processing': {
            'outlier_method': outlier_method,
            'include_uncertainty': include_uncertainty,
            'bbox_used': bbox
        }
    }
    
    # Add summary for easy access
    if not np.isnan(stats.mean):
        result['summary'] = {
            'mean_biomass_Mg_ha': round(stats.mean, 2),
            'std_biomass_Mg_ha': round(stats.std, 2),
            'pixel_count': stats.count
        }
        
        # Include uncertainty - either from separate uncertainty band or estimated from std
        if stats.uncertainty_mean is not None:
            # Use uncertainty from separate uncertainty band if available
            result['summary']['uncertainty_Mg_ha'] = round(stats.uncertainty_mean, 2)
            result['summary']['uncertainty_source'] = 'uncertainty_band'
        elif include_uncertainty:
            # Use weighted standard deviation as uncertainty estimate
            result['summary']['uncertainty_Mg_ha'] = round(stats.std, 2)  
            result['summary']['uncertainty_source'] = 'data_spread'
    
    logger.info("Biomass analysis completed successfully")
    return result


def list_available_datasets(source: str = "dlr", data_dir: str = "data") -> Dict[str, Any]:
    """
    List available datasets for a data source.
    
    Args:
        source: Data source name
        data_dir: Directory containing data files
        
    Returns:
        Dictionary of available datasets with metadata
    """
    config = BiomassConfig(data_dir=data_dir)
    data_source = get_source(source, config)
    
    datasets = data_source.get_available_datasets()
    
    return {
        'source': source,
        'datasets': {k: v.dict() for k, v in datasets.items()}
    }


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude coordinates.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        
    Returns:
        True if coordinates are valid
    """
    if not (-90 <= lat <= 90):
        logger.error(f"Invalid latitude: {lat}. Must be between -90 and 90.")
        return False
    
    if not (-180 <= lon <= 180):
        logger.error(f"Invalid longitude: {lon}. Must be between -180 and 180.")
        return False
    
    return True
