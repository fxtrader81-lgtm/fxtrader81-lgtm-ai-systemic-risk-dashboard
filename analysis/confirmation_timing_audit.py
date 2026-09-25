"""Audit whether historical market confirmation preceded an equity decline.

The 06/07 flags come from the existing monthly backtest. Daily S&P 500 closes
locate the first 10% decline and the drawdown already sustained when a 07
signal was first observable at month-end. This is a current-vintage
reconstruction, not a real-time historical backtest of revised FSI series.
"""

from __future__ import annotations

from pathlib import Path
from io import StringIO

import numpy as np
import pandas as pd
import requests
import yfinance as yf


ROOT = Path(__file__).resolve().parent
MONTHLY_AUDIT = ROOT / "outputs" / "monthly_signal_audit.csv"
EPISODES = ROOT / "outputs" / "leading_market_transition_episodes.csv"
OUTPUT = ROOT / "outputs" / "confirmation_timing_audit.csv"
MARKET_FLAG = "滚动分位市场确认：4项至少2项"


def daily_close() -> pd.Series:
    frame = yf.download("^GSPC", start="2006-01-01", end="2023-01-01", interval="1d", auto_adjust=True, progress=False)
    values = frame["Close"]
    if isinstance(values, pd.DataFrame):
        values = values.iloc[:, 0]
    result = pd.to_numeric(values, errors="coerce").dropna().sort_index()
    result.index = pd.to_datetime(result.index).tz_localize(None)
    return result


def daily_vix() -> pd.Series:
    response = requests.get(
        "https://fred.stlouisfed.org/graph/fredgraph.csv",
        params={"id": "VIXCLS", "cosd": "2006-01-01"},
        timeout=25,
    )
    response.raise_for_status()
    frame = pd.read_csv(StringIO(response.text))
    result = pd.Series(
        pd.to_numeric(frame["VIXCLS"], errors="coerce").to_numpy(),
        index=pd.to_datetime(frame.iloc[:, 0]),
        name="vix",
    )
    return result.dropna().sort_index()


def asof_close(series: pd.Series, month: pd.Period) -> tuple[pd.Timestamp, float]:
    available = series[series.index <= month.to_timestamp(how="end")]
    if available.empty:
        raise ValueError(f"No price available by {month}")
    return available.index[-1], float(available.iloc[-1])


def first_crossing(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp, level: float) -> pd.Timestamp | pd.NaT:
    window = series[(series.index > start) & (series.index <= end)]
    hits = window[window <= level]
    return hits.index[0] if not hits.empty else pd.NaT


