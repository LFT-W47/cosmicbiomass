"""Footprint analysis and weighting functions."""

import logging

import numpy as np
import xarray as xr
from pyproj import Transformer

from ..config import FootprintConfig

logger = logging.getLogger(__name__)


class FootprintProcessor:
    """Handles footprint-based analysis of biomass data."""

    def __init__(self, config: FootprintConfig):
        self.config = config

    def compute_footprint_weights(
        self,
        data: xr.Dataset,
        center_lat: float,
        center_lon: float
    ) -> np.ndarray:
        """
        Compute footprint weights for biomass data.

        Args:
            data: Biomass dataset with spatial coordinates
            center_lat: Center latitude in WGS84
            center_lon: Center longitude in WGS84

        Returns:
            Array of weights matching data spatial dimensions
        """
        logger.info(f"Computing {self.config.shape} footprint weights for center ({center_lat}, {center_lon})")
        logger.info(f"Footprint parameters: radius={self.config.radius}m")

        # Get coordinate arrays
        if 'x' in data.coords and 'y' in data.coords:
            x_coords = data.x.values
            y_coords = data.y.values
        elif 'lon' in data.coords and 'lat' in data.coords:
            x_coords = data.lon.values
            y_coords = data.lat.values
        else:
            raise ValueError("Dataset must have either (x,y) or (lon,lat) coordinates")

        # Detect data CRS
        data_crs = getattr(data, 'rio', None)
        if data_crs is not None and hasattr(data_crs, 'crs') and data_crs.crs:
            data_crs_str = str(data_crs.crs)
            logger.debug(f"Detected data CRS: {data_crs_str}")
        else:
            # Assume projected coordinates if x/y, geographic if lon/lat
            if 'x' in data.coords:
                data_crs_str = "EPSG:32632"  # Default to UTM 32N for DLR data
            else:
                data_crs_str = "EPSG:4326"
            logger.debug(f"Assuming data CRS: {data_crs_str}")

        # Transform center coordinates to data CRS if needed
        if data_crs_str != "EPSG:4326":
            transformer = Transformer.from_crs("EPSG:4326", data_crs_str, always_xy=True)
            center_x, center_y = transformer.transform(center_lon, center_lat)
            logger.debug(f"Transformed center: ({center_x:.2f}, {center_y:.2f}) in {data_crs_str}")
        else:
            center_x, center_y = center_lon, center_lat

        # Create coordinate grids
        X, Y = np.meshgrid(x_coords, y_coords)

        # Calculate distances from center
        distances = np.sqrt((X - center_x)**2 + (Y - center_y)**2)

        # Compute weights based on footprint shape
        if self.config.shape == "circular":
            weights = self._circular_footprint(distances)
        elif self.config.shape == "gaussian":
            weights = self._gaussian_footprint(distances)
        elif self.config.shape == "crns":
            weights = self._crns_footprint(distances)
        else:
            raise ValueError(f"Unsupported footprint shape: {self.config.shape}")

        # Log footprint statistics
        total_weight = np.sum(weights)
        effective_pixels = np.sum(weights > 0.01 * np.max(weights))  # Pixels with >1% max weight

        logger.info(f"Footprint computed: {effective_pixels} effective pixels, total weight: {total_weight:.2f}")

        return weights

    def _circular_footprint(self, distances: np.ndarray) -> np.ndarray:
        """Compute circular footprint weights."""
        weights = np.zeros_like(distances)
        mask = distances <= self.config.radius
        weights[mask] = 1.0
        return weights

    def _gaussian_footprint(self, distances: np.ndarray) -> np.ndarray:
        """Compute Gaussian footprint weights."""
        # Use radius as 2*sigma (covers ~95% of distribution)
        sigma = self.config.radius / 2.0
        weights = np.exp(-0.5 * (distances / sigma)**2)

        # Optionally apply cutoff at radius
        if hasattr(self.config, 'apply_cutoff') and self.config.apply_cutoff:
            weights[distances > self.config.radius] = 0.0

        return weights

    def _crns_footprint(self, distances: np.ndarray) -> np.ndarray:
        """
        Compute CRNS footprint weights using Schrön et al. (2017) formula.

        W(r) = 30*exp(−r/1.6) + exp(−r/100)
        Final weight = W(r)/r for r > 1, W(r) for r ≤ 1

        Reference: Schrön et al. (2017), applied in Fersch et al. (2018)
        """
        # Schrön et al. (2017) weighting function
        w_r = 30 * np.exp(-distances / 1.6) + np.exp(-distances / 100)

        # Apply distance normalization: W(r)/r for r > 1
        # For r ≤ 1, use r = 1 to avoid division by zero
        r_normalized = np.maximum(distances, 1.0)
        weights = w_r / r_normalized

        # Apply radius cutoff if specified
        if self.config.radius > 0:
            weights[distances > self.config.radius] = 0.0

        logger.debug(f"CRNS weights - max: {np.max(weights):.4f}, "
                    f"mean: {np.mean(weights[weights > 0]):.4f}")

        return weights


def validate_footprint_coverage(weights: np.ndarray, min_coverage: float = 0.1) -> bool:
    """
    Validate that footprint has sufficient coverage of the data.

    Args:
        weights: Footprint weight array
        min_coverage: Minimum fraction of footprint that should have data

    Returns:
        True if coverage is sufficient
    """
    if weights.size == 0:
        return False

    # Check fraction of non-zero weights
    coverage = np.sum(weights > 0) / weights.size

    logger.debug(f"Footprint coverage: {coverage:.3f} (minimum: {min_coverage})")

    return coverage >= min_coverage
