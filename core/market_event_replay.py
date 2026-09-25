"""Retrospective event-month market confirmation, never an ex-ante forecast."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.macro_risk import COMPONENTS, compute_macro_metrics


def event_validation_scope(kind: str) -> str:
    """Keep boundary cases visible without counting them as model hits or misses."""
    if kind == "外生冲击":
        return "模型边界：外生冲击"
    if kind == "周期底部":
        return "不纳入风险预警验证：市场底部"
    return "机制案例；不等于独立验证样本"


def build_history_rows(
    stress: dict[str, pd.Series], events: list[tuple[str, str, str, str]],
    sp500_daily: pd.Series | None = None,
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
        # Compare the event-month closing baseline with the lowest daily close
        # in the following six calendar months. This outcome is not a score input.
        outcome_end = (pd.Period(month, freq="M") + 6).to_timestamp("M")
        daily = sp500_daily if sp500_daily is not None else pd.Series(dtype=float)
        if not daily.empty:
            daily = daily.copy()
            daily.index = pd.to_datetime(daily.index).tz_localize(None)
            baseline_observations = daily[daily.index <= event_end]
            baseline_month = baseline_observations[baseline_observations.index.to_period("M") == pd.Period(month)]
            baseline = float(baseline_month.iloc[-1]) if not baseline_month.empty else np.nan
            event_window = daily[(daily.index > event_end) & (daily.index <= outcome_end)]
        else:
            baseline, event_window = np.nan, pd.Series(dtype=float)
        drawdown = (
            float(min(0.0, (event_window / baseline - 1).min()))
            if not event_window.empty and np.isfinite(baseline) else np.nan
        )
        drawdown_text = "N/A" if np.isnan(drawdown) else "0%" if drawdown == 0 else f"{drawdown:.2%}"
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
            "drawdown": drawdown_text,
            "summary": (
                f'{description} 以事件月最后交易日收盘价为基准，随后六个月内最低日收盘价对应回撤为{drawdown_text}。'
                if not np.isnan(drawdown) else description
            ),
            "score": composite["score"],
            "state": composite["grade"],
            "coverage": composite["coverage"],
            "components": " · ".join(components),
        })
    return rows
