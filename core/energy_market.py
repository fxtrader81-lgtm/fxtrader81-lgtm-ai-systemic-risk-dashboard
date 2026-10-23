"""Shared CEG/VST market signal for Factor 04 detail and overview.

The signal is deliberately narrow: it is a low-weight market-price proxy, not
evidence of physical grid scarcity.  Both required tickers must be available
for the score to be used.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from statistics import mean
from zoneinfo import ZoneInfo

import requests
import streamlit as st


TICKERS = ("CEG", "VST")
YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def score_from_position(position_pct):
    if (isinstance(position_pct, bool) or not isinstance(position_pct, (int, float))
            or not math.isfinite(position_pct) or not 0 <= position_pct <= 100):
        return None
    if position_pct > 80:
        return 75
    if position_pct > 60:
        return 55
    if position_pct > 40:
        return 35
    return 20


def _state(score):
    if score is None:
        return "N/A"
    if score < 30:
        return "SAFE"
    if score < 50:
        return "WATCH"
    if score < 70:
        return "WARNING"
    return "CRITICAL"


def make_snapshot(rows, checked_at=None):
    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    result = {
        "available": False,
        "tickers": list(TICKERS),
        "rows": {},
        "mean_position_pct": None,
        "score": None,
        "state": "N/A",
        "weight": 0.15,
        "contribution": None,
        "checked_at": checked_at,
        "cache_policy": "页面读取时检查；成功结果缓存1小时",
        "method_version": "ceg-vst-52w-position-v1",
        "missing_reason": "CEG/VST任一必要行情缺失，市场分项N/A；不使用后备分",
    }
    if not isinstance(rows, dict) or set(rows) != set(TICKERS):
        return result
    normalized = {}
    for ticker in TICKERS:
        row = rows.get(ticker, {})
        values = [row.get(k) for k in ("current_price", "week52_low", "week52_high")]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            return result
        current, low, high = map(float, values)
        if current <= 0 or low <= 0 or high <= low:
            return result
        position = (current - low) / (high - low) * 100
        if not 0 <= position <= 100:
            return result
        observed_on = row.get("observed_on")
        if not observed_on:
            return result
        normalized[ticker] = {
            "current_price": current,
            "week52_low": low,
            "week52_high": high,
            "position_pct": position,
            "observed_on": str(observed_on),
        }
    if len({row["observed_on"] for row in normalized.values()}) != 1:
        result["missing_reason"] = "CEG/VST行情日期不一致，市场分项N/A；不拼接不同交易日"
        return result
    position = mean(row["position_pct"] for row in normalized.values())
    score = score_from_position(position)
    return dict(
        result,
        available=True,
        rows=normalized,
        mean_position_pct=position,
        score=score,
        state=_state(score),
        contribution=round(score * result["weight"], 2),
        observed_on=next(iter(normalized.values()))["observed_on"],
        missing_reason="",
    )


def _fetch_ticker(ticker):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
    response = requests.get(url, headers=YF_HEADERS, timeout=10)
    response.raise_for_status()
    payload = response.json().get("chart", {}).get("result", [])
    if not payload:
        return None
    meta = payload[0].get("meta", {})
    market_time = meta.get("regularMarketTime")
    if not market_time:
        return None
    observed_on = datetime.fromtimestamp(float(market_time), timezone.utc).astimezone(
        ZoneInfo("America/New_York")
    ).date().isoformat()
    return {
        "current_price": meta.get("regularMarketPrice"),
        "week52_low": meta.get("fiftyTwoWeekLow"),
        "week52_high": meta.get("fiftyTwoWeekHigh"),
        "observed_on": observed_on,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_energy_market():
    rows = {}
    for ticker in TICKERS:
        try:
            row = _fetch_ticker(ticker)
        except (requests.RequestException, ValueError, TypeError):
            row = None
        if row:
            rows[ticker] = row
    return make_snapshot(rows)
