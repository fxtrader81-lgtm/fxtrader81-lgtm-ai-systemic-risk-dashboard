"""Quarterly page snapshots for Factor 03 (data-center asset obsolescence)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from core.quarterly_history import calculate_score, component, load_history as _load_history, quarter_for, state_for


CONFIG = Path(__file__).resolve().parents[1] / "config/data_center_quarterly_history.json"
WEIGHTS = {
    "aof": 0.25,
    "reit_pressure": 0.35,
    "liquid_cooling": 0.25,
    "power_infrastructure": 0.15,
}


def _market_period(snapshot):
    dates = "/".join(f"{row.get('ticker')} {row.get('price_date', '未知')}" for row in snapshot.get("rows", []))
    return f"价格{dates}；采集{snapshot.get('checked_at', '未知')}"


def make_current_snapshot(aof, reit, liquid, power, today=None):
    today = today or date.today()
    aof_metrics = aof.get("metrics", {})
    reit_metrics = reit.get("metrics") or {}
    liquid_metrics = liquid.get("metrics") or {}
    power_metrics = power.get("metrics") or {}
    reference = aof.get("reference", {})
    components = [
        component(
            "aof", "AOF机柜适配压力", aof_metrics.get("score"),
            f"{aof_metrics['aof']:.1f}×" if aof_metrics.get("aof") is not None else "N/A",
            f"{reference.get('model', '方案未知')}；参数复核{reference.get('reviewed_date', '未知')}",
            aof, WEIGHTS,
        ),
        component(
            "reit_pressure", "REIT估值压力", reit_metrics.get("score"),
            f"-{reit_metrics['mean_drawdown']:.1f}%" if reit_metrics.get("mean_drawdown") is not None else "N/A",
            _market_period(reit), reit, WEIGHTS,
        ),
        component(
            "liquid_cooling", "液冷加速信号", liquid_metrics.get("score"),
            f"{liquid_metrics['mean_growth']:+.1f}%" if liquid_metrics.get("mean_growth") is not None else "N/A",
            _market_period(liquid), liquid, WEIGHTS,
        ),
        component(
            "power_infrastructure", "电力基础设施", power_metrics.get("score"),
            f"{power_metrics['mean_growth']:+.1f}%" if power_metrics.get("mean_growth") is not None else "N/A",
            _market_period(power), power, WEIGHTS,
        ),
    ]
    score = calculate_score({row["id"]: row["score"] for row in components}, WEIGHTS)
    missing = [row["name"] for row in components if row["score"] is None]
    quarter = quarter_for(today)
    return {
        "id": f"data-center-page-{quarter.lower()}-current",
        "quarter": quarter,
        "period_end": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "record_type": "current_in_progress",
        "method_version": "data-center-page-quarterly-v1",
        "score": score,
        "display_score": None if score is None else round(score),
        "state": state_for(score),
        "components": components,
        "summary": (f"{quarter}进行中；当前四项均有效。" if not missing
                    else f"{quarter}进行中；缺少：{'、'.join(missing)}。"),
        "caveat": "当前季度会随来源刷新，不写入历史。季度结束后才冻结为一条页面级快照。",
    }


def load_history(path=None):
    return _load_history(path or CONFIG, WEIGHTS)
