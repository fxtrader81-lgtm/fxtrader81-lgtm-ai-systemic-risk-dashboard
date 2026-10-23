"""Quarterly page snapshots for Factor 02 (open-source compression)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from core.quarterly_history import calculate_score, component, load_history as _load_history, quarter_for, state_for


CONFIG = Path(__file__).resolve().parents[1] / "config/open_source_quarterly_history.json"
WEIGHTS = {
    "capability_gap": 0.20,
    "price_compression": 0.35,
    "deployment_momentum": 0.30,
    "ecosystem_velocity": 0.15,
}


def _compact(value, divisor, suffix):
    return f"{value / divisor:.1f}{suffix}" if value is not None else "N/A"


def make_current_snapshot(capability, prices, deployment, ecology, today=None):
    today = today or date.today()
    cap = capability.get("metrics", {})
    price = prices.get("metrics") or {}
    deploy = deployment.get("metrics") or {}
    eco = ecology.get("metrics") or {}
    components = [
        component(
            "capability_gap", "能力代差", cap.get("score"),
            f"{cap['signed_gap']:+.2f}%" if cap.get("signed_gap") is not None else "N/A",
            f"LiveBench {capability.get('release', '版本未知')}；读取{capability.get('checked_at', '未知')}",
            capability, WEIGHTS,
        ),
        component(
            "price_compression", "价格压缩", price.get("score"),
            f"{price['ratio']:.1f}%" if price.get("ratio") is not None else "N/A",
            f"OpenRouter；读取{prices.get('checked_at', '未知')}", prices, WEIGHTS,
        ),
        component(
            "deployment_momentum", "部署动能", deploy.get("score"),
            _compact(deploy.get("total_stars"), 1_000, "K stars"),
            f"GitHub累计stars；读取{deployment.get('checked_at', '未知')}", deployment, WEIGHTS,
        ),
        component(
            "ecosystem_velocity", "生态速度", eco.get("score"),
            _compact(eco.get("total_downloads"), 1_000_000, "M downloads"),
            f"Hugging Face近30天滚动窗口；读取{ecology.get('checked_at', '未知')}", ecology, WEIGHTS,
        ),
    ]
    score = calculate_score({row["id"]: row["score"] for row in components}, WEIGHTS)
    missing = [row["name"] for row in components if row["score"] is None]
    quarter = quarter_for(today)
    return {
        "id": f"open-source-page-{quarter.lower()}-current",
        "quarter": quarter,
        "period_end": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "record_type": "current_in_progress",
        "method_version": "open-source-page-quarterly-v1",
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
