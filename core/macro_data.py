"""Shared, cached data snapshot for the macro dashboard and system overview."""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from config.api_keys import FMP_API_KEY, FRED_API_KEY


def _fred(series_id: str) -> pd.Series:
    if not FRED_API_KEY:
        response = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv",
            params={"id": series_id, "cosd": "1994-01-01"},
            timeout=20,
        )
        response.raise_for_status()
        frame = pd.read_csv(StringIO(response.text))
        if frame.empty or series_id not in frame.columns:
            return pd.Series(dtype=float)
        dates = pd.to_datetime(frame.iloc[:, 0], errors="coerce")
        values = pd.to_numeric(frame[series_id], errors="coerce")
        series = pd.Series(values.values, index=dates).dropna()
        return series.resample("ME").last().dropna().sort_index()
    response = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={"series_id": series_id, "api_key": FRED_API_KEY, "file_type": "json", "observation_start": "1994-01-01", "frequency": "m", "aggregation_method": "eop"},
        timeout=15,
    )
    response.raise_for_status()
    values = {item["date"]: float(item["value"]) for item in response.json().get("observations", []) if item.get("value") not in (None, ".")}
    series = pd.Series(values, dtype=float)
    series.index = pd.to_datetime(series.index)
    return series.sort_index()


def _yahoo(ticker: str) -> pd.Series:
    frame = yf.download(ticker, start="1994-01-01", interval="1mo", progress=False, auto_adjust=True)
    if frame.empty or "Close" not in frame.columns:
        return pd.Series(dtype=float)
    series = frame["Close"]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    series = pd.to_numeric(series, errors="coerce").dropna()
    series.index = pd.to_datetime(series.index).to_period("M").to_timestamp("M")
    return series.groupby(level=0).last().sort_index()


def _fmp(symbol: str) -> pd.Series:
    if not FMP_API_KEY:
        return pd.Series(dtype=float)
    response = requests.get(
        f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}",
        params={"apikey": FMP_API_KEY, "from": "1994-01-01"},
        timeout=20,
    )
    response.raise_for_status()
    history = response.json().get("historical", [])
    if not history:
        return pd.Series(dtype=float)
    frame = pd.DataFrame(history)[["date", "close"]]
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date")["close"].sort_index().resample("ME").last().dropna()


@st.cache_data(ttl=3600, show_spinner=False)
def load_macro_snapshot() -> tuple[pd.Series, pd.Series, pd.Series, str]:
    """Return 10Y, 30Y, S&P 500 and the actual source path used."""
    try:
        y10, y30 = _fred("DGS10"), _fred("DGS30")
    except Exception:
        y10, y30 = pd.Series(dtype=float), pd.Series(dtype=float)
    yield_source = "FRED（DGS10、DGS30）"
    if y10.empty or y30.empty:
        y10, y30 = _yahoo("^TNX"), _yahoo("^TYX")
        y10 = y10 / 10.0 if not y10.empty and float(y10.median()) > 15 else y10
        y30 = y30 / 10.0 if not y30.empty and float(y30.median()) > 15 else y30
        yield_source = "Yahoo Finance（FRED备用源）"

    try:
        sp500 = _fmp("^GSPC")
    except Exception:
        sp500 = pd.Series(dtype=float)
    equity_source = "FMP（标普500）"
    if sp500.empty:
        sp500 = _yahoo("^GSPC")
        equity_source = "Yahoo Finance（标普500备用源）"
    return y10, y30, sp500, f"{yield_source} · {equity_source}"


@st.cache_data(ttl=3600, show_spinner=False)
def load_macro_stress_snapshot() -> tuple[dict[str, pd.Series], str]:
    """Return the observed series used by the factor-07 market model."""
    y10, _y30, sp500, market_source = load_macro_snapshot()
    series = {"y10": y10, "sp500": sp500}
    missing = []
    for key, fred_id in {
        "y3m": "DGS3MO",
        "stlfsi": "STLFSI4",
    }.items():
        try:
            series[key] = _fred(fred_id)
        except Exception:
            series[key] = pd.Series(dtype=float)
            missing.append(fred_id)
    try:
        series["vix"] = _yahoo("^VIX")
    except Exception:
        series["vix"] = pd.Series(dtype=float)
        missing.append("VIX")
    source = f"{market_source} · FRED（DGS3MO、STLFSI4） · Yahoo Finance（VIX）"
    if missing:
        source += f" · 缺失：{', '.join(missing)}"
    return series, source


@st.cache_data(ttl=3600, show_spinner=False)
def load_credit_stress_snapshot() -> tuple[dict[str, pd.Series], str]:
    """Return the source series used by the factor-06 credit model."""
    series: dict[str, pd.Series] = {}
    missing = []
    for key, fred_id in {
        "hy_oas": "BAMLH0A0HYM2",
        "baa10y": "BAA10Y",
        "real_yield": "DFII10",
        "nfci": "NFCI",
    }.items():
        try:
            series[key] = _fred(fred_id)
        except Exception:
            series[key] = pd.Series(dtype=float)
            missing.append(fred_id)
    source = "FRED（BAMLH0A0HYM2、BAA10Y、DFII10、NFCI）"
    if missing:
        source += f" · 缺失：{', '.join(missing)}"
    return series, source
