"""Auditable cross-market confirmation scoring shared by the market dashboard."""

from __future__ import annotations

import pandas as pd


COMPONENTS = {
    "equity_momentum": {"label": "标普500三个月收益", "weight": 0.30, "unit": "%"},
    "equity_drawdown": {"label": "标普500距六个月高点", "weight": 0.20, "unit": "%"},
    "volatility": {"label": "VIX波动率", "weight": 0.20, "unit": ""},
    "rate_shock": {"label": "10Y收益率三个月变化", "weight": 0.15, "unit": "bp"},
    "financial_stress": {"label": "金融市场压力 STLFSI", "weight": 0.10, "unit": ""},
    "curve": {"label": "10Y−3M期限利差", "weight": 0.05, "unit": "bp"},
}


def normalize_monthly(series: pd.Series | None) -> pd.Series:
    if series is None or series.empty:
        return pd.Series(dtype=float)
    normalized = pd.to_numeric(series, errors="coerce").dropna()
    if isinstance(normalized.index, pd.PeriodIndex):
        normalized.index = normalized.index.asfreq("M")
    else:
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
    vix: pd.Series | None = None,
) -> dict:
    """Score observed cross-market confirmation signals.

    Credit spreads, real yields and NFCI belong to factor 06 and deliberately do
    not enter this score. Missing signals are excluded and never treated as safe.
    """
    y10, y3m, sp500, stlfsi, vix = map(normalize_monthly, (y10, y3m, sp500, stlfsi, vix))
    result: dict[str, dict] = {}
    if len(sp500) >= 4:
        value = float(sp500.iloc[-1] / sp500.iloc[-4] - 1) * 100
        result["equity_momentum"] = _item(value, _falling(value, 0.0, -5.0, -12.0), "%")
    if len(sp500) >= 2:
        window = sp500.iloc[-6:]
        value = float(window.iloc[-1] / window.max() - 1) * 100
        result["equity_drawdown"] = _item(value, _falling(value, -3.0, -8.0, -15.0), "%")
    if not vix.empty:
        value = float(vix.iloc[-1])
        result["volatility"] = _item(value, _ascending(value, 20.0, 25.0, 35.0), "")
    if len(y10) >= 4:
        value = float(y10.iloc[-1] - y10.iloc[-4]) * 100
        result["rate_shock"] = _item(value, _ascending(value, 40.0, 80.0, 140.0), "bp")
    if not stlfsi.empty:
        value = float(stlfsi.iloc[-1])
        result["financial_stress"] = _item(value, _ascending(value, 0.0, 0.32, 0.83), "")
    common = y10.index.intersection(y3m.index)
    if len(common):
        value = float(y10.loc[common[-1]] - y3m.loc[common[-1]]) * 100
        result["curve"] = _item(value, _falling(value, 30.0, 0.0, -50.0), "bp")

    available_weight = sum(COMPONENTS[key]["weight"] for key in result)
    if available_weight < 0.65:
        result["composite"] = {"score": None, "grade": "N/A", "coverage": round(available_weight * 100)}
        return result
    breadth = sum(item["score"] * COMPONENTS[key]["weight"] for key, item in result.items()) / available_weight
    primary_scores = [result[key]["score"] for key in COMPONENTS if key != "curve" and key in result]
    dominant = max(primary_scores) if primary_scores else 0
    composite = dominant * 0.65 + breadth * 0.35
    result["composite"] = {
        "score": round(composite, 1),
        "grade": _grade(composite),
        "coverage": round(available_weight * 100),
        "dominant": dominant,
        "breadth": round(breadth, 1),
    }
    return result
