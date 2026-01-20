"""Vegetation index (VI) data fetchers for seasonal interpolation."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

logger = logging.getLogger(__name__)

_DEFAULT_GAP_STEPS = 5
_DEFAULT_USE_CLIMATOLOGY = True
_DEFAULT_FINAL_BRIDGE = True
_DEFAULT_SMOOTH_KIND = "rolling"
_DEFAULT_ROLLING_WINDOW = 3


def _deg_to_m_grid(x_deg: np.ndarray, y_deg: np.ndarray, lat0: float) -> tuple[np.ndarray, np.ndarray]:
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * np.cos(np.deg2rad(lat0))
    x0 = float(np.nanmean(x_deg))
    y0 = float(np.nanmean(y_deg))
    xd, yd = np.meshgrid(x_deg - x0, y_deg - y0)
    return xd * m_per_deg_lon, yd * m_per_deg_lat


def _crns_weights(
    x_vals: np.ndarray,
    y_vals: np.ndarray,
    center_lat: float,
    radius_cutoff_m: float = 0.0,
) -> np.ndarray:
    xd, yd = _deg_to_m_grid(x_vals, y_vals, center_lat)
    r = np.sqrt(xd**2 + yd**2).astype(np.float64)
    w_r = 30.0 * np.exp(-r / 1.6) + np.exp(-r / 100.0)
    w = w_r / np.maximum(r, 1.0)
    if radius_cutoff_m and radius_cutoff_m > 0:
        w[r > radius_cutoff_m] = 0.0
    s = float(np.nansum(w))
    if s == 0.0:
        raise ValueError("All weights are zero")
    return w / s


def _series_from_da(da: xr.DataArray) -> pd.Series:
    tindex = pd.DatetimeIndex(pd.to_datetime(np.asarray(da["time"].data)))
    return pd.Series(np.asarray(da.data), index=tindex).sort_index()


def _aggregate_weighted_ts(
    da: xr.DataArray,
    center_lat: float,
    radius_cutoff_m: float,
) -> xr.DataArray:
    x_vals = np.asarray(da.x.data)
    y_vals = np.asarray(da.y.data)
    try:
        if x_vals.size == 0 or y_vals.size == 0 or np.all(np.isnan(x_vals)) or np.all(np.isnan(y_vals)):
            raise ValueError("empty x/y coordinates")
        w = _crns_weights(x_vals, y_vals, center_lat=center_lat, radius_cutoff_m=radius_cutoff_m)
        w_da = xr.DataArray(w, coords={"y": da.y, "x": da.x}, dims=("y", "x"))
        valid = da.notnull()
        num = (da * w_da).where(valid).sum(dim=("y", "x"))
        den = w_da.where(valid).sum(dim=("y", "x"))
        return (num / xr.where(den > 0, den, np.nan)).astype(float)
    except Exception as exc:
        logger.warning("CRNS weighting failed, falling back to spatial aggregate: %s", exc)
        try:
            return da.median(dim=("y", "x"), skipna=True).astype(float)
        except Exception:
            return da.mean(dim=("y", "x"), skipna=True).astype(float)


def _gap_fill(
    series: pd.Series,
    small_gap_steps: int = _DEFAULT_GAP_STEPS,
    use_climatology: bool = _DEFAULT_USE_CLIMATOLOGY,
    final_bridge: bool = _DEFAULT_FINAL_BRIDGE,
) -> pd.Series:
    filled = series.interpolate("time", limit=small_gap_steps, limit_direction="both")
    if use_climatology:
        doy = filled.index.dayofyear
        clim = filled.groupby(doy).median()
        na = filled.isna()
        if na.any():
            filled.loc[na] = clim.reindex(doy[na]).values
    if final_bridge:
        return filled.interpolate("time", limit_direction="both", limit_area="inside")
    return filled


def _smooth(
    series: pd.Series,
    kind: str = _DEFAULT_SMOOTH_KIND,
    rolling_window: int = _DEFAULT_ROLLING_WINDOW,
) -> pd.Series:
    if kind == "rolling":
        return series.rolling(window=rolling_window, center=True, min_periods=1).median()
    return series


def _decode_mcd15_qc(
    qc_da: xr.DataArray,
    require_modland_good: bool,
    require_dead_detector_ok: bool,
    require_cloud_clear: bool,
    max_scf_code: int,
) -> xr.DataArray:
    q = qc_da.astype("uint16")
    modland_good = (q & 0b1) == 0
    dead_ok = ((q >> 2) & 0b1) == 0
    cloud_state = (q >> 3) & 0b11
    cloud_ok = cloud_state == 0 if require_cloud_clear else cloud_state <= 0b10
    scf_conf = (q >> 5) & 0b111
    scf_ok = scf_conf <= max_scf_code
    mask = xr.ones_like(q, dtype=bool)
    if require_modland_good:
        mask = mask & modland_good
    if require_dead_detector_ok:
        mask = mask & dead_ok
    return mask & cloud_ok & scf_ok


def _fetch_lai_gee(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    center_lat: float,
    radius_cutoff_m: float,
    scale_factor_lai: float,
    require_modland_good: bool,
    require_dead_detector_ok: bool,
    require_cloud_clear: bool,
    max_scf_code: int,
) -> pd.Series:
    try:
        import cubo  # type: ignore
        import ee  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("GEE/cubo required for LAI fetch") from exc

    try:
        ee.Initialize(project="ee-louit")
    except Exception:
        ee.Initialize()

    da = cubo.create(
        lat=lat,
        lon=lon,
        collection="MODIS/061/MCD15A3H",
        bands=["Lai", "Fpar", "FparLai_QC"],
        start_date=start_date,
        end_date=end_date,
        edge_size=50,
        resolution=10,
        gee=True,
    )

    lai = da.sel(band="Lai").astype("float32") * scale_factor_lai
    qc_band = da.sel(band="FparLai_QC")
    mask = _decode_mcd15_qc(
        qc_band,
        require_modland_good=require_modland_good,
        require_dead_detector_ok=require_dead_detector_ok,
        require_cloud_clear=require_cloud_clear,
        max_scf_code=max_scf_code,
    )
    lai = lai.where(mask)

    ts = _aggregate_weighted_ts(lai, center_lat=center_lat, radius_cutoff_m=radius_cutoff_m)
    series = _series_from_da(ts)
    series = _gap_fill(series)
    return _smooth(series)


def _stackstac_stack(
    items: list[Any],
    assets: list[str],
    bounds: list[float],
    epsg: int,
    resolution: float,
    chunksize: int,
) -> xr.DataArray:
    import stackstac as st  # type: ignore

    try:
        from stackstac.gdal import configure as gdal_config  # type: ignore

        gcfg = gdal_config(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            GDAL_HTTP_MAX_RETRY="6",
            GDAL_HTTP_RETRY_DELAY="1",
            GDAL_HTTP_TIMEOUT="30",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        )
    except Exception:
        gcfg = None
    try:
        from rasterio.errors import RasterioIOError  # type: ignore

        err_types = (RasterioIOError,)
    except Exception:
        err_types = (Exception,)

    try:
        kw = {
            "items": items,
            "assets": list(assets),
            "bounds": bounds,
            "epsg": epsg,
            "resolution": resolution,
            "chunksize": chunksize,
            "sortby_date": "asc",
            "errors_as_nodata": err_types,
        }
        if gcfg is not None:
            kw["gdal_env"] = gcfg
        return st.stack(**kw)
    except TypeError:
        kw = {
            "items": items,
            "assets": list(assets),
            "bounds": bounds,
            "epsg": epsg,
            "resolution": resolution,
            "chunksize": chunksize,
            "sortby_date": "asc",
        }
        if gcfg is not None:
            kw["gdal_env"] = gcfg
        return st.stack(**kw)


def _fetch_vi_pc_stackstac(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    include_evi: bool,
    center_lat: float,
    radius_cutoff_m: float,
) -> tuple[pd.Series | None, pd.Series | None]:
    import planetary_computer  # type: ignore
    from pystac_client import Client  # type: ignore

    bbox = [lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01]
    api = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    search = api.search(
        collections=["modis-13A1-061"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
    )
    items = list(search.get_items())
    if not items:
        point = {"type": "Point", "coordinates": [lon, lat]}
        items = list(
            api.search(
                collections=["modis-13A1-061"],
                intersects=point,
                datetime=f"{start_date}/{end_date}",
            ).get_items()
        )
    if not items:
        raise RuntimeError("No MODIS 13A1 items found")

    assets = ["500m_16_days_NDVI"] + (["500m_16_days_EVI"] if include_evi else [])
    assets.append("500m_16_days_pixel_reliability")

    da = _stackstac_stack(
        items=items,
        assets=assets,
        bounds=bbox,
        epsg=4326,
        resolution=0.00463,
        chunksize=128,
    ).rename("VI_raw")
    da = da.assign_coords(band=[str(b) for b in da.band.values])

    times: list[np.datetime64] = []
    for it in items:
        dt = it.properties.get("start_datetime") or it.properties.get("datetime") or it.properties.get("end_datetime")
        if dt:
            times.append(np.datetime64(dt))
        else:
            match = re.search(r"\.A(\d{4})(\d{3})\.", it.id or "")
            if match:
                year = int(match.group(1))
                doy = int(match.group(2))
                stamp = pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=doy - 1)
                times.append(np.datetime64(stamp.date()))
            else:
                times.append(np.datetime64("NaT"))
    da = da.assign_coords(time=("time", times))
    valid = ~np.isnat(da.time.values)
    if not valid.any():
        raise ValueError("All time coordinates are NaT")
    if not valid.all():
        da = da.isel(time=valid)

    bands_list = list(map(str, da.band.values))
    qa = da.sel(band="500m_16_days_pixel_reliability") if "500m_16_days_pixel_reliability" in bands_list else None

    def _process(vi_band_name: str, clip: tuple[float, float]) -> pd.Series | None:
        if vi_band_name not in bands_list:
            return None
        vi = da.sel(band=vi_band_name)
        if np.issubdtype(vi.dtype, np.integer):
            vi = vi.astype("float32") * 0.0001
        if qa is not None:
            vi = vi.where(qa <= 1)
        vi = vi.where((vi >= clip[0]) & (vi <= clip[1]))

        ts = _aggregate_weighted_ts(vi, center_lat=center_lat, radius_cutoff_m=radius_cutoff_m)
        series = _series_from_da(ts)
        series = _gap_fill(series)
        return _smooth(series)

    ndvi = _process("500m_16_days_NDVI", clip=(-0.2, 1.0))
    evi = _process("500m_16_days_EVI", clip=(-0.1, 1.0)) if include_evi else None
    return evi, ndvi


def _fetch_vi_pc_cubo(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    include_evi: bool,
    center_lat: float,
    radius_cutoff_m: float,
) -> tuple[pd.Series | None, pd.Series | None]:
    try:
        import cubo  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("cubo required for PC fetch") from exc

    bands = ["500m_16_days_NDVI"] + (["500m_16_days_EVI"] if include_evi else [])
    bands.append("500m_16_days_pixel_reliability")

    da = cubo.create(
        lat=lat,
        lon=lon,
        collection="modis-13A1-061",
        bands=bands,
        start_date=start_date,
        end_date=end_date,
        edge_size=50,
        resolution=500,
        stac="https://planetarycomputer.microsoft.com/api/stac/v1",
    )

    da = da.assign_coords(band=[str(b) for b in da.band.values])
    bands_list = list(map(str, da.band.values))
    qa = da.sel(band="500m_16_days_pixel_reliability") if "500m_16_days_pixel_reliability" in bands_list else None

    def _process(vi_band_name: str, clip: tuple[float, float]) -> pd.Series | None:
        if vi_band_name not in bands_list:
            return None
        vi = da.sel(band=vi_band_name)
        if np.issubdtype(vi.dtype, np.integer):
            vi = vi.astype("float32") * 0.0001
        if qa is not None:
            vi = vi.where(qa <= 1)
        vi = vi.where((vi >= clip[0]) & (vi <= clip[1]))
        ts = _aggregate_weighted_ts(vi, center_lat=center_lat, radius_cutoff_m=radius_cutoff_m)
        series = _series_from_da(ts)
        series = _gap_fill(series)
        return _smooth(series)

    ndvi = _process("500m_16_days_NDVI", clip=(-0.2, 1.0))
    evi = _process("500m_16_days_EVI", clip=(-0.1, 1.0)) if include_evi else None
    return evi, ndvi


def fetch_vi_timeseries(
    lat: float,
    lon: float,
    start_time: int | str | date | datetime,
    end_time: int | str | date | datetime,
    include_evi: bool = True,
    use_gee_lai: bool = True,
    use_pc_vi: bool = True,
    pc_mode: str = "stackstac",
    radius_cutoff_m: float = 0.0,
    center_lat: float | None = None,
    scale_factor_lai: float = 0.1,
    require_modland_good: bool = True,
    require_dead_detector_ok: bool = True,
    require_cloud_clear: bool = True,
    max_scf_code: int = 1,
) -> pd.DataFrame:
    """
    Fetch VI time series (LAI, EVI, NDVI) with optional CRNS weighting.

    Returns a DataFrame indexed by timestamps with columns: lai, evi, ndvi.
    """
    center_lat = center_lat if center_lat is not None else lat
    start_date = str(pd.to_datetime(start_time).date())
    end_date = str(pd.to_datetime(end_time).date())

    lai = None
    evi = None
    ndvi = None

    if use_gee_lai:
        logger.info("Fetching LAI via GEE/cubo")
        lai = _fetch_lai_gee(
            lat=lat,
            lon=lon,
            start_date=start_date,
            end_date=end_date,
            center_lat=center_lat,
            radius_cutoff_m=radius_cutoff_m,
            scale_factor_lai=scale_factor_lai,
            require_modland_good=require_modland_good,
            require_dead_detector_ok=require_dead_detector_ok,
            require_cloud_clear=require_cloud_clear,
            max_scf_code=max_scf_code,
        )

    if use_pc_vi:
        logger.info("Fetching VI via Planetary Computer")
        try:
            if pc_mode == "cubo":
                evi, ndvi = _fetch_vi_pc_cubo(
                    lat=lat,
                    lon=lon,
                    start_date=start_date,
                    end_date=end_date,
                    include_evi=include_evi,
                    center_lat=center_lat,
                    radius_cutoff_m=radius_cutoff_m,
                )
            else:
                evi, ndvi = _fetch_vi_pc_stackstac(
                    lat=lat,
                    lon=lon,
                    start_date=start_date,
                    end_date=end_date,
                    include_evi=include_evi,
                    center_lat=center_lat,
                    radius_cutoff_m=radius_cutoff_m,
                )
        except Exception as exc:
            logger.warning("PC VI fetch failed: %s", exc)
            if pc_mode == "cubo":
                logger.info("Falling back to stackstac")
                evi, ndvi = _fetch_vi_pc_stackstac(
                    lat=lat,
                    lon=lon,
                    start_date=start_date,
                    end_date=end_date,
                    include_evi=include_evi,
                    center_lat=center_lat,
                    radius_cutoff_m=radius_cutoff_m,
                )
            else:
                raise

    def _dedupe(series: pd.Series | None) -> pd.Series | None:
        if series is None:
            return None
        if series.index.has_duplicates:
            series = series.groupby(series.index).mean()
        return series.sort_index()

    lai = _dedupe(lai)
    evi = _dedupe(evi)
    ndvi = _dedupe(ndvi)

    def _require_data(series: pd.Series | None, label: str) -> None:
        if series is None:
            return
        if series.isna().all():
            raise RuntimeError(f"{label} series contains only NaN values")

    _require_data(lai, "LAI")
    _require_data(evi, "EVI")
    _require_data(ndvi, "NDVI")

    df = pd.DataFrame(index=pd.DatetimeIndex([]))
    if lai is not None:
        df["lai"] = lai
    if evi is not None:
        df["evi"] = evi
    if ndvi is not None:
        df["ndvi"] = ndvi

    if df.empty:
        raise RuntimeError("No VI time series could be fetched")

    return df.sort_index()
