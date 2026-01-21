"""Tests for seasonal biomass time series generation."""

from unittest.mock import patch

import numpy as np
import pandas as pd

from cosmicbiomass.core import get_seasonal_biomass_timeseries


def _make_vi_df(start: str, end: str, freq: str) -> pd.DataFrame:
    index = pd.date_range(start=start, end=end, freq=freq)
    values = np.sin(np.linspace(0, 2 * np.pi, len(index))) * 0.4 + 0.6
    df = pd.DataFrame(
        {
            "lai": values * 3.0,
            "evi": values * 0.8,
            "ndvi": values * 0.7,
        },
        index=index,
    )
    return df


@patch("cosmicbiomass.core.get_average_biomass_timeseries")
def test_seasonal_timeseries_infers_frequency(mock_timeseries):
    vi = _make_vi_df("2020-01-01", "2021-12-31", "1D")
    mock_timeseries.return_value = [
        {"year": 2020, "dataset": "agbd_2020", "result": {"summary": {"mean_biomass_Mg_ha": 100.0}}},
        {"year": 2021, "dataset": "agbd_2021", "result": {"summary": {"mean_biomass_Mg_ha": 120.0}}},
    ]

    df = get_seasonal_biomass_timeseries(
        lat=52.0,
        lon=11.0,
        start_time=2020,
        end_time=2021,
        vi=vi,
    )

    assert isinstance(df, pd.DataFrame)
    assert "agbd_annual" in df.columns
    assert "agbd_interpolated" in df.columns
    assert "vi_fused" in df.columns
    assert df.index.min().year == 2020
    assert df.index.max().year == 2021

    annual_max = df["agbd_interpolated"].groupby(df.index.year).max()
    annual_min = df["agbd_interpolated"].groupby(df.index.year).min()
    assert np.isclose(annual_max.loc[2020], 100.0, atol=1e-6)
    assert np.isclose(annual_max.loc[2021], 120.0, atol=1e-6)
    assert np.isclose(annual_min.loc[2020], 80.0, atol=1e-6)
    assert np.isclose(annual_min.loc[2021], 96.0, atol=1e-6)


@patch("cosmicbiomass.core.get_average_biomass_timeseries")
def test_seasonal_timeseries_respects_target_frequency(mock_timeseries):
    vi = _make_vi_df("2020-01-01", "2020-12-31", "1D")
    mock_timeseries.return_value = [
        {"year": 2020, "dataset": "agbd_2020", "result": {"summary": {"mean_biomass_Mg_ha": 80.0}}},
    ]

    df = get_seasonal_biomass_timeseries(
        lat=52.0,
        lon=11.0,
        start_time=2020,
        end_time=2020,
        vi=vi,
        target_frequency="1H",
    )

    assert df.index.freq is not None or pd.infer_freq(df.index) == "h"
    assert df.index.min().year == 2020
    assert df.index.max().year == 2020
    assert np.isclose(df["agbd_interpolated"].min(), 64.0, atol=1e-6)
    assert np.isclose(df["agbd_interpolated"].max(), 80.0, atol=1e-6)
