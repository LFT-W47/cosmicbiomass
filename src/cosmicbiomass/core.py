"""Core API functions for biomass analysis."""

import logging
import re
from datetime import date, datetime
from typing import Any

import numpy as np

from .config import BiomassConfig, FootprintConfig
from .processing import (
    FootprintProcessor,
    StatisticsProcessor,
    validate_footprint_coverage,
)
from .registry import get_source

logger = logging.getLogger(__name__)


def get_average_biomass(
    lat: float,
    lon: float,
    radius: float = 200.0,
    source: str = "dlr",
    dataset: str = "agbd_2021",
    data_dir: str = "data",
    footprint_shape: str = "crns",
    include_uncertainty: bool = True,
    outlier_method: str | None = None,
    **kwargs
) -> dict[str, Any]:
    """
    Get average biomass for a footprint around specified coordinates.

    Args:
        lat: Center latitude in WGS84 decimal degrees
        lon: Center longitude in WGS84 decimal degrees
        radius: Footprint radius in meters (default: 200m)
        source: Data source name (default: "dlr")
        dataset: Dataset identifier (default: "agbd_2021")
        data_dir: Directory containing biomass data files
        footprint_shape: Shape of footprint ("crns", "circular" or "gaussian")
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


def _coerce_year(value: int | str | date | datetime) -> int:
    """Coerce a year from int, ISO date strings, or datetime/date objects."""
    if isinstance(value, int):
        return value
    if isinstance(value, datetime | date):
        return value.year
    if isinstance(value, str):
        match = re.search(r"(\d{4})", value)
        if match:
            return int(match.group(1))
    raise ValueError(f"Unsupported date/year value: {value!r}")


def _build_dataset_id(dataset: str, year: int, multiple_years: bool) -> str:
    """Build a dataset id for a given year."""
    if "{year}" in dataset:
        return dataset.format(year=year)
    if re.search(r"\d{4}", dataset):
        if multiple_years:
            raise ValueError(
                "Dataset includes a fixed year. Use a template like 'agbd_{year}' for ranges."
            )
        return dataset
    return f"{dataset}_{year}"


def get_average_biomass_timeseries(
    lat: float,
    lon: float,
    radius: float = 200.0,
    source: str = "dlr",
    dataset: str = "agbd_{year}",
    start_time: int | str | date | datetime = 2021,
    end_time: int | str | date | datetime = 2021,
    data_dir: str = "data",
    footprint_shape: str = "crns",
    include_uncertainty: bool = True,
    outlier_method: str | None = None,
    **kwargs
) -> list[dict[str, Any]]:
    """
    Get a multi-year time series of average biomass for a footprint.

    Args:
        lat: Center latitude in WGS84 decimal degrees
        lon: Center longitude in WGS84 decimal degrees
        radius: Footprint radius in meters (default: 200m)
        source: Data source name (default: "dlr")
        dataset: Dataset template (default: "agbd_{year}")
        start_time: Start year/date (int or date string)
        end_time: End year/date (int or date string)
        data_dir: Directory containing biomass data files
        footprint_shape: Shape of footprint ("crns", "circular" or "gaussian")
        include_uncertainty: Whether to include uncertainty statistics
        outlier_method: Outlier detection method ("iqr", "zscore", or None)
        **kwargs: Additional configuration parameters

    Returns:
        Ordered list of dicts with keys: year, dataset, result.
    """
    start_year = _coerce_year(start_time)
    end_year = _coerce_year(end_time)
    if start_year > end_year:
        raise ValueError("start_time must be <= end_time")

    years = range(start_year, end_year + 1)
    multiple_years = start_year != end_year
    series: list[dict[str, Any]] = []

    for year in years:
        dataset_id = _build_dataset_id(dataset, year, multiple_years)
        result = get_average_biomass(
            lat=lat,
            lon=lon,
            radius=radius,
            source=source,
            dataset=dataset_id,
            data_dir=data_dir,
            footprint_shape=footprint_shape,
            include_uncertainty=include_uncertainty,
            outlier_method=outlier_method,
            **kwargs,
        )
        series.append({"year": year, "dataset": dataset_id, "result": result})

    return series


def list_available_datasets(source: str = "dlr", data_dir: str = "data") -> dict[str, Any]:
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
