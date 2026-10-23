"""Shared page-level quarterly snapshot helpers for Factors 02 and 03."""
from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path


def quarter_for(day=None):
    day = day or date.today()
    return f"{day.year}Q{(day.month - 1) // 3 + 1}"


def state_for(score, cutoffs=(25, 45, 65)):
    if score is None:
        return "N/A"
    safe, watch, warning = cutoffs
    if score < safe:
        return "SAFE"
    if score < watch:
        return "WATCH"
    if score < warning:
        return "WARNING"
    return "CRITICAL"


def calculate_score(scores, weights):
    if set(scores) != set(weights):
        return None
    values = list(scores.values())
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or not 0 <= value <= 100 for value in values):
        return None
    return round(sum(float(scores[key]) * weights[key] for key in weights), 1)


def component(component_id, name, score, display_value, observation_period, raw, weights):
    weight = weights[component_id]
    return {
        "id": component_id,
        "name": name,
        "weight": weight,
        "score": score,
        "contribution": None if score is None else round(float(score) * weight, 1),
        "display_value": display_value,
        "observation_period": observation_period,
        "raw": raw,
    }


def load_history(path, weights, cutoffs=(25, 45, 65)):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = payload.get("records", [])
    ids = [row.get("id") for row in records]
    quarters = [row.get("quarter") for row in records]
    if len(ids) != len(set(ids)) or len(quarters) != len(set(quarters)):
        raise ValueError("季度历史ID或季度重复")
    for record in records:
        scores = {row.get("id"): row.get("score") for row in record.get("components", [])}
        expected = calculate_score(scores, weights)
        if expected is None or abs(expected - float(record.get("score"))) > 0.11:
            raise ValueError(f"季度历史总分与分项不一致：{record.get('quarter')}")
        if record.get("state") != state_for(expected, cutoffs):
            raise ValueError(f"季度历史状态与总分不一致：{record.get('quarter')}")
    return records
