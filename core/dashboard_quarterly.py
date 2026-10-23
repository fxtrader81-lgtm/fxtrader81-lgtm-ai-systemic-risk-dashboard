"""Page-level quarterly snapshots for the seven-factor system overview."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path

from config.thresholds import STRAW_WEIGHTS
from core.quarterly_history import quarter_for, state_for


CONFIG = Path(__file__).resolve().parents[1] / "config/dashboard_quarterly_history.json"
FACTOR_ORDER = tuple(f"straw{number}" for number in range(1, 8))
FACTOR_ROLES = {
    "straw1": "投入与收入匹配",
    "straw2": "开源竞争与商业化压力",
    "straw3": "数据中心资产减值代理",
    "straw4": "能源、电网与交付约束",
    "straw5": "融资结构脆弱性",
    "straw6": "信用与再融资外部确认",
    "straw7": "宏观与跨市场传导确认",
}


def _factor_row(key, item):
    available = bool(item.get("available")) and item.get("score") is not None
    weight = STRAW_WEIGHTS.get(key)
    score = float(item["score"]) if available else None
    return {
        "id": key,
        "number": key[-1].zfill(2),
        "name": item.get("name", key),
        "role": FACTOR_ROLES[key],
        "layer": "structure" if weight is not None else "transmission",
        "weight": weight,
        "score": score,
        "state": item.get("state", state_for(score)) if available else "N/A",
        "coverage": float(item.get("coverage", 0)),
        "contribution": None if weight is None or score is None else round(score * weight, 1),
        "detail": item.get("detail", "未保存证据摘要"),
        "source": item.get("source", "未保存来源"),
    }


def make_current_snapshot(results, system, today=None):
    today = today or date.today()
    quarter = quarter_for(today)
    factors = [_factor_row(key, results[key]) for key in FACTOR_ORDER]
    missing = [row["number"] for row in factors if row["score"] is None]
    return {
        "id": f"dashboard-{quarter.lower()}-current",
        "quarter": quarter,
        "period_end": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "record_type": "current_in_progress",
        "method_version": "dashboard-quarterly-v1",
        "score": system.get("score"),
        "display_score": None if system.get("score") is None else round(system["score"]),
        "state": system.get("state", "N/A"),
        "coverage": system.get("coverage", 0),
        "phase": system.get("phase", "常态监测"),
        "cascade": bool(system.get("cascade", False)),
        "factors": factors,
        "summary": (f"{quarter}进行中；七个因子当前均可用。" if not missing
                    else f"{quarter}进行中；当前缺少因子：{'/'.join(missing)}。"),
        "caveat": "当前季度随来源刷新，不写入历史。结构总分只汇总01–05；06、07仅记录传导确认。",
    }


def _calculated_structure(factors, minimum_coverage=0.70):
    by_id = {row["id"]: row for row in factors}
    available_weight = sum(
        weight for key, weight in STRAW_WEIGHTS.items()
        if by_id.get(key, {}).get("score") is not None
    )
    if available_weight < minimum_coverage:
        return None, "N/A", round(available_weight * 100)
    weighted = sum(by_id[key]["score"] * weight for key, weight in STRAW_WEIGHTS.items()
                   if by_id.get(key, {}).get("score") is not None)
    score = round(weighted / available_weight, 1)
    return score, state_for(score), round(available_weight * 100)


def load_history(path=None):
    payload = json.loads(Path(path or CONFIG).read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if len({row.get("id") for row in records}) != len(records):
        raise ValueError("总览季度历史ID重复")
    if len({row.get("quarter") for row in records}) != len(records):
        raise ValueError("总览季度历史季度重复")
    for record in records:
        factors = record.get("factors", [])
        if [row.get("id") for row in factors] != list(FACTOR_ORDER):
            raise ValueError(f"总览历史因子顺序或覆盖错误：{record.get('quarter')}")
        score, state, coverage = _calculated_structure(factors)
        if record.get("score") != score or record.get("state") != state or record.get("coverage") != coverage:
            raise ValueError(f"总览历史总分、状态或覆盖率不一致：{record.get('quarter')}")
    return records
