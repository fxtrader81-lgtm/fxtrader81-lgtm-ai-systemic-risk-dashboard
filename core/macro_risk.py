"""Auditable macro-market stress scoring shared by the dashboard and factor 06."""

from __future__ import annotations

import pandas as pd


COMPONENTS = {
    "financial_stress": {"label": "金融压力 STLFSI", "weight": 0.30, "unit": ""},
    "credit_impulse": {"label": "信用利差三个月变化", "weight": 0.25, "unit": "bps/3M"},
    "conditions_momentum": {"label": "金融条件三个月变化", "weight": 0.20, "unit": ""},
    "equity_momentum": {"label": "标普500三个月收益", "weight": 0.20, "unit": "%/3M"},
    "curve": {"label": "10Y−3M期限利差", "weight": 0.05, "unit": "bps"},
}


def normalize_monthly(series: pd.Series | None) -> pd.Series:
    if series is None or series.empty:
        return pd.Series(dtype=float)
    normalized = pd.to_numeric(series, errors="coerce").dropna()
    normalized.index = pd.to_datetime(normalized.index).to_period("M")
    return normalized.groupby(level=0).last().sort_index()


def _grade(score: float) -> str:
    return "SAFE" if score < 25 else "WATCH" if score < 50 else "WARNING" if score < 75 else "CRITICAL"


def _ascending(value: float, watch: float, warning: float, critical: float) -> int:
    if value <= watch:
        return 0
    if value <= warning:
        return 33
    if value <= critical:
        return 67
    return 100


def _falling(value: float, watch: float, warning: float, critical: float) -> int:
    if value >= watch:
        return 0
    if value >= warning:
        return 33
    if value >= critical:
        return 67
    return 100


def _item(value: float, score: int, unit: str) -> dict:
    return {"value": round(float(value), 3), "score": score, "grade": _grade(score), "unit": unit}


def compute_macro_metrics(
    y10: pd.Series,
    y3m: pd.Series,
    sp500: pd.Series,
    stlfsi: pd.Series,
    baa10y: pd.Series,
    nfci: pd.Series,
) -> dict:
    """Calculate a five-signal market-stress score from observed monthly series.

    Missing signals are excluded and weights are renormalized; they are never
    scored as safe. Cut points come from the historical analysis discussed for
    this dashboard, rather than being assigned to individual events.
    """
    y10, y3m, sp500, stlfsi, baa10y, nfci = map(
        normalize_monthly, (y10, y3m, sp500, stlfsi, baa10y, nfci)
    )
    result: dict[str, dict] = {}
    if not stlfsi.empty:
        value = float(stlfsi.iloc[-1])
        result["financial_stress"] = _item(value, _ascending(value, 0.0, 0.32, 0.83), "")
    if len(baa10y) >= 4:
        value = float(baa10y.iloc[-1] - baa10y.iloc[-4]) * 100
        result["credit_impulse"] = _item(value, _ascending(value, 0.0, 14.0, 38.0), "bps/3M")
    if len(nfci) >= 4:
        value = float(nfci.iloc[-1] - nfci.iloc[-4])
        result["conditions_momentum"] = _item(value, _ascending(value, 0.0, 0.071, 0.184), "")
    if len(sp500) >= 4:
        value = float(sp500.iloc[-1] / sp500.iloc[-4] - 1) * 100
        result["equity_momentum"] = _item(value, _falling(value, 0.0, -1.52, -7.9), "%/3M")
    common = y10.index.intersection(y3m.index)
    if len(common):
        value = float(y10.loc[common[-1]] - y3m.loc[common[-1]]) * 100
        result["curve"] = _item(value, _falling(value, 30.0, 0.0, -50.0), "bps")

    available_weight = sum(COMPONENTS[key]["weight"] for key in result)
    if available_weight < 0.65:
        result["composite"] = {"score": None, "grade": "N/A", "coverage": round(available_weight * 100)}
        return result
    breadth = sum(item["score"] * COMPONENTS[key]["weight"] for key, item in result.items()) / available_weight
    # Different crises are led by different signals. A plain weighted mean hid a
    # strong credit or stress trigger behind several calm readings. Use the
    # strongest primary trigger for early warning, while retaining breadth as a
    # confirmation term. The low-weight curve is context, never the sole trigger.
    primary_scores = [result[key]["score"] for key in COMPONENTS if key != "curve" and key in result]
    dominant = max(primary_scores) if primary_scores else 0
    composite = dominant * 0.75 + breadth * 0.25
    result["composite"] = {
        "score": round(composite, 1),
        "grade": _grade(composite),
        "coverage": round(available_weight * 100),
        "dominant": dominant,
        "breadth": round(breadth, 1),
    }
    return result
