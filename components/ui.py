# =========================================================
# components/ui.py
# 公共 UI 组件：CSS加载、页眉、Metric卡片、Panel标题等
# =========================================================

import streamlit as st
from pathlib import Path
from datetime import datetime


# ---- CSS 加载 ------------------------------------------------

def load_css():
    """按层级加载统一黑金样式，每个 Straw 页面顶部调用一次。"""
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
    title   : e.g. "🌾 稻草一：AI资本开支循环检测"
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


# ---- 页脚 ----------------------------------------------------

def render_footer(sources: str):
    """sources: 数据来源说明字符串"""
    st.markdown(
        f'<div class="footer-text">数据来源：{sources} · 实时采集 · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>',
        unsafe_allow_html=True,
    )
