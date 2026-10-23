"""Display-only maintenance status; never changes data or scoring."""
from datetime import date, datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo


def maintenance_status(snapshot, today=None):
    today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    try:
        reviewed = date.fromisoformat(snapshot.get("reviewed_on", ""))
        due = reviewed + timedelta(days=90)
    except (TypeError, ValueError):
        reviewed, due = None, None
    if not snapshot.get("available"):
        label, attention = "待补齐数据 · 人工维护", True
    elif due is None or today < reviewed:
        label, attention = "复核日期待核验 · 人工维护", True
    elif today >= due:
        label, attention = "已到复核期 · 人工维护", True
    else:
        label, attention = "已复核 · 人工维护", False
    detail = f"最近复核：{reviewed.isoformat()}" if reviewed else "最近复核日期未知"
    if due:
        detail += f"；下次例行复核：{due.isoformat()}"
    if not snapshot.get("available"):
        detail += "；当前仍缺可比成对价格，无需等到下次日期才补齐"
    detail += "。仅提示维护状态，不自动采集，不代表风险等级。"
    return {"label": label, "attention": attention, "detail": detail}


def maintenance_badge(snapshot, today=None):
    state = maintenance_status(snapshot, today)
    css = "cost-maintenance cost-maintenance--attention" if state["attention"] else "cost-maintenance"
    return (f'<span class="{css}" title="{escape(state["detail"], quote=True)}">'
            f'<span class="cost-maintenance__dot" aria-hidden="true"></span>{escape(state["label"])}</span>')
