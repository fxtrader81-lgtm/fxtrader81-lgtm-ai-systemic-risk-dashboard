from __future__ import annotations

# =========================================================
# components/ui.py
# 公共 UI 组件：CSS加载、页眉、Metric卡片、Panel标题等
# =========================================================

import streamlit as st
from pathlib import Path
from datetime import date, datetime
from html import escape


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
    right    = f'<div class="page-header-meta">{time_str}{badge}</div>' if (time_str or badge) else ""

    st.markdown(f"""
<div class="page-header">
  <div>
    <div class="main-title">{title}</div>
    <div class="sub-title">{subtitle}</div>
  </div>
  {right}
</div>
""", unsafe_allow_html=True)


def dashboard_header(
    title: str,
    subtitle: str,
    *,
    updated_at: str | None = None,
) -> str:
    """Return the overview header using the shared header layout."""
    timestamp = updated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        '<div class="dashboard-header"><div>'
        f'<div class="main-title">{escape(title)}</div>'
        f'<div class="sub-title">{escape(subtitle)}</div></div>'
        f'<span class="timestamp-text">🕐 更新时间：{escape(timestamp)}</span></div>'
    )


# ---- Metric 卡片 ---------------------------------------------

def metric_card(
    label: str,
    value: str,
    color_class: str,
    arrow: str = "",
    desc: str = "",
    extra_class: str = "",
) -> str:
    """
    返回单个 KPI 卡片 HTML。
    color_class: "green" / "red" / "yellow" / "orange" / "gray"
    """
    classes = f"metric-card {extra_class}".strip()
    return f"""<div class="{classes}">
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


def panel(title: str, body: str, *, extra_class: str = "") -> str:
    """Return a complete shared panel instead of repeating wrapper markup."""
    classes = f"panel {extra_class}".strip()
    title_html = f'<div class="panel-title">{title}</div>' if title else ""
    return f'<div class="{classes}">{title_html}{body}</div>'


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


def logic_panel(steps: list[dict], *, title: str = "⚙️ 检测逻辑") -> str:
    """Render numbered methodology steps and their optional threshold rows."""
    blocks = []
    for index, step in enumerate(steps, start=1):
        step_class = " logic-step-separated" if index > 1 else ""
        blocks.append(
            f'<div class="logic-step{step_class}"><div class="step-num">{index}</div>'
            f'<div class="step-text">{step["text"]}</div></div>'
        )
        thresholds = step.get("thresholds", [])
        if thresholds:
            rows = "".join(threshold_row(*row) for row in thresholds)
            blocks.append(f'<div class="threshold-block">{rows}</div>')
    return panel(title, "".join(blocks), extra_class="logic-panel")


def source_tag_row(tags: list[str]) -> str:
    """Wrap source/status tags with one responsive shared layout."""
    return f'<div class="source-tag-row">{"".join(tags)}</div>'


def note_panel(title: str, body: str, *, tone: str = "warning") -> str:
    """Render a reusable explanatory note with a semantic tone."""
    safe_tone = tone if tone in {"warning", "info", "neutral"} else "neutral"
    return (
        f'<div class="note-panel note-panel-{safe_tone}">'
        f'<div class="note-panel-title">{title}</div>'
        f'<div class="note-panel-body">{body}</div></div>'
    )


def model_evidence_panel(*, sample: str, validation: str, boundary: str, calibration: str) -> str:
    """Use the same visible evidence disclosure on both transmission pages."""
    fields = (
        ("独立样本", sample),
        ("验证结果", validation),
        ("模型边界", boundary),
        ("阈值校准", calibration),
    )
    rows = "".join(
        f'<div class="model-evidence-row"><b>{escape(label)}</b><span>{escape(value)}</span></div>'
        for label, value in fields
    )
    return panel("📎 模型说明", f'<div class="model-evidence-grid">{rows}</div>')


def market_phase_card(phase: dict, score: float | None, grade: str, coverage: int) -> str:
    """Lead the market page with an observable phase, not a probability-like score."""
    phases = (
        ("quiet", "尚未确认"), ("transmitting", "初步传导"),
        ("release", "风险释放"), ("dissipating", "压力消退"),
    )
    steps = "".join(
        f'<div class="market-phase-step{" active" if key == phase["key"] else ""}">{escape(label)}</div>'
        for key, label in phases
    )
    score_text = "N/A" if score is None else f"{score:.1f}/100"
    return (
        '<div class="market-phase-card">'
        '<div class="market-phase-kicker">市场侧阶段观察（探索性）</div>'
        f'<div class="market-phase-title">{escape(phase["label"])}</div>'
        f'<div class="market-phase-detail">{escape(phase["detail"])}</div>'
        f'<div class="market-phase-steps">{steps}</div>'
        f'<div class="market-phase-meta">指标强度 {escape(score_text)} · 原四级状态 {escape(grade)} · '
        f'有效数据覆盖 {coverage}% · 阶段为事中描述，不是未来回调概率</div></div>'
    )


def transmission_chain_panel(phase: str, nodes: tuple[bool, bool, bool, bool]) -> str:
    """Show the four observable legs of the 05–06–07 cascade at a glance."""
    labels = ("05 结构脆弱", "06 信贷压力", "07 市场确认", "风险释放")
    items = "".join(
        f'<div class="transmission-node{" active" if active else ""}">'
        f'<span>{"●" if active else "○"}</span>{escape(label)}</div>'
        for label, active in zip(labels, nodes)
    )
    return panel(
        "结构—信贷—市场传导链",
        f'<div class="transmission-chain">{items}</div>'
        f'<div class="transmission-status">当前阶段：{escape(phase)}。'
        '节点是当前状态快照；没有验证连续触发顺序，也不是股市下跌概率。</div>',
        extra_class="transmission-panel",
    )


def section_intro(title: str, subtitle: str = "") -> str:
    subtitle_html = f'<div class="section-intro-subtitle">{subtitle}</div>' if subtitle else ""
    return f'<div class="section-intro"><div class="section-intro-title">{title}</div>{subtitle_html}</div>'


def counter_card(title: str, body: str, *, label: str = "", value: str = "") -> str:
    meta = ""
    if label or value:
        meta = f'<div class="counter-meta"><span>{label}</span><b>{value}</b></div>'
    return f'<div class="counter-card"><div class="counter-title">{title}</div><div class="counter-body">{body}{meta}</div></div>'


def two_column_info_panel(title: str, items: list[dict]) -> str:
    """Render paired explanatory blocks used by market interpretation panels."""
    columns = []
    for item in items:
        color_class = item.get("color_class", "blue")
        columns.append(
            '<div class="info-column">'
            f'<div class="info-column-title {color_class}">{item["title"]}</div>'
            f'<div class="info-column-body">{item["body"]}</div></div>'
        )
    return panel(title, f'<div class="info-grid">{"".join(columns)}</div>')


def spacer(size: str = "sm") -> str:
    safe_size = size if size in {"xs", "sm", "md", "lg"} else "sm"
    return f'<div class="ui-spacer ui-spacer-{safe_size}" aria-hidden="true"></div>'


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


def dashboard_conclusion(state: str, color: str, report_html: str, coverage: float) -> str:
    """Return the shared dashboard conclusion block."""
    return (
        '<div class="dashboard-conclusion"><div class="conclusion-eyebrow">综合结论</div>'
        f'<div class="conclusion-state" style="color:{color};">{escape(state)}</div>'
        f'<div class="conclusion-copy conclusion-report">{report_html}</div>'
        f'<div class="conclusion-note">有效权重覆盖率 {coverage}% · 缺失因子不按安全或中性分处理</div></div>'
    )


def source_strip(items: list[dict], *, title: str = "数据覆盖与来源") -> str:
    """Return the shared dashboard source coverage strip."""
    cards = []
    for item in items:
        cards.append(
            '<div class="source-status">'
            f'<b>{escape(str(item["name"]))}</b>'
            f'<span>{escape(str(item["availability"]))}</span>'
            f'<small>{escape(str(item["source"]))}</small></div>'
        )
    return f'<div class="source-strip"><div class="compact-title">{escape(title)}</div>{"".join(cards)}</div>'


def coverage_panel(coverage: float, confidence: str, color: str, table_html: str, note: str) -> str:
    """Render coverage confidence together with its evidence table."""
    return (
        '<div class="panel"><div class="metric-desc">有效权重覆盖率 '
        f'<b class="coverage-value" style="color:{color};">{coverage}%</b> · {escape(confidence)}</div>'
        f'{table_html}<div class="metric-sub">{escape(note)}</div></div>'
    )
