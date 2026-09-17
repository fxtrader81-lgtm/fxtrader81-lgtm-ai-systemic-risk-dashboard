from __future__ import annotations

# =========================================================
# components/ui.py
# 公共 UI 组件：CSS加载、页眉、Metric卡片、Panel标题等
# =========================================================

import streamlit as st
from pathlib import Path
from datetime import date, datetime


# ---- CSS 加载 ------------------------------------------------

def load_css():
    """Load the shared design system for every dashboard page."""
    styles_dir = Path(__file__).parent.parent / "styles"
    css_files = ["base.css", "components.css", "pages.css"]
    chunks = []

    try:
        for filename in css_files:
            chunks.append((styles_dir / filename).read_text(encoding="utf-8"))
        st.markdown(f"<style>{chr(10).join(chunks)}</style>", unsafe_allow_html=True)
    except FileNotFoundError as exc:
        fallback = styles_dir / "bloomberg.css"
        if fallback.exists():
            st.markdown(f"<style>{fallback.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
        else:
            st.warning(f"⚠️ 样式文件未找到：{exc.filename}")


# ---- 页眉 ----------------------------------------------------

def render_header(
    title: str,
    subtitle: str,
    *,
    symbol: str = None,
    show_time: bool = True,
):
    """
    渲染标准页眉行。
    title   : e.g. "🌾 资本开支偏离"
    subtitle: 核心检测维度说明
    symbol  : 可选，显示股票代码 badge
    """
    time_str = f'<span class="timestamp-text">🕐 更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>' if show_time else ""
    badge    = f'<span class="symbol-badge">标的：{symbol}</span>' if symbol else ""
    right    = f'<div style="text-align:right; padding-top:4px;">{time_str}{badge}</div>' if (time_str or badge) else ""

    st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:18px;">
  <div>
    <div class="main-title">{title}</div>
    <div class="sub-title">{subtitle}</div>
  </div>
  {right}
</div>
""", unsafe_allow_html=True)


# ---- Metric 卡片 ---------------------------------------------

def metric_card(
    label: str,
    value: str,
    color_class: str,
    arrow: str = "",
    desc: str = "",
) -> str:
    """
    返回单个 KPI 卡片 HTML。
    color_class: "green" / "red" / "yellow" / "orange" / "gray"
    """
    return f"""<div class="metric-card">
  <div class="metric-label">{label}</div>
  <div class="metric-row">
    <span class="metric-number {color_class}">{value}</span>
    <span class="metric-arrow {color_class}">{arrow}</span>
  </div>
  <div class="metric-desc">{desc}</div>
</div>"""


# ---- Panel 包裹 ----------------------------------------------

def panel_open(title: str = "") -> str:
    title_html = f'<div class="panel-title">{title}</div>' if title else ""
    return f'<div class="panel">{title_html}'


def panel_close() -> str:
    return "</div>"


# ---- 检测逻辑步骤 --------------------------------------------

def logic_step(num: int, text: str) -> str:
    return f'<div class="logic-step"><div class="step-num">{num}</div><div class="step-text">{text}</div></div>'


def threshold_row(dot_color: str, label: str, status: str, status_class: str) -> str:
    return f"""<div class="threshold-row">
  <div class="t-dot" style="background:{dot_color};"></div>
  <div class="t-label">{label}</div>
  <div class="t-arrow">→</div>
  <div class="t-status {status_class}">{status}</div>
</div>"""


# ---- 数据新鲜度与页脚 ----------------------------------------

def freshness_badge(updated_at: str | None, *, mode: str = "static") -> str:
    """Return one shared freshness badge for live, static, or unavailable data."""
    if not updated_at:
        return '<span class="freshness-stale">更新时间未知</span>'
    if mode == "live":
        return f'<span class="freshness-ok">自动更新 · {updated_at}</span>'
    if mode == "fallback":
        return f'<span class="freshness-warn">备用数据 · {updated_at}</span>'
    try:
        normalized = f"{updated_at}-01" if len(updated_at) == 7 else updated_at
        days_ago = (date.today() - date.fromisoformat(normalized)).days
        css = "freshness-stale" if days_ago > 90 else "freshness-warn" if days_ago > 30 else "freshness-ok"
        return f'<span class="{css} static-data-badge">静态维护 · {days_ago} 天前</span>'
    except (TypeError, ValueError):
        return f'<span class="freshness-warn static-data-badge">静态维护 · {updated_at}</span>'


def render_data_freshness(items: list[dict], *, title: str = "数据覆盖与来源") -> None:
    """Render a common source/freshness panel.

    Each item accepts ``name``, ``source``, ``updated_at`` and ``mode``.
    """
    rows = []
    for item in items:
        rows.append(
            '<div class="freshness-row">'
            f'<div><b>{item["name"]}</b><small>{item["source"]}</small></div>'
            f'{freshness_badge(item.get("updated_at"), mode=item.get("mode", "static"))}'
            '</div>'
        )
    st.markdown(
        f'<div class="freshness-panel"><div class="panel-title">📡 {title}</div>{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def render_footer(sources: str, *, updated_at: str | None = None, note: str = "仅供研究参考，不构成投资建议"):
    """Render the shared readable source footer."""
    timestamp = updated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f'<div class="footer-text">数据来源：{sources}<span>数据截至：{timestamp}</span><span>{note}</span></div>',
        unsafe_allow_html=True,
    )
