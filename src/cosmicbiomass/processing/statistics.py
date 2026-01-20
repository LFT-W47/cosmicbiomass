"""Statistical analysis functions for biomass data."""

import logging
from typing import Any

import numpy as np
import xarray as xr
from pydantic import BaseModel
from scipy import stats

logger = logging.getLogger(__name__)


class BiomassStatistics(BaseModel):
    """Container for biomass statistics results."""
    mean: float
    std: float
    median: float
    min: float
    max: float
    count: int
    uncertainty_mean: float | None = None
    uncertainty_std: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return self.dict(exclude_none=True)


class StatisticsProcessor:
    """Handles statistical analysis of biomass data."""

    def __init__(self, mask_invalid: bool = True, outlier_method: str | None = None):
        """
        Initialize statistics processor.

        Args:
            mask_invalid: Whether to mask invalid/NaN values
            outlier_method: Method for outlier detection ('iqr', 'zscore', or None)
        """
        self.mask_invalid = mask_invalid
        self.outlier_method = outlier_method

    def compute_weighted_statistics(
        self,
        data: xr.Dataset,
        weights: np.ndarray,
        variable: str = "agbd_cog",
        uncertainty_variable: str | None = None
    ) -> BiomassStatistics:
        """
        Compute weighted statistics for biomass data.

        Args:
            data: Biomass dataset
            weights: Weight array matching data spatial dimensions
            variable: Primary variable name for analysis
            uncertainty_variable: Uncertainty variable name (optional)

        Returns:
            BiomassStatistics object with computed statistics
        """
        logger.info(f"Computing weighted statistics for variable: {variable}")

        # Handle both Dataset and DataArray inputs
        if hasattr(data, 'data_vars'):
            # It's a Dataset
            if variable not in data.data_vars:
                # Try to find the variable in a multi-band structure
                if 'variable' in data.dims:
                    try:
                        data_array = data.sel(variable=variable)
                    except KeyError as e:
                        available_vars = list(data.coords.get('variable', data.data_vars.keys()))
                        raise ValueError(
                            f"Variable '{variable}' not found. Available: {available_vars}"
                        ) from e
                else:
                    raise ValueError(f"Variable '{variable}' not found in dataset")
            else:
                data_array = data[variable]
        else:
            # It's a DataArray - handle band selection
            data_array = data
            if 'band' in data_array.dims:
                logger.info(f"Available bands: {list(data_array.band.values)}")
                try:
                    # Try to select the agbd_cog band specifically
                    data_array = data_array.sel(band="agbd_cog")
                    logger.info("Selected agbd_cog band from data array")
                except (KeyError, ValueError):
                    # Fallback to first band if agbd_cog not found
                    available_bands = list(data_array.band.values)
                    logger.warning(f"agbd_cog band selection failed, available bands: {available_bands}")
                    data_array = data_array.isel(band=0)
                    logger.info(f"Using first available band: {data_array.band.values}")

            # If DataArray has a name and it doesn't match, log a warning
            if hasattr(data_array, 'name') and data_array.name and data_array.name != variable:
                logger.debug(f"Requested variable '{variable}' but DataArray has name '{data_array.name}'")

        # Handle temporal dimension if present
        if 'time' in data_array.dims:
            # Use the most recent time slice
            data_array = data_array.isel(time=-1)

        # Ensure weights match data dimensions
        if weights.shape != data_array.shape[-2:]:  # Last two dims should be spatial
            raise ValueError(f"Weight shape {weights.shape} doesn't match data spatial shape {data_array.shape[-2:]}")

        # Flatten arrays for easier processing
        if data_array.ndim > 2:
            # Handle multi-dimensional data (e.g., with band/variable dimension)
            data_flat = data_array.values.flatten() if hasattr(data_array, 'values') else data_array.flatten()
        else:
            data_flat = data_array.values.flatten()

        weights_flat = weights.flatten()

        # Apply masking
        valid_mask = self._create_valid_mask(data_flat, weights_flat)

        if not np.any(valid_mask):
            logger.warning("No valid data points found for statistics computation")
            return BiomassStatistics(
                mean=np.nan, std=np.nan, median=np.nan,
                min=np.nan, max=np.nan, count=0
            )

        # Apply valid mask
        data_masked = data_flat[valid_mask]
        weights_masked = weights_flat[valid_mask]

        # Apply outlier detection if requested
        if self.outlier_method:
            outlier_mask = self._detect_outliers(data_masked, method=self.outlier_method)
            data_masked = data_masked[~outlier_mask]
            weights_masked = weights_masked[~outlier_mask]

            if len(data_masked) == 0:
                logger.warning("All data points identified as outliers")
                return BiomassStatistics(
                    mean=np.nan, std=np.nan, median=np.nan,
                    min=np.nan, max=np.nan, count=0
                )

        # Compute weighted statistics
        stats_dict = self._compute_basic_statistics(data_masked, weights_masked)

        # Compute uncertainty statistics if available
        uncertainty_stats = None
        if uncertainty_variable:
            uncertainty_stats = self._compute_uncertainty_statistics(
                data, uncertainty_variable, weights, valid_mask
            )

        # Create result object
        result = BiomassStatistics(
            **stats_dict,
            uncertainty_mean=uncertainty_stats.get('mean') if uncertainty_stats else None,
            uncertainty_std=uncertainty_stats.get('std') if uncertainty_stats else None
        )

        logger.info(f"Statistics computed: mean={result.mean:.2f}, std={result.std:.2f}, count={result.count}")

        return result

    def _create_valid_mask(self, data: np.ndarray, weights: np.ndarray) -> np.ndarray:
        """Create mask for valid data points."""
        if not self.mask_invalid:
            return weights > 0

        # Mask invalid values
        valid_data = ~(np.isnan(data) | np.isinf(data) | (data < 0))
        valid_weights = ~(np.isnan(weights) | np.isinf(weights)) & (weights > 0)

        return valid_data & valid_weights

    def _detect_outliers(self, data: np.ndarray, method: str = "iqr") -> np.ndarray:
        """Detect outliers in the data."""
        if method == "iqr":
            Q1 = np.percentile(data, 25)
            Q3 = np.percentile(data, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = (data < lower_bound) | (data > upper_bound)

        elif method == "zscore":
            z_scores = np.abs(stats.zscore(data))
            outliers = z_scores > 3

        else:
            raise ValueError(f"Unknown outlier detection method: {method}")

        n_outliers = np.sum(outliers)
        if n_outliers > 0:
            logger.debug(f"Detected {n_outliers} outliers using {method} method")

        return outliers

    def _compute_basic_statistics(self, data: np.ndarray, weights: np.ndarray) -> dict[str, float]:
        """Compute basic weighted statistics."""
        # Normalize weights
        weights_norm = weights / np.sum(weights)

        # Weighted statistics
        weighted_mean = np.average(data, weights=weights)
        weighted_var = np.average((data - weighted_mean)**2, weights=weights)
        weighted_std = np.sqrt(weighted_var)

        # Weighted median (approximate using weighted percentile)
        sorted_indices = np.argsort(data)
        sorted_data = data[sorted_indices]
        sorted_weights = weights_norm[sorted_indices]
        cumsum_weights = np.cumsum(sorted_weights)

        # Find median
        median_idx = np.searchsorted(cumsum_weights, 0.5)
        if median_idx >= len(sorted_data):
            median_idx = len(sorted_data) - 1
        weighted_median = sorted_data[median_idx]

        return {
            'mean': float(weighted_mean),
            'std': float(weighted_std),
            'median': float(weighted_median),
            'min': float(np.min(data)),
            'max': float(np.max(data)),
            'count': len(data)
        }

    def _compute_uncertainty_statistics(
        self,
        data: xr.Dataset,
        uncertainty_variable: str,
        weights: np.ndarray,
        valid_mask: np.ndarray
    ) -> dict[str, float] | None:
        """Compute statistics for uncertainty data."""
        try:
            if uncertainty_variable in data.data_vars:
                uncertainty_array = data[uncertainty_variable]
            elif 'variable' in data.dims:
                uncertainty_array = data.sel(variable=uncertainty_variable)
            else:
                logger.warning(f"Uncertainty variable '{uncertainty_variable}' not found")
                return None

            # Flatten and apply same mask as main data
            uncertainty_flat = uncertainty_array.values.flatten()
            uncertainty_masked = uncertainty_flat[valid_mask]
            weights_masked = weights.flatten()[valid_mask]

            # Compute weighted uncertainty statistics
            weights_masked / np.sum(weights_masked)
            uncertainty_mean = np.average(uncertainty_masked, weights=weights_masked)
            uncertainty_var = np.average((uncertainty_masked - uncertainty_mean)**2, weights=weights_masked)
            uncertainty_std = np.sqrt(uncertainty_var)

            return {
                'mean': float(uncertainty_mean),
                'std': float(uncertainty_std)
            }

        except Exception as e:
            logger.warning("Failed to compute uncertainty statistics", exc_info=e)
            return None
