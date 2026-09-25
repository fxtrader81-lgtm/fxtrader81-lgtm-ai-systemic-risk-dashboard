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
    for event_date, event, description, kind in events:
        month = event_date[:7]
        anchor_date = pd.Timestamp(event_date) if len(event_date) == 10 else None
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
            sp500_daily[sp500_daily.index <= event_end] if sp500_daily is not None else None,
        )
        # Outcomes use the actual event/observation date, never a synthetic
        # first-of-month or event-month-end baseline. Neither feeds the score.
        daily = sp500_daily if sp500_daily is not None else pd.Series(dtype=float)
        if not daily.empty and anchor_date is not None:
            daily = daily.copy()
            daily.index = pd.to_datetime(daily.index).tz_localize(None)
            daily = pd.to_numeric(daily, errors="coerce").dropna().sort_index()
            prior = daily[daily.index < anchor_date]
            baseline = float(prior.iloc[-1]) if not prior.empty else np.nan
            baseline_date = prior.index[-1] if not prior.empty else None
            outcome_end = anchor_date + pd.DateOffset(months=6)
            event_window = daily[(daily.index >= anchor_date) & (daily.index <= outcome_end)]
        else:
            baseline, baseline_date, event_window = np.nan, None, pd.Series(dtype=float)

        def outcome(segment: pd.Series) -> tuple[str, str, str]:
            if segment.empty or not np.isfinite(baseline):
                return "N/A", "N/A", "N/A"
            low_date = segment.idxmin()
            loss = min(0.0, float(segment.loc[low_date] / baseline - 1))
            loss_text = "0%" if loss == 0 else f"{loss:.2%}"
            return loss_text, low_date.strftime("%Y-%m-%d"), str((low_date - anchor_date).days)

        drawdown_text, drawdown_date, drawdown_days = outcome(event_window)
        if not event_window.empty and np.isfinite(baseline):
            recovered = event_window[event_window >= baseline]
            recovery_date = recovered.index[0] if not recovered.empty else None
            initial_window = event_window[event_window.index < recovery_date] if recovery_date is not None else event_window
        else:
            recovery_date, initial_window = None, pd.Series(dtype=float)
        initial_text, initial_date, initial_days = outcome(initial_window)
        if recovery_date is not None and initial_window.empty:
            initial_text, initial_date, initial_days = "0%", "—", "—"
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
            "drawdown_date": drawdown_date,
            "drawdown_days": drawdown_days,
            "initial_drawdown": initial_text,
            "initial_drawdown_date": initial_date,
            "initial_drawdown_days": initial_days,
            "event_date": event_date if anchor_date is not None else "N/A",
            "baseline_date": baseline_date.strftime("%Y-%m-%d") if baseline_date is not None else "N/A",
            "baseline_close": f"{baseline:,.2f}" if np.isfinite(baseline) else "N/A",
            "recovery_date": recovery_date.strftime("%Y-%m-%d") if recovery_date is not None else "未恢复",
            "summary": (
                f'{description} 以观察日前一交易日收盘价为基准，六个月内相对基准最大跌幅'
                f'{drawdown_text}（第{drawdown_days}天）；首次恢复前跌幅{initial_text}'
                f'{f"（第{initial_days}天）" if initial_days != "—" else ""}。'
                if drawdown_text != "N/A" else description
            ),
            "score": composite["score"],
            "state": composite["grade"],
            "coverage": composite["coverage"],
            "components": " · ".join(components),
        })
    return rows
