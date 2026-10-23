"""Reviewed counter-signal registry for Factor 04.

The registry is intentionally manual.  Public feeds can discover candidate
projects, but they cannot safely reconcile IT load, generation capacity and
project stage without review.  A new calendar quarter therefore raises a
visible review reminder while preserving the last reviewed snapshot.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re

from core.energy_quarterly import quarter_for


CONFIG = Path(__file__).resolve().parents[1] / "config/energy_counter_signals.json"
REQUIRED_SIGNALS = {"overseas_ai_expansion", "dedicated_power_progress"}
_QUARTER = re.compile(r"^(\d{4})Q([1-4])$")


def _quarter_index(value: str) -> int:
    match = _QUARTER.fullmatch(value or "")
    if not match:
        raise ValueError(f"无效季度：{value}")
    return int(match.group(1)) * 4 + int(match.group(2)) - 1


def next_quarter(value: str) -> str:
    index = _quarter_index(value) + 1
    year, zero_based = divmod(index, 4)
    return f"{year}Q{zero_based + 1}"


def _validate(payload: dict) -> None:
    if payload.get("review_mode") != "quarterly_manual_review":
        raise ValueError("反证项必须使用季度人工复核模式")
    _quarter_index(payload.get("reviewed_quarter"))
    if not payload.get("reviewed_on"):
        raise ValueError("缺少反证项核验日期")
    signals = payload.get("signals", {})
    if set(signals) != REQUIRED_SIGNALS:
        raise ValueError("反证项清单不完整")
    for signal in signals.values():
        if not signal.get("title") or not signal.get("summary") or not signal.get("projects"):
            raise ValueError("反证项缺少标题、摘要或项目")
        ids = []
        for project in signal["projects"]:
            ids.append(project.get("id"))
            if not all(project.get(key) for key in ("id", "project", "stage", "source_name", "source_url")):
                raise ValueError("反证项目缺少必要证据字段")
            if not str(project["source_url"]).startswith("https://"):
                raise ValueError("反证项目来源必须为HTTPS链接")
        if len(ids) != len(set(ids)):
            raise ValueError("反证项目ID重复")


def load_counter_signals(*, today: date | None = None, path: Path | str | None = None) -> dict:
    payload = json.loads(Path(path or CONFIG).read_text(encoding="utf-8"))
    _validate(payload)
    result = deepcopy(payload)
    current_quarter = quarter_for(today or date.today())
    reviewed_quarter = result["reviewed_quarter"]
    result["current_quarter"] = current_quarter
    result["next_review_quarter"] = next_quarter(reviewed_quarter)
    result["review_due"] = _quarter_index(current_quarter) > _quarter_index(reviewed_quarter)
    if result["review_due"]:
        result["review_status"] = "跨季度待人工复核"
        result["review_message"] = (
            f"当前已进入{current_quarter}，但反证项仍是{reviewed_quarter}快照。"
            "请人工检索并核验项目阶段、容量及来源；完成前不自动改写项目清单。"
        )
    else:
        result["review_status"] = f"{reviewed_quarter}已人工核验"
        result["review_message"] = (
            f"核验日{result['reviewed_on']}；进入{result['next_review_quarter']}后页面将提示人工更新。"
            "反证项仅作观察，不计入ESRI。"
        )
    return result
