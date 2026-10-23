"""Page-level quarterly snapshots for Factor 04.

Archived quarters are immutable, version-controlled records.  Live refreshes
produce only the current-quarter view and never create noisy history rows.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import math
from pathlib import Path


CONFIG = Path(__file__).resolve().parents[1] / "config/energy_quarterly_history.json"
WEIGHTS = {
    "infrastructure": 0.40,
    "energy_cost": 0.25,
    "system_efficiency": 0.20,
    "market_signal": 0.15,
}


def state_for(score):
    if score is None:
        return "N/A"
    if score < 30:
        return "SAFE"
    if score < 50:
        return "WATCH"
    if score < 70:
        return "WARNING"
    return "CRITICAL"


def calculate_score(scores):
    if set(scores) != set(WEIGHTS):
        return None
    values = list(scores.values())
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           or not 0 <= v <= 100 for v in values):
        return None
    return round(sum(WEIGHTS[key] * float(scores[key]) for key in WEIGHTS), 1)


def quarter_for(day=None):
    day = day or date.today()
    return f"{day.year}Q{(day.month - 1) // 3 + 1}"


def _component(component_id, name, score, display_value, observation_period, raw):
    weight = WEIGHTS[component_id]
    return {
        "id": component_id,
        "name": name,
        "weight": weight,
        "score": score,
        "contribution": None if score is None else round(score * weight, 1),
        "display_value": display_value,
        "observation_period": observation_period,
        "raw": raw,
    }


def make_current_snapshot(infra, cost, efficiency, market, today=None):
    today = today or date.today()
    infra_inputs = infra.get("inputs", {})
    cost_range = cost.get("ratio_range")
    market_rows = market.get("rows", {})
    metrics = efficiency.get("metrics", {})
    components = [
        _component(
            "infrastructure", "基础设施约束", infra.get("score"),
            f"{infra_inputs.get('interconnection_queue_months', 'N/A')}mo",
            infra_inputs.get("updated", "观察期未知"), infra_inputs,
        ),
        _component(
            "energy_cost", "能源成本压力", cost.get("score"),
            f"{cost_range[0]:.2f}—{cost_range[1]:.2f}" if cost_range else "N/A",
            cost.get("period", "观察期未知"),
            {"ratio_range": cost_range, "state": cost.get("state"),
             "reviewed_on": cost.get("reviewed_on")},
        ),
        _component(
            "system_efficiency", "AI推理系统能效对冲", metrics.get("score"),
            f"{metrics['generation_gain']:.2f}×" if metrics.get("generation_gain") else "N/A",
            f"MLPerf {efficiency.get('baseline_release', 'N/A')}→{efficiency.get('target_release', 'N/A')}；检查{efficiency.get('checked_at', '未知')}",
            {"generation_gain": metrics.get("generation_gain"),
             "pair_count": metrics.get("pair_count"),
             "baseline_generation": efficiency.get("baseline_generation"),
             "target_generation": efficiency.get("target_generation")},
        ),
        _component(
            "market_signal", "电力市场信号", market.get("score"),
            f"{market['mean_position_pct']:.1f}%" if market.get("mean_position_pct") is not None else "N/A",
            f"Yahoo Finance {market.get('observed_on', '行情日期未知')}；页面缓存1小时",
            {ticker: market_rows.get(ticker) for ticker in market.get("tickers", ["CEG", "VST"])},
        ),
    ]
    scores = {row["id"]: row["score"] for row in components}
    score = calculate_score(scores)
    unavailable = [row["name"] for row in components if row["score"] is None]
    return {
        "id": f"energy-page-{quarter_for(today).lower()}-current",
        "quarter": quarter_for(today),
        "period_end": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "record_type": "current_in_progress",
        "method_version": "energy-page-quarterly-v2",
        "score": score,
        "display_score": None if score is None else round(score),
        "state": state_for(score),
        "components": components,
        "summary": (f"{quarter_for(today)}进行中；当前四项均有效。" if not unavailable
                    else f"{quarter_for(today)}进行中；缺少：{'、'.join(unavailable)}。"),
        "caveat": "当前季度会随来源刷新，不写入历史。季度结束后才冻结为一条页面级快照。",
    }


def load_history(path=None):
    payload = json.loads(Path(path or CONFIG).read_text(encoding="utf-8"))
    records = payload.get("records", [])
    ids = [row.get("id") for row in records]
    quarters = [row.get("quarter") for row in records]
    if len(ids) != len(set(ids)) or len(quarters) != len(set(quarters)):
        raise ValueError("季度历史ID或季度重复")
    for record in records:
        scores = {row.get("id"): row.get("score") for row in record.get("components", [])}
        expected = calculate_score(scores)
        if expected is None or abs(expected - float(record.get("score"))) > 0.11:
            raise ValueError(f"季度历史总分与分项不一致：{record.get('quarter')}")
        if record.get("state") != state_for(expected):
            raise ValueError(f"季度历史状态与总分不一致：{record.get('quarter')}")
    return records


def export_bundle(current, path=None, legacy=None):
    return {
        "schema_version": 1,
        "history_policy": "每季度只保存一条页面级快照；页面刷新只更新当前季度，不产生历史记录。",
        "current": current,
        "quarterly_history": load_history(path),
        "legacy_method_evidence": legacy or {},
    }
