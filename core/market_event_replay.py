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
            prior_six_months = prior[prior.index >= anchor_date - pd.DateOffset(months=6)]
        else:
            baseline, baseline_date, event_window = np.nan, None, pd.Series(dtype=float)
            prior_six_months = pd.Series(dtype=float)

        def outcome(segment: pd.Series) -> tuple[str, str, str]:
            if segment.empty or not np.isfinite(baseline):
                return "N/A", "N/A", "N/A"
            low_date = segment.idxmin()
            loss = min(0.0, float(segment.loc[low_date] / baseline - 1))
            if loss == 0:
                return "0%", "—", "—"
            loss_text = f"{loss:.2%}"
            return loss_text, low_date.strftime("%Y-%m-%d"), str((low_date - anchor_date).days)

        drawdown_text, drawdown_date, drawdown_days = outcome(event_window)
        if drawdown_text not in {"N/A", "0%"}:
            trough_date = pd.Timestamp(drawdown_date)
            trough_close = float(event_window.loc[trough_date])
            recovered_after_trough = event_window[
                (event_window.index > trough_date) & (event_window >= baseline)
            ]
            recovery_after_trough = recovered_after_trough.index[0] if not recovered_after_trough.empty else None
            recovery_duration = (
                f"{(recovery_after_trough - anchor_date).days}天"
                if recovery_after_trough is not None else "六个月内未收复"
            )
            drawdown_formula = f"{trough_close:,.2f} ÷ {baseline:,.2f} − 1 = {drawdown_text}"
        else:
            recovery_after_trough = None
            recovery_duration = "未跌破基准" if drawdown_text == "0%" else "N/A"
            drawdown_formula = "未跌破基准，记0%" if drawdown_text == "0%" else "日收盘数据不足"
        first_breach_date = None
        first_breach_session = None
        if not event_window.empty and np.isfinite(baseline):
            first_breach = event_window[event_window < baseline]
            if first_breach.empty:
                recovery_date, initial_window = None, pd.Series(dtype=float)
            else:
                first_breach_date = first_breach.index[0]
                first_breach_session = int(event_window.index.get_loc(first_breach_date)) + 1
                recovered = event_window[(event_window.index > first_breach_date) & (event_window >= baseline)]
                recovery_date = recovered.index[0] if not recovered.empty else None
                initial_window = event_window[event_window.index >= first_breach_date]
                if recovery_date is not None:
                    initial_window = initial_window[initial_window.index < recovery_date]
        else:
            recovery_date, initial_window = None, pd.Series(dtype=float)
        initial_text, initial_date, initial_days = outcome(initial_window)
        if not event_window.empty and np.isfinite(baseline) and first_breach.empty:
            initial_text, initial_date, initial_days = "0%", "—", "—"

        if first_breach_date is None:
            breach_timing = "未跌破事前基准" if not event_window.empty and np.isfinite(baseline) else "N/A"
            first_underwater_days = "—"
        else:
            # These are descriptive buckets, not an estimate of causal impact.
            timing = "短期观察窗" if first_breach_session <= 5 else (
                "传导观察窗" if first_breach_session <= 20 else "较晚出现，不能直接归因于该事件"
            )
            breach_timing = f"观察日后第{first_breach_session}个有数据交易日（{timing}）"
            first_underwater_days = (
                f"{(recovery_date - first_breach_date).days}个自然日后收复"
                if recovery_date is not None else
                f"截至{event_window.index[-1]:%Y-%m-%d}已持续{(event_window.index[-1] - first_breach_date).days}个自然日，仍未收复"
            )
        later_episode = recovery_date is not None and drawdown_date not in {"N/A", "—"} and pd.Timestamp(drawdown_date) > recovery_date
        if not prior_six_months.empty and not event_window.empty:
            prior_peak_date = prior_six_months.idxmax()
            prior_peak_close = float(prior_six_months.loc[prior_peak_date])
            higher = event_window[event_window > prior_peak_close]
            new_high_date = higher.index[0] if not higher.empty else None
            new_high_status = (
                f"曾于{new_high_date:%Y-%m-%d}超过事前六个月最高收盘"
                if new_high_date is not None else "未超过事前六个月最高收盘"
            )
        else:
            prior_peak_date, prior_peak_close, new_high_date = None, np.nan, None
            new_high_status = "N/A"

        if event_window.empty or not np.isfinite(baseline):
            window_end_date, window_end_close, window_end_return = "N/A", "N/A", "N/A"
            window_end_label = "观察期末"
            path_summary = f"{description}缺少事前基准或后续日收盘价，无法计算事件后六个月的跌幅和期末位置。"
            hover_summary = "事前基准或后续日收盘数据不足，无法计算六个月市场路径。"
        else:
            last_date = event_window.index[-1]
            last_close = float(event_window.iloc[-1])
            window_end_date = last_date.strftime("%Y-%m-%d")
            window_end_close = f"{last_close:,.2f}"
            window_end_return = f"{last_close / baseline - 1:+.2%}"
            complete_window = outcome_end - last_date <= pd.Timedelta(days=7)
            window_end_label = "六个月观察期最后交易日" if complete_window else "最后可用交易日"
            end_position = (
                f"高于基准{last_close / baseline - 1:.2%}" if last_close > baseline
                else f"低于基准{1 - last_close / baseline:.2%}" if last_close < baseline
                else "恰好回到基准"
            )
            baseline_story = (
                f"以{event_date}为观察日，前一交易日{baseline_date:%Y-%m-%d}"
                f"标普500收于{baseline:,.2f}点，作为固定基准。"
            )
            end_story = f"{window_end_label}{window_end_date}收于{window_end_close}点，{end_position}。"
            if drawdown_text == "0%":
                path_summary = f"{description}{baseline_story}观察窗口内没有一天收盘跌破该基准；{new_high_status}。{end_story}"
                hover_summary = f"事前基准{baseline:,.2f}点（{baseline_date:%Y-%m-%d}）<br>观察期内未跌破基准；{new_high_status}<br>{window_end_label}{window_end_date}：{window_end_close}点，{end_position}"
            else:
                recovery_story = (
                    f"首次跌破发生于{first_breach_date:%Y-%m-%d}，{breach_timing}；"
                    + f"首轮低于基准状态：{first_underwater_days}；"
                    + f"首轮最深跌幅{initial_text}。"
                )
                if later_episode:
                    recovery_story += "六个月最低点出现在首次收复之后，属于后续另一段下跌，不能自动归因于原事件。"
                elif recovery_after_trough is None:
                    recovery_story += "六个月最低点之后在观察期内未重新收复基准。"
                recovery_story += f"{new_high_status}。"
                path_summary = (
                    f"{description}{baseline_story}观察日后第{drawdown_days}个自然日"
                    f"（{drawdown_date}）收于{trough_close:,.2f}点，"
                    f"为随后六个月的最低日收盘，较事前基准下跌{abs(trough_close / baseline - 1):.2%}（{drawdown_text}）。"
                    f"{recovery_story}{end_story}"
                )
                hover_summary = (
                    f"事前基准{baseline:,.2f}点（{baseline_date:%Y-%m-%d}）<br>"
                    f"第{drawdown_days}个自然日触及六个月最低收盘{trough_close:,.2f}点，"
                    f"相对基准{drawdown_text}<br>"
                    f"首次跌破：{first_breach_date:%Y-%m-%d}（{breach_timing}）；"
                    f"首次收复：{recovery_date.strftime('%Y-%m-%d') if recovery_date is not None else '观察期内未收复'}<br>"
                    f"{new_high_status}；{window_end_label}{window_end_date}：{window_end_close}点，{end_position}"
                )
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
            "drawdown_formula": drawdown_formula,
            "recovery_after_trough_date": recovery_after_trough.strftime("%Y-%m-%d") if recovery_after_trough is not None else "—",
            "recovery_duration": recovery_duration,
            "window_end_date": window_end_date,
            "window_end_close": window_end_close,
            "window_end_return": window_end_return,
            "window_end_label": window_end_label,
            "hover_summary": hover_summary,
            "initial_drawdown": initial_text,
            "initial_drawdown_date": initial_date,
            "initial_drawdown_days": initial_days,
            "first_breach_date": first_breach_date.strftime("%Y-%m-%d") if first_breach_date is not None else "—",
            "first_breach_session": first_breach_session,
            "breach_timing": breach_timing,
            "first_underwater_days": first_underwater_days,
            "later_episode": later_episode,
            "prior_peak_date": prior_peak_date.strftime("%Y-%m-%d") if prior_peak_date is not None else "N/A",
            "prior_peak_close": f"{prior_peak_close:,.2f}" if np.isfinite(prior_peak_close) else "N/A",
            "new_high_date": new_high_date.strftime("%Y-%m-%d") if new_high_date is not None else "—",
            "new_high_status": new_high_status,
            "event_date": event_date if anchor_date is not None else "N/A",
            "baseline_date": baseline_date.strftime("%Y-%m-%d") if baseline_date is not None else "N/A",
            "baseline_close": f"{baseline:,.2f}" if np.isfinite(baseline) else "N/A",
            "recovery_date": recovery_date.strftime("%Y-%m-%d") if recovery_date is not None else "未恢复",
            "summary": path_summary,
            "score": composite["score"],
            "state": composite["grade"],
            "coverage": composite["coverage"],
            "components": " · ".join(components),
        })
    return rows
