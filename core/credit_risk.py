"""Auditable AI credit and refinancing pressure scoring.

The model separates broad credit pricing, real borrowing costs, system-wide
financial conditions, and issuer-specific AI financing evidence. Missing
components are excluded and never treated as SAFE.
"""

from __future__ import annotations

import pandas as pd


COMPONENTS = {
    "credit_spread": {"label": "高收益信用利差", "weight": 0.35, "unit": "bp"},
    "real_rate": {"label": "10Y实际利率", "weight": 0.30, "unit": "%"},
    "financial_conditions": {"label": "NFCI金融条件", "weight": 0.25, "unit": ""},
    "ai_deal": {"label": "AI融资交易温度", "weight": 0.10, "unit": ""},
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


def state_for(score: float | None) -> str:
    if score is None:
        return "N/A"
    if score < 25:
        return "SAFE"
    if score < 50:
        return "WATCH"
    if score < 75:
        return "WARNING"
    return "CRITICAL"


def _ascending(value: float, safe: float, watch: float, warning: float) -> int:
    if value < safe:
        return 0
    if value < watch:
        return 33
    if value < warning:
        return 67
    return 100


def _component(value: float, change: float | None, level_score: int, change_score: int | None,
               *, level_weight: float, unit: str) -> dict:
    if change_score is None:
        score = float(level_score)
    else:
        score = level_score * level_weight + change_score * (1 - level_weight)
    return {
        "value": round(float(value), 3),
        "change": None if change is None else round(float(change), 3),
        "score": round(score, 1),
        "grade": state_for(score),
        "unit": unit,
    }


def compute_credit_metrics(
    hy_oas: pd.Series,
    real_yield: pd.Series,
    nfci: pd.Series,
    *,
    baa_spread: pd.Series | None = None,
    ai_deal_score: float | None = None,
) -> dict:
    """Compute CFRI from source series available at the selected observation date.

    HY OAS is preferred for live monitoring. BAA10Y is used only as an
    explicitly labelled long-history proxy when HY OAS is unavailable.
    """
    hy_oas = normalize_monthly(hy_oas)
    real_yield = normalize_monthly(real_yield)
    nfci = normalize_monthly(nfci)
    baa_spread = normalize_monthly(baa_spread)
    result: dict[str, dict] = {}

    credit_series = hy_oas
    proxy = "HY OAS"
    if credit_series.empty and not baa_spread.empty:
        credit_series = baa_spread
        proxy = "BAA10Y长期代理"
    if not credit_series.empty:
        value_bp = float(credit_series.iloc[-1]) * 100
        change_bp = float(credit_series.iloc[-1] - credit_series.iloc[-4]) * 100 if len(credit_series) >= 4 else None
        if proxy == "HY OAS":
            level_score = _ascending(value_bp, 350, 500, 750)
        else:
            level_score = _ascending(value_bp, 200, 300, 450)
        change_score = None if change_bp is None else _ascending(change_bp, 50, 100, 200)
        result["credit_spread"] = _component(
            value_bp, change_bp, level_score, change_score,
            level_weight=0.60, unit="bp",
        )
        result["credit_spread"]["proxy"] = proxy

    if not real_yield.empty:
        value = float(real_yield.iloc[-1])
        change_bp = float(real_yield.iloc[-1] - real_yield.iloc[-4]) * 100 if len(real_yield) >= 4 else None
        level_score = _ascending(value, 1.0, 2.0, 3.0)
        change_score = None if change_bp is None else _ascending(change_bp, 25, 50, 100)
        result["real_rate"] = _component(
            value, change_bp, level_score, change_score,
            level_weight=0.70, unit="%",
        )

    if not nfci.empty:
        value = float(nfci.iloc[-1])
        change = float(nfci.iloc[-1] - nfci.iloc[-4]) if len(nfci) >= 4 else None
        level_score = _ascending(value, -0.39, 0.0, 0.5)
        change_score = None if change is None else _ascending(change, 0.0, 0.15, 0.35)
        result["financial_conditions"] = _component(
            value, change, level_score, change_score,
            level_weight=0.60, unit="",
        )

    if ai_deal_score is not None:
        bounded = max(0.0, min(100.0, float(ai_deal_score)))
        result["ai_deal"] = {
            "value": bounded,
            "change": None,
            "score": round(bounded, 1),
            "grade": state_for(bounded),
            "unit": "",
        }

    available_weight = sum(COMPONENTS[key]["weight"] for key in result)
    if available_weight < 0.75:
        result["composite"] = {
            "score": None,
            "grade": "N/A",
            "coverage": round(available_weight * 100),
        }
        return result
    score = sum(result[key]["score"] * COMPONENTS[key]["weight"] for key in result) / available_weight
    result["composite"] = {
        "score": round(score, 1),
        "grade": state_for(score),
        "coverage": round(available_weight * 100),
    }
    return result
