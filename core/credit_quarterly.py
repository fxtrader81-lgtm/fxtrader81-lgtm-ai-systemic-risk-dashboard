"""Page-level quarterly snapshots for Factor 06 credit/refinancing pressure."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path

import pandas as pd

from core.credit_risk import COMPONENTS
from core.quarterly_history import component, load_history as _load_history, quarter_for


CONFIG = Path(__file__).resolve().parents[1] / "config/credit_quarterly_history.json"
WEIGHTS = {key: value["weight"] for key, value in COMPONENTS.items()}


def _latest_period(series, *, quarterly=False):
    if series is None or series.empty:
        return "日期不可得"
    stamp = pd.Timestamp(series.dropna().index[-1])
    return str(stamp.to_period("Q")) if quarterly else stamp.strftime("%Y-%m-%d")


def _component_snapshot(key, item, series):
    labels = {
        "credit_spread": "高收益信用利差",
        "real_rate": "10Y实际利率",
        "financial_conditions": "NFCI金融条件",
        "lending_standards": "银行融资可得性",
    }
    if item is None:
        return component(key, labels[key], None, "N/A", "数据缺失", {}, WEIGHTS)
    if key == "credit_spread":
        display = f"{item['value']:.0f}bp"
        period = f"FRED HY OAS；截至{_latest_period(series['hy_oas'])}"
    elif key == "real_rate":
        display = f"{item['value']:.2f}%"
        period = f"FRED 10Y TIPS；截至{_latest_period(series['real_yield'])}"
    elif key == "financial_conditions":
        display = f"{item['value']:+.3f}"
        period = f"FRED NFCI；截至{_latest_period(series['nfci'])}"
    else:
        display = f"{item['value']:+.1f}%"
        period = f"美联储SLOOS；{_latest_period(series['sloos'], quarterly=True)}"
    return component(key, labels[key], item.get("score"), display, period, dict(item), WEIGHTS)


def make_current_snapshot(metrics, series, today=None):
    """Build the current-quarter page snapshot from the shared Factor-06 metrics."""
    today = today or date.today()
    rows = [_component_snapshot(key, metrics.get(key), series) for key in WEIGHTS]
    composite = metrics["composite"]
    quarter = quarter_for(today)
    missing = [row["name"] for row in rows if row["score"] is None]
    return {
        "id": f"credit-page-{quarter.lower()}-current",
        "quarter": quarter,
        "period_end": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "record_type": "current_in_progress",
        "method_version": "cfri-quarterly-v2-sloos",
        "score": composite.get("score"),
        "display_score": None if composite.get("score") is None else round(composite["score"]),
        "state": composite.get("grade", "N/A"),
        "components": rows,
        "summary": (f"{quarter}进行中；四项覆盖率{composite.get('coverage', 0)}%。"
                    if not missing else f"{quarter}进行中；缺少：{'、'.join(missing)}。"),
        "caveat": "当前季度会随来源刷新，不写入历史。季度结束后才冻结一条06页面级快照；AI融资事件只作非评分证据。",
    }


def load_history(path=None):
    return _load_history(path or CONFIG, WEIGHTS, cutoffs=(25, 50, 75))


def load_archive_metadata(path=None):
    payload = json.loads(Path(path or CONFIG).read_text(encoding="utf-8"))
    return {
        "method_notes": payload.get("method_notes", []),
        "legacy_method_evidence": payload.get("legacy_method_evidence", {}),
    }
