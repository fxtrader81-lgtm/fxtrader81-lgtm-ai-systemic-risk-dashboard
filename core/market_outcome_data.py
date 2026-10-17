"""Daily S&P 500 closes used only for historical six-month outcomes."""

from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from config.api_keys import FMP_API_KEY
from core.market_freshness import download_yahoo, repair_if_stale


@st.cache_data(ttl=3600, show_spinner=False)
def _fmp_daily() -> pd.Series:
    if not FMP_API_KEY:
        return pd.Series(dtype=float)
    response = requests.get(
        "https://financialmodelingprep.com/api/v3/historical-price-full/^GSPC",
        params={"apikey": FMP_API_KEY, "from": "1994-01-01"},
        timeout=20,
    )
    response.raise_for_status()
    history = response.json().get("historical", [])
    if not history:
        return pd.Series(dtype=float)
    frame = pd.DataFrame(history)[["date", "close"]]
    frame["date"] = pd.to_datetime(frame["date"])
    return pd.to_numeric(frame.set_index("date")["close"], errors="coerce").dropna().sort_index()


@st.cache_data(ttl=3600, show_spinner=False)
def _yahoo_daily() -> pd.Series:
    frame = download_yahoo("^GSPC", start="1994-01-01", interval="1d", progress=False, auto_adjust=True)
    if frame.empty or "Close" not in frame.columns:
        return pd.Series(dtype=float)
    series = frame["Close"]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    series = pd.to_numeric(series, errors="coerce").dropna()
    series.index = pd.to_datetime(series.index).tz_localize(None)
    return series.sort_index()


@st.cache_data(ttl=300, show_spinner=False)
def load_sp500_daily() -> tuple[pd.Series, str]:
    """Prefer complete history, then repair missing recent sessions separately."""
    try:
        series = _fmp_daily()
    except Exception:
        series = pd.Series(dtype=float)
    source = "FMP（^GSPC 日收盘价）"
    if series.empty or series.index.min() > pd.Timestamp("1997-10-31"):
        try:
            yahoo_series = _yahoo_daily()
        except Exception:
            yahoo_series = pd.Series(dtype=float)
        if not yahoo_series.empty and (series.empty or yahoo_series.index.min() < series.index.min()):
            series = yahoo_series
            source = "Yahoo Finance（^GSPC 日收盘价；FMP 历史覆盖不足时的备用源）"
        elif not series.empty:
            source = "FMP（^GSPC 日收盘价；早期事件可能无数据）"
    series, supplemented = repair_if_stale(series, "^GSPC", "US")
    if supplemented:
        source += "；近期缺失日期由 Yahoo Finance 补齐"
    return (series, source) if not series.empty else (series, "日线暂不可用")
