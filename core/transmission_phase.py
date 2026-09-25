"""Exploratory, observable stages of market transmission.

These stages describe a current snapshot and recent market history. They do
not claim that a future correction will occur or assign a probability to it.
"""

from __future__ import annotations

import pandas as pd

from core.macro_risk import compute_macro_metrics, normalize_monthly


RANK = {"N/A": -1, "SAFE": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}


def recent_market_grades(series: dict[str, pd.Series], months: int = 3) -> list[str]:
    """Return completed prior-month grades, using only data through each month."""
    normalized = {key: normalize_monthly(series.get(key)) for key in ("y10", "y3m", "sp500", "stlfsi", "vix")}
    sp500 = normalized["sp500"]
    if sp500.empty:
        return []
    observations = list(sp500.index[-(months + 1):-1])
    grades = []
    for month in observations:
        inputs = {key: values[values.index <= month] for key, values in normalized.items()}
        grades.append(compute_macro_metrics(**inputs)["composite"]["grade"])
    return grades


def market_phase(market_state: str, *, prior_grades: list[str] | None = None,
                 equity_momentum: float | None = None, vix_change: float | None = None,
                 stress: float | None = None) -> dict:
    """Classify the *observed* market leg without inventing new score cutoffs."""
    prior_grades = prior_grades or []
    if market_state == "N/A":
        return {"key": "unavailable", "label": "数据不足", "detail": "缺少足够的市场数据，不能判断传导阶段。"}
    was_stressed = any(RANK.get(grade, -1) >= 2 for grade in prior_grades)
    recovering = (was_stressed and market_state == "SAFE"
                  and equity_momentum is not None and equity_momentum >= 0
                  and vix_change is not None and vix_change < 0
                  and stress is not None and stress <= 0)
    if recovering:
        return {"key": "dissipating", "label": "压力消退中", "detail": "近三个月曾有显著市场压力；目前股市动量转正、VIX回落且金融压力不高于零。"}
    if RANK[market_state] >= 2:
        return {"key": "release", "label": "风险释放中", "detail": "多项市场指标已明显恶化；这是事中识别，不是下跌前预测。"}
    if market_state == "WATCH":
        return {"key": "transmitting", "label": "初步传导", "detail": "市场出现初步压力，尚未达到广泛恶化。"}
    return {"key": "quiet", "label": "尚未市场传导", "detail": "当前市场指标未形成确认；不能据此排除突发冲击。"}


def market_phase_from_series(series: dict[str, pd.Series]) -> dict:
    """Evaluate the market phase from the same snapshot used by factor 07."""
    metrics = compute_macro_metrics(
        series["y10"], series["y3m"], series["sp500"], series["stlfsi"], series["vix"],
    )
    vix = normalize_monthly(series.get("vix"))
    stress = normalize_monthly(series.get("stlfsi"))
    momentum = metrics.get("equity_momentum", {}).get("value")
    return market_phase(
        metrics["composite"]["grade"],
        prior_grades=recent_market_grades(series),
        equity_momentum=momentum,
        vix_change=float(vix.iloc[-1] - vix.iloc[-2]) if len(vix) >= 2 else None,
        stress=float(stress.iloc[-1]) if not stress.empty else None,
    )


def system_phase(structure_state: str, credit_state: str, market: dict) -> dict:
    """Join structural fragility, credit trigger and observed market leg."""
    market_key = market["key"]
    if "N/A" in (structure_state, credit_state) or market_key == "unavailable":
        return {"key": "unavailable", "label": "数据不足，无法判断联动", "nodes": (False, False, False, False)}
    structure = RANK[structure_state] >= 2
    credit = RANK[credit_state] >= 2
    market_on = market_key in ("transmitting", "release")
    release = market_key == "release"
    nodes = (structure, credit, market_on, release)
    if market_key == "dissipating":
        label = "市场压力消退中" if structure and credit else "宏观压力消退，AI链未确认"
    elif structure and credit and release:
        label = "风险释放中 · CASCADE 联动"
    elif structure and credit and market_on:
        label = "开始传导 · CASCADE 联动"
    elif structure and credit:
        label = "融资压力抬升，市场尚未确认"
    elif structure and market_on:
        label = "结构风险高，市场承压但信贷未确认"
    elif structure:
        label = "结构性积累期，尚未市场传导"
    elif market_on:
        label = "宏观压力，AI体系暂未确认联动"
    elif credit:
        label = "外部信贷压力，AI结构尚未共振"
    else:
        label = "常态监测"
    return {"key": market_key, "label": label, "nodes": nodes}