def main() -> None:
    close = daily_close()
    vix = daily_vix()
    daily = pd.DataFrame({"sp500": close}).join(vix, how="left")
    daily["momentum_63d"] = (daily["sp500"] / daily["sp500"].shift(63) - 1) * 100
    daily["gap_126d"] = (daily["sp500"] / daily["sp500"].rolling(126).max() - 1) * 100
    daily["three_market_flags"] = (
        (daily["momentum_63d"] <= -5).astype(int)
        + (daily["gap_126d"] <= -8).astype(int)
        + (daily["vix"] >= 25).astype(int)
    )
    daily["three_market_confirmation"] = daily["three_market_flags"] >= 2
    monthly = pd.read_csv(MONTHLY_AUDIT, index_col=0)
    monthly.index = pd.PeriodIndex(monthly.index, freq="M")
    episodes = pd.read_csv(EPISODES)
    cases = episodes[episodes["future_10pct_correction"]].copy()
    rows = []
    for _, case in cases.iterrows():
        onset_month = pd.Period(case["onset_month"], freq="M")
        onset_date, onset_price = asof_close(close, onset_month)
        horizon = onset_date + pd.DateOffset(months=6)
        first_10 = first_crossing(close, onset_date, horizon, onset_price * 0.9)
        first_5 = first_crossing(close, onset_date, horizon, onset_price * 0.95)

        possible = monthly.loc[onset_month : onset_month + 3, MARKET_FLAG]
        positives = possible[possible.eq(True)]
        confirmation_month = positives.index[0] if not positives.empty else None
        confirmation_date, confirmation_price = (
            asof_close(close, confirmation_month) if confirmation_month else (pd.NaT, np.nan)
        )
        reference_window = close.loc[onset_date - pd.DateOffset(months=6) : confirmation_date] if confirmation_month else pd.Series(dtype=float)
        reference_peak_date = reference_window.idxmax() if not reference_window.empty else pd.NaT
        reference_peak_price = float(reference_window.max()) if not reference_window.empty else np.nan
        first_5_from_peak = first_crossing(close, reference_peak_date, horizon, reference_peak_price * 0.95) if confirmation_month else pd.NaT
        first_10_from_peak = first_crossing(close, reference_peak_date, horizon, reference_peak_price * 0.90) if confirmation_month else pd.NaT
        candidate_daily = daily.loc[onset_date : onset_date + pd.DateOffset(months=3)]
        proxy_hits = candidate_daily.index[candidate_daily["three_market_confirmation"]]
        proxy_date = proxy_hits[0] if len(proxy_hits) else pd.NaT
        proxy_close = float(close.loc[proxy_date]) if pd.notna(proxy_date) else np.nan
        proxy_prior_peak = close.loc[proxy_date - pd.DateOffset(months=6) : proxy_date].max() if pd.notna(proxy_date) else np.nan
        prior_peak = close.loc[confirmation_date - pd.DateOffset(months=6) : confirmation_date].max() if confirmation_month else np.nan
        already_down_from_peak = (confirmation_price / prior_peak - 1) * 100 if confirmation_month else np.nan
        already_down_from_onset = (confirmation_price / onset_price - 1) * 100 if confirmation_month else np.nan
        future_prices = close[(close.index > confirmation_date) & (close.index <= horizon)] if confirmation_month else pd.Series(dtype=float)
        further_min_return = (future_prices.min() / confirmation_price - 1) * 100 if not future_prices.empty else np.nan
        rows.append({
            "onset_month": str(onset_month),
            "onset_date": onset_date.date().isoformat(),
            "first_confirmed_month_within_3m_window": str(confirmation_month) if confirmation_month else "",
            "first_confirmed_observable_date_within_3m_window": confirmation_date.date().isoformat() if confirmation_month else "",
            "days_from_onset_to_confirmation": (confirmation_date - onset_date).days if confirmation_month else np.nan,
            "first_5pct_drop_from_onset_date": first_5.date().isoformat() if pd.notna(first_5) else "",
            "first_10pct_drop_from_onset_date": first_10.date().isoformat() if pd.notna(first_10) else "",
            "days_confirmation_minus_first_5pct": (confirmation_date - first_5).days if pd.notna(first_5) and confirmation_month else np.nan,
            "days_confirmation_minus_first_10pct": (confirmation_date - first_10).days if pd.notna(first_10) and confirmation_month else np.nan,
            "at_confirmation_pct_from_prior_6m_peak": already_down_from_peak,
            "at_confirmation_pct_from_onset_close": already_down_from_onset,
            "reference_peak_date": reference_peak_date.date().isoformat() if pd.notna(reference_peak_date) else "",
            "first_5pct_from_reference_peak_date": first_5_from_peak.date().isoformat() if pd.notna(first_5_from_peak) else "",
            "first_10pct_from_reference_peak_date": first_10_from_peak.date().isoformat() if pd.notna(first_10_from_peak) else "",
            "days_confirmation_minus_peak_5pct": (confirmation_date - first_5_from_peak).days if pd.notna(first_5_from_peak) and confirmation_month else np.nan,
            "days_confirmation_minus_peak_10pct": (confirmation_date - first_10_from_peak).days if pd.notna(first_10_from_peak) and confirmation_month else np.nan,
            "further_min_return_after_confirmation_pct": further_min_return,
            "six_month_min_return_from_onset_daily_pct": (close[(close.index > onset_date) & (close.index <= horizon)].min() / onset_price - 1) * 100,
            "three_market_proxy_date_no_fsi": proxy_date.date().isoformat() if pd.notna(proxy_date) else "",
            "proxy_days_minus_first_5pct": (proxy_date - first_5).days if pd.notna(first_5) and pd.notna(proxy_date) else np.nan,
            "proxy_days_minus_first_10pct": (proxy_date - first_10).days if pd.notna(first_10) and pd.notna(proxy_date) else np.nan,
            "proxy_pct_from_prior_6m_peak": (proxy_close / proxy_prior_peak - 1) * 100 if pd.notna(proxy_date) else np.nan,
            "proxy_vix": daily.loc[proxy_date, "vix"] if pd.notna(proxy_date) else np.nan,
            "proxy_momentum_63d": daily.loc[proxy_date, "momentum_63d"] if pd.notna(proxy_date) else np.nan,
        })
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
