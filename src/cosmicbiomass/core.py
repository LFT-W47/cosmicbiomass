"""Core API functions for biomass analysis."""

import logging
import re
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from .config import BiomassConfig, FootprintConfig
from .processing import (
    FootprintProcessor,
    StatisticsProcessor,
    validate_footprint_coverage,
)
from .registry import get_source
from .sources import fetch_vi_timeseries

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
    return_format: str = "dataframe",
    **kwargs
) -> dict[str, Any] | pd.DataFrame:
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
        Pandas DataFrame with one row by default, or a dict when
        return_format="dict".
    """
    logger.info(
        "Computing average biomass at (%s, %s) with %sm radius",
        lat,
        lon,
        radius,
    )

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

    if return_format not in {"dataframe", "dict"}:
        raise ValueError("return_format must be 'dataframe' or 'dict'")

    if return_format == "dict":
        return result

    summary = result.get("summary", {})
    row = {
        "mean_biomass_Mg_ha": summary.get("mean_biomass_Mg_ha"),
        "std_biomass_Mg_ha": summary.get("std_biomass_Mg_ha"),
        "uncertainty_Mg_ha": summary.get("uncertainty_Mg_ha"),
        "uncertainty_source": summary.get("uncertainty_source"),
        "pixel_count": summary.get("pixel_count"),
        "dataset": dataset,
        "source": source,
        "latitude": lat,
        "longitude": lon,
        "radius_m": radius,
        "footprint_shape": footprint_shape,
        "units": result["data_info"].get("units"),
        "spatial_resolution": result["data_info"].get("spatial_resolution"),
        "temporal_coverage": result["data_info"].get("temporal_coverage"),
    }

    year = None
    if source.lower() == "dlr":
        try:
            year = _coerce_year(dataset)
        except ValueError:
            year = None

    if year is not None:
        index = pd.PeriodIndex([year], freq="Y", name="year")
    else:
        index = pd.Index([dataset], name="dataset")

    df = pd.DataFrame([row], index=index)
    df.attrs["result"] = result
    return df


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


def _infer_target_index(
    vi_series: pd.Series,
    target_frequency: str | None,
    reference_index: pd.DatetimeIndex | None,
    start_time: int | str | date | datetime,
    end_time: int | str | date | datetime,
) -> pd.DatetimeIndex:
    if reference_index is not None:
        return pd.DatetimeIndex(reference_index)

    freq = target_frequency or pd.infer_freq(vi_series.index)
    if isinstance(freq, str):
        freq = freq.lower()
    if freq is None:
        return pd.DatetimeIndex(vi_series.index)

    start_year = _coerce_year(start_time)
    end_year = _coerce_year(end_time)
    start_dt = pd.Timestamp(year=start_year, month=1, day=1)
    end_dt = pd.Timestamp(year=end_year, month=12, day=31)
    return pd.date_range(start=start_dt, end=end_dt, freq=freq)


def _scale_series_by_year(values: pd.Series) -> pd.Series:
    out = values.copy()
    for _year, seg in out.groupby(out.index.year):
        if seg.dropna().empty:
            continue
        vmin = float(np.nanmin(seg))
        vmax = float(np.nanmax(seg))
        if vmax > vmin:
            out.loc[seg.index] = (seg - vmin) / (vmax - vmin)
        else:
            out.loc[seg.index] = 0.0
    return out.clip(0.0, 1.0)


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
    return_format: str = "dataframe",
    **kwargs
) -> list[dict[str, Any]] | pd.DataFrame:
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
        Pandas DataFrame by default, or an ordered list of dicts with keys:
        year, dataset, result when return_format="list".
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
            return_format="dict",
            **kwargs,
        )
        series.append({"year": year, "dataset": dataset_id, "result": result})

    if return_format not in {"dataframe", "list"}:
        raise ValueError("return_format must be 'dataframe' or 'list'")
    if return_format == "list":
        return series

    rows: list[dict[str, Any]] = []
    years_index: list[int] = []
    datasets_index: list[str] = []
    for entry in series:
        summary = entry["result"].get("summary", {})
        row = {
            "mean_biomass_Mg_ha": summary.get("mean_biomass_Mg_ha"),
            "std_biomass_Mg_ha": summary.get("std_biomass_Mg_ha"),
            "uncertainty_Mg_ha": summary.get("uncertainty_Mg_ha"),
            "uncertainty_source": summary.get("uncertainty_source"),
            "pixel_count": summary.get("pixel_count"),
        }
        rows.append(row)
        years_index.append(int(entry["year"]))
        datasets_index.append(entry["dataset"])

    if source.lower() == "dlr":
        index = pd.PeriodIndex(years_index, freq="Y", name="year")
    else:
        index = pd.Index(years_index, name="year")

    df = pd.DataFrame(rows, index=index)
    df.attrs["series"] = series
    df.attrs["datasets"] = dict(zip(years_index, datasets_index, strict=False))
    df.attrs["source"] = source
    df.attrs["dataset_template"] = dataset
    return df


def get_seasonal_biomass_timeseries(
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
    vi: pd.DataFrame | dict[str, pd.Series] | None = None,
    vi_source: str = "auto",
    target_frequency: str | None = None,
    reference_index: pd.DatetimeIndex | None = None,
    baseline_fraction: float = 0.8,
    **kwargs,
) -> pd.DataFrame:
    """
    Build a higher-frequency biomass time series using VI-driven seasonal interpolation.

    This function combines annual AGBD values with vegetation index (VI) time series
    (LAI/EVI/NDVI) to produce a higher-resolution pandas DataFrame.

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
        vi: Optional VI inputs as a DataFrame or dict with keys "lai", "evi", "ndvi"
        vi_source: "auto" (default), "gee+pc", "gee", or "pc" for fetching VI when vi is None
        target_frequency: Optional pandas frequency (e.g., "1H", "1D"). If None, auto-detect.
        reference_index: Optional DatetimeIndex (e.g., Neptoon index) for auto alignment.
        baseline_fraction: Annual baseline fraction (0..1). VI modulates the remaining fraction.
        **kwargs: Additional configuration parameters

    Returns:
        DataFrame indexed by timestamps with columns:
        - agbd_annual
        - agbd_interpolated
        - agbd_lai / agbd_evi / agbd_ndvi (if provided)
        - agbd_fused
        - vi_fused
        - vi_lai / vi_evi / vi_ndvi (if provided)
    """
    if vi is None:
        if vi_source not in {"auto", "gee+pc", "gee", "pc"}:
            raise ValueError("vi_source must be 'auto', 'gee+pc', 'gee', or 'pc'")
        use_gee_lai = vi_source in {"auto", "gee+pc", "gee"}
        use_pc_vi = vi_source in {"auto", "gee+pc", "pc"}
        vi = fetch_vi_timeseries(
            lat=lat,
            lon=lon,
            start_time=start_time,
            end_time=end_time,
            include_evi=True,
            use_gee_lai=use_gee_lai,
            use_pc_vi=use_pc_vi,
            radius_cutoff_m=radius,
            center_lat=lat,
        )

    logger.info("Building seasonal biomass time series for (%s, %s)", lat, lon)

    def _to_series(value: pd.Series | pd.DataFrame | None) -> pd.Series | None:
        if value is None:
            return None
        if hasattr(value, "index"):
            series = value.squeeze()
            if hasattr(series, "index"):
                series.index = pd.to_datetime(series.index)
                return series.sort_index()
        raise ValueError("VI inputs must be pandas Series or DataFrame columns")

    if hasattr(vi, "columns"):
        lai = _to_series(vi["lai"]) if "lai" in vi.columns else None
        evi = _to_series(vi["evi"]) if "evi" in vi.columns else None
        ndvi = _to_series(vi["ndvi"]) if "ndvi" in vi.columns else None
    else:
        lai = _to_series(vi.get("lai"))
        evi = _to_series(vi.get("evi"))
        ndvi = _to_series(vi.get("ndvi"))

    if lai is None and evi is None and ndvi is None:
        raise ValueError("At least one VI series (lai/evi/ndvi) is required")

    def _normalize_seasonyear(s: pd.Series) -> pd.Series:
        out = s.copy()
        for _year, seg in out.groupby(out.index.year):
            if seg.dropna().size:
                p5 = float(np.nanpercentile(seg, 5))
                p95 = float(np.nanpercentile(seg, 95))
                if p95 > p5:
                    out.loc[seg.index] = (seg - p5) / (p95 - p5)
        return out.clip(0.0, 1.0)

    def _build_fused_vi(
        lai_s: pd.Series | None,
        evi_s: pd.Series | None,
        ndvi_s: pd.Series | None,
    ) -> pd.Series:
        series = [s for s in (lai_s, evi_s, ndvi_s) if s is not None and not s.empty]
        idx = series[0].index
        for s in series[1:]:
            idx = idx.union(s.index)
        idx = pd.DatetimeIndex(sorted(idx.unique()))

        lai_i = lai_s.reindex(idx).interpolate("time") if lai_s is not None else None
        evi_i = evi_s.reindex(idx).interpolate("time") if evi_s is not None else None
        ndvi_i = ndvi_s.reindex(idx).interpolate("time") if ndvi_s is not None else None

        if evi_i is None and ndvi_i is None:
            if lai_i is None:
                raise ValueError("No VI series available for fusion")
            return _normalize_seasonyear(lai_i)
        if evi_i is None:
            return _normalize_seasonyear(ndvi_i)
        if ndvi_i is None:
            return _normalize_seasonyear(evi_i)

        lai_abs = lai_i
        evi_n = _normalize_seasonyear(evi_i)
        ndvi_n = _normalize_seasonyear(ndvi_i)

        t1, t2 = 2.0, 3.0
        a_low, a_mid, a_high = 0.65, 0.50, 0.35
        alpha = pd.Series(a_mid, index=idx)
        if lai_abs is not None and not lai_abs.empty:
            alpha.loc[lai_abs < t1] = a_low
            alpha.loc[(lai_abs >= t1) & (lai_abs < t2)] = a_mid
            alpha.loc[lai_abs >= t2] = a_high
        f = alpha.values * ndvi_n.fillna(0).values + (1.0 - alpha.values) * evi_n.fillna(0).values
        return pd.Series(f, index=idx).clip(0.0, 1.0)

    if not (0.0 <= baseline_fraction <= 1.0):
        raise ValueError("baseline_fraction must be between 0 and 1")

    vi_fused = _build_fused_vi(lai, evi, ndvi)

    target_index = _infer_target_index(
        vi_fused,
        target_frequency,
        reference_index,
        start_time,
        end_time,
    )

    vi_fused = vi_fused.reindex(target_index).interpolate("time")
    vi_lai = lai.reindex(target_index).interpolate("time") if lai is not None else None
    vi_evi = evi.reindex(target_index).interpolate("time") if evi is not None else None
    vi_ndvi = ndvi.reindex(target_index).interpolate("time") if ndvi is not None else None

    series = get_average_biomass_timeseries(
        lat=lat,
        lon=lon,
        radius=radius,
        source=source,
        dataset=dataset,
        start_time=start_time,
        end_time=end_time,
        data_dir=data_dir,
        footprint_shape=footprint_shape,
        include_uncertainty=include_uncertainty,
        outlier_method=outlier_method,
        **kwargs,
    )

    annual_map: dict[int, float] = {}
    if hasattr(series, "columns"):
        values = series
        if "mean_biomass_Mg_ha" in values.columns:
            if isinstance(values.index, pd.PeriodIndex):
                index_years = [int(period.year) for period in values.index]
            else:
                index_years = [int(_coerce_year(value)) for value in values.index]
            for year, mean in zip(index_years, values["mean_biomass_Mg_ha"], strict=False):
                annual_map[year] = mean
        else:
            raise ValueError("Expected mean_biomass_Mg_ha column in timeseries DataFrame")
    else:
        for entry in series:
            year = int(entry["year"])
            summary = entry["result"].get("summary", {})
            annual_map[year] = summary.get("mean_biomass_Mg_ha", np.nan)

    years = pd.Index(sorted(annual_map.keys()), name="year")
    annual_series = pd.Series(annual_map, index=years, name="agbd_annual")

    annual_on_index = pd.Series(index=target_index, dtype=float)
    for year, value in annual_series.items():
        mask = target_index.year == year
        annual_on_index.loc[mask] = value

    seasonal_multiplier = _scale_series_by_year(vi_fused)
    agbd_interpolated = annual_on_index * (baseline_fraction + (1.0 - baseline_fraction) * seasonal_multiplier)

    agbd_fused = agbd_interpolated
    agbd_lai = None
    agbd_evi = None
    agbd_ndvi = None

    if vi_lai is not None:
        lai_mult = _scale_series_by_year(vi_lai)
        agbd_lai = annual_on_index * (baseline_fraction + (1.0 - baseline_fraction) * lai_mult)
    if vi_evi is not None:
        evi_mult = _scale_series_by_year(vi_evi)
        agbd_evi = annual_on_index * (baseline_fraction + (1.0 - baseline_fraction) * evi_mult)
    if vi_ndvi is not None:
        ndvi_mult = _scale_series_by_year(vi_ndvi)
        agbd_ndvi = annual_on_index * (baseline_fraction + (1.0 - baseline_fraction) * ndvi_mult)

    data = {
        "agbd_annual": annual_on_index,
        "agbd_interpolated": agbd_interpolated,
        "agbd_fused": agbd_fused,
        "vi_fused": vi_fused,
    }
    if vi_lai is not None:
        data["vi_lai"] = vi_lai
    if vi_evi is not None:
        data["vi_evi"] = vi_evi
    if vi_ndvi is not None:
        data["vi_ndvi"] = vi_ndvi
    if agbd_lai is not None:
        data["agbd_lai"] = agbd_lai
    if agbd_evi is not None:
        data["agbd_evi"] = agbd_evi
    if agbd_ndvi is not None:
        data["agbd_ndvi"] = agbd_ndvi

    return pd.DataFrame(data, index=target_index).sort_index()


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
