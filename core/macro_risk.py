"""Shared macro-market scoring logic used by the dashboard and factor page."""

from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_monthly(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    normalized = series.copy().dropna()
    normalized.index = pd.to_datetime(normalized.index).to_period("M")
    return normalized.groupby(level=0).last().sort_index()


def compute_macro_metrics(y10: pd.Series, y30: pd.Series, sp500: pd.Series) -> dict:
    """Score the four macro inputs with one auditable set of thresholds."""
    y10, y30, sp500 = map(normalize_monthly, (y10, y30, sp500))

    cur_y10 = float(y10.iloc[-1]) if not y10.empty else 0.0
    score1 = 0 if cur_y10 < 3 else 33 if cur_y10 < 4 else 67 if cur_y10 < 5 else 100
    grade1 = "SAFE" if score1 == 0 else "WATCH" if score1 == 33 else "WARNING" if score1 == 67 else "CRITICAL"

    chg3m = float(y10.iloc[-1] - y10.iloc[-4]) * 100 if len(y10) >= 4 else 0.0
    score2 = 0 if chg3m < 50 else 33 if chg3m < 100 else 67 if chg3m < 150 else 100
    grade2 = "SAFE" if score2 == 0 else "WATCH" if score2 == 33 else "WARNING" if score2 == 67 else "CRITICAL"

    common_yields = y30.index.intersection(y10.index)
    spread = float(y30.loc[common_yields[-1]] - y10.loc[common_yields[-1]]) * 100 if len(common_yields) else 20.0
    score3 = 0 if spread > 20 else 33 if spread > 0 else 67 if spread > -30 else 100
    grade3 = "SAFE" if score3 == 0 else "WATCH" if score3 == 33 else "WARNING" if score3 == 67 else "CRITICAL"

    corr_val = 0.0
    common_assets = y10.index.intersection(sp500.index)
    if len(common_assets) >= 12:
        y_aligned = y10.loc[common_assets].tail(12).diff().dropna()
        s_aligned = sp500.loc[common_assets].tail(12).pct_change().dropna()
        common_returns = y_aligned.index.intersection(s_aligned.index)
        if len(common_returns) >= 6:
            corr_val = float(np.corrcoef(y_aligned.loc[common_returns], s_aligned.loc[common_returns])[0, 1])
            if not np.isfinite(corr_val):
                corr_val = 0.0
    score4 = 0 if corr_val > -0.3 else 33 if corr_val > -0.5 else 67 if corr_val > -0.7 else 100
    grade4 = "SAFE" if score4 == 0 else "WATCH" if score4 == 33 else "WARNING" if score4 == 67 else "CRITICAL"

    composite = score1 * 0.15 + score2 * 0.40 + score3 * 0.25 + score4 * 0.20
    master_grade = "SAFE" if composite < 25 else "WATCH" if composite < 50 else "WARNING" if composite < 75 else "CRITICAL"
    return {
        "y10_level": {"value": cur_y10, "grade": grade1, "score": score1, "unit": "%"},
        "y10_momentum": {"value": chg3m, "grade": grade2, "score": score2, "unit": "bps/3M"},
        "spread": {"value": spread, "grade": grade3, "score": score3, "unit": "bps"},
        "correlation": {"value": corr_val, "grade": grade4, "score": score4, "unit": "r"},
        "composite": {"score": round(composite, 1), "grade": master_grade},
    }
