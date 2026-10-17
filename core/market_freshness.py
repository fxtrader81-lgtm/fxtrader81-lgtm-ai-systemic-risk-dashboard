"""Freshness checks and short-window repairs for daily market-index series."""

from __future__ import annotations

from datetime import datetime, time, timedelta
import re
from threading import RLock
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


MARKETS = {
    "US": ("America/New_York", time(16, 30)),
    "CN": ("Asia/Shanghai", time(15, 30)),
}
YFINANCE_LOCK = RLock()
SINA_CHINA_INDEX = {"000001.SS": "sh000001", "399001.SZ": "sz399001"}


def download_yahoo(*args, **kwargs):
    """Serialize yfinance.download, which shares mutable state across calls."""
    with YFINANCE_LOCK:
        kwargs["threads"] = False
        return yf.download(*args, **kwargs)


def expected_close_date(market: str, now: datetime | None = None) -> pd.Timestamp:
    """Most recent weekday whose market close plus a short feed delay has passed.

    Exchange holidays are not inferred here; a holiday can trigger a cautious
    stale warning, never a fabricated price or an automatic SAFE state.
    """
    zone, cutoff = MARKETS[market]
    local_now = (now or datetime.now(ZoneInfo(zone))).astimezone(ZoneInfo(zone))
    day = local_now.date()
    if local_now.time() < cutoff:
        day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return pd.Timestamp(day)


def stale_sessions(series: pd.Series, market: str, now: datetime | None = None) -> int | None:
    """Number of expected weekday closes missing after the last observation."""
    valid = series.dropna()
    if valid.empty:
        return None
    expected = expected_close_date(market, now)
    latest = pd.Timestamp(valid.index.max()).tz_localize(None).normalize()
    if latest >= expected:
        return 0
    return len(pd.bdate_range(latest + pd.Timedelta(days=1), expected))


def merge_recent(history: pd.Series, recent: pd.Series) -> pd.Series:
    """Use the recent feed for overlapping dates and retain older history."""
    if history.empty:
        return recent.sort_index()
    if recent.empty:
        return history.sort_index()
    return recent.combine_first(history).sort_index()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_recent_yahoo(ticker: str) -> pd.Series:
    """Short-window Yahoo request; refreshes independently of long history."""
    try:
        frame = download_yahoo(
            ticker, period="1mo", interval="1d", progress=False,
            auto_adjust=True, timeout=10,
        )
        if frame.empty or "Close" not in frame.columns:
            return pd.Series(dtype=float)
        series = frame["Close"]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        series = pd.to_numeric(series, errors="coerce").dropna()
        series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
        return series[~series.index.duplicated(keep="last")].sort_index()
    except Exception:
        return pd.Series(dtype=float)


def repair_if_stale(history: pd.Series, ticker: str, market: str) -> tuple[pd.Series, bool]:
    """Always recheck recent prices; use their latest overlap or newer dates."""
    recent = fetch_recent_yahoo(ticker)
    repaired = merge_recent(history, recent)
    supplemented = not recent.empty and (history.empty or repaired.index.max() > history.index.max())
    return repaired, supplemented


def fetch_sina_china_close(ticker: str, now: datetime | None = None) -> pd.Series:
    """Use a dated public quote only after the China session has completed."""
    code = SINA_CHINA_INDEX.get(ticker)
    if code is None:
        return pd.Series(dtype=float)
    try:
        response = requests.get(
            "https://hq.sinajs.cn/list=" + code,
            headers={"Referer": "https://finance.sina.com.cn/", "User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.content.decode("gbk", errors="replace")
        match = re.search(r'="([^"]+)"', payload)
        if match is None:
            return pd.Series(dtype=float)
        fields = match.group(1).split(",")
        if len(fields) < 32:
            return pd.Series(dtype=float)
        price = float(fields[3])
        observed = pd.Timestamp(fields[30])
        quote_time = time.fromisoformat(fields[31])
        if (not 0 < price or pd.isna(observed)
                or quote_time < time(15, 0)
                or observed > expected_close_date("CN", now)):
            return pd.Series(dtype=float)
        return pd.Series([price], index=pd.DatetimeIndex([observed]), name=ticker)
    except (requests.RequestException, ValueError, TypeError, IndexError):
        return pd.Series(dtype=float)


def repair_china_if_stale(history: pd.Series, ticker: str) -> pd.Series:
    """Try Yahoo first, then the dated Sina close for a missing completed session."""
    merged, _ = repair_if_stale(history, ticker, "CN")
    if stale_sessions(merged, "CN") == 0:
        return merged
    backup = fetch_sina_china_close(ticker)
    if backup.empty or (not merged.empty and backup.index.max() <= merged.index.max()):
        return merged
    return merge_recent(merged, backup)
