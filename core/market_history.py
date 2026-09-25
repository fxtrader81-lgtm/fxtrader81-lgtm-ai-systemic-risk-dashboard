"""Retrospective event-month market confirmation, never an ex-ante forecast."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.macro_risk import COMPONENTS, compute_macro_metrics
from core.transmission_phase import market_phase_from_series


def event_validation_scope(kind: str) -> str:
    """Keep boundary cases visible without counting them as model hits or misses."""
    if kind == "外生冲击":
        return "模型边界：外生冲击"
    if kind == "周期底部":
        return "不纳入风险预警验证：市场底部"
    return "机制案例；不等于独立验证样本"


def build_history_rows(
    stress: dict[str, pd.Series], events: list[tuple[str, str, str, str]]
) -> list[dict]:
    """Reconstruct each event-month state using observations through that month.

    This is an ex-post reconstruction using the latest data vintage. It does
    not assert that revised stress-series values were available in real time.
    """
    rows = []
    sp500 = stress["sp500"]
    y10 = stress["y10"]
    for month, event, description, kind in events:
        event_end = pd.Period(month, freq="M").to_timestamp("M")
        history = {
            key: values[pd.to_datetime(values.index) <= event_end] if not values.empty else values
            for key, values in stress.items()
        }
        base = {
            "month": month,
            "event": event,
            "description": description,
            "kind": kind,
            "scope": event_validation_scope(kind),
        }
        if history["y10"].empty or history["sp500"].empty:
            rows.append({**base, "available": False, "score": None, "state": "N/A"})
            continue

        metrics = compute_macro_metrics(
            history["y10"], history["y3m"], history["sp500"],
            history["stlfsi"], history["vix"],
        )
        # Subsequent peak-to-trough drawdown is an observed outcome, not input
        # to the event-month confirmation score.
        outcome_end = (pd.Period(month, freq="M") + 6).to_timestamp("M")
        event_window = sp500[(sp500.index >= event_end) & (sp500.index <= outcome_end)]
        drawdown = float((event_window / event_window.cummax() - 1).min()) if not event_window.empty else np.nan
        phase = market_phase_from_series(history)
        components = []
        for key, definition in COMPONENTS.items():
            if key not in metrics:
                components.append(f'{definition["label"]} N/A（未计入）')
                continue
            item = metrics[key]
            raw = f'{item["value"]:.2f}{item["unit"]}' if key in {"equity_drawdown", "volatility"} else f'{item["value"]:+.2f}{item["unit"]}'
            contribution = item["score"] * definition["weight"]
            components.append(f'{definition["label"]} {raw} → {item["score"]}/100 ×{definition["weight"]:.2f} = {contribution:.1f}')
        composite = metrics["composite"]
        if composite["score"] is None:
            components.append("汇总：有效权重不足，未生成评分")
        else:
            components.append(
                f'汇总：主触发 {composite["dominant"]:.0f} ×0.65 + '
                f'压力广度 {composite["breadth"]:.1f} ×0.35 = {composite["score"]:.1f}'
            )
        y10_at_event = y10[pd.to_datetime(y10.index) <= event_end]
        rows.append({
            **base,
            "available": composite["score"] is not None,
            "as_of": month,
            "y10": f'{float(y10_at_event.iloc[-1]):.2f}%' if not y10_at_event.empty else "N/A",
            "drawdown": "N/A" if np.isnan(drawdown) else f"{drawdown:.0%}",
            "summary": (
                f'{description} 按事件月末后6个月的月末点位计算，标普500最大峰谷回撤为{drawdown:.0%}。'
                if not np.isnan(drawdown) else description
            ),
            "score": composite["score"],
            "state": composite["grade"],
            "phase": phase["label"],
            "coverage": composite["coverage"],
            "components": " · ".join(components),
        })
    return rows
