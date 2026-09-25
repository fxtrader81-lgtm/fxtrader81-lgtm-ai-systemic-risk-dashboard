from __future__ import annotations

# Streamlit Cloud reload marker: native factor navigation

# =========================================================
# core/score_engine.py
# 每个 Straw 计算完自己的分数后，注册到这里
# Dashboard 读取并汇总 System Risk Score
# =========================================================

import streamlit as st
from core.alert_engine import score_to_state
from config.thresholds import STRAW_WEIGHTS, STATE_COLORS


# ---- Straw 评分注册 ----------------------------------------

def register_score(straw_id: str, score: float):
    """
    在 Straw 页面末尾调用，把自己的分数写入 session_state。
    straw_id: "straw1" ~ "straw7"
    score:    0–100
    """
    if "straw_scores" not in st.session_state:
        st.session_state["straw_scores"] = {}
    st.session_state["straw_scores"][straw_id] = round(score, 1)


# ---- AI结构性风险总分 ----------------------------------------

def system_risk_score(scores: dict) -> float | None:
    """
    加权平均各 Straw 分数 → System Risk Score (0–100)
    scores: {"straw1": 82, "straw2": 61, ...}
    缺失项不参与计算；覆盖率不足时由调用方显示不可用。
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for straw_id, weight in STRAW_WEIGHTS.items():
        score = scores.get(straw_id)
        if score is None:
            continue
        weighted_sum += score * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return round(weighted_sum / total_weight, 1)


# ---- Dashboard 渲染工具 -------------------------------------

def render_system_card(scores: dict, *, system_result: dict | None = None) -> str:
    """
    返回AI结构性风险大卡片 HTML。
    scores: {"straw1": 82, ...}
    """
    raw_score = system_result.get("score") if system_result else system_risk_score(scores)
    raw_coverage = system_result.get("coverage", 100) if system_result else 100
    try:
        sys_score = None if raw_score is None else float(raw_score)
        coverage = int(round(float(raw_coverage)))
    except (TypeError, ValueError, OverflowError):
        sys_score, coverage = None, 0
    if sys_score is None:
        return f'''<div class="system-score-card system-score-unavailable">
  <div><div class="system-score-label">COMPUTE-DOLLAR RISK TERMINAL · AI结构性风险</div>
  <div class="system-score-na">N/A</div><div class="system-score-desc">有效数据覆盖率 {coverage}%：不足以形成可信总分。</div></div>
  <div class="system-score-meta">仅汇总因子01–05 · 缺失数据不按安全或中性分处理</div></div>'''
    state     = str((system_result or {}).get("state") or score_to_state(sys_score))
    color     = STATE_COLORS.get(state, "#fbbf24")
    bar_w     = min(int(sys_score), 100)

    descs = {
        "SAFE":     "01–05结构因子处于正常区间；传导状态另见06与07。",
        "WATCH":    "部分结构因子出现早期信号；传导状态另见06与07。",
        "WARNING":  "多项结构因子同步抬升，但不等同于市场已经发生传导。",
        "CRITICAL": "结构脆弱性处于高位；需结合信贷与市场确认判断CASCADE。",
    }

    return f"""
<div class="system-score-card">
  <div>
    <div class="system-score-label">COMPUTE-DOLLAR RISK TERMINAL · AI结构性风险</div>
    <div class="system-score-row"><div class="system-score-num" style="color:{color};">{sys_score:.0f}</div><div class="system-score-scale">/100</div></div>
    <div class="system-score-desc">{descs.get(state, '')}<br><span class="coverage-text">有效权重覆盖率 {coverage}%</span></div>
  </div>
  <div class="system-score-right">
    <div class="osci-state-label">结构状态</div>
    <div class="system-score-state" style="color:{color};">{state}</div>
    <div class="osci-bar-wrap system-score-bar">
      <div class="risk-bar-fill" style="width:{bar_w}%; background:{color};"></div>
    </div>
  </div>
</div>
"""


FACTOR_LABELS = {
    "straw1": "🌾 01 · 资本开支偏离",
    "straw2": "💻 02 · 开源商业化压缩",
    "straw3": "🏗 03 · 数据中心资产减值",
    "straw4": "⚡ 04 · AI能源约束",
    "straw5": "🏦 05 · AI融资结构脆弱性",
    "straw6": "💳 06 · AI信贷与再融资压力",
    "straw7": "📊 07 · 宏观与跨市场传导确认",
}

FACTOR_FILES = {
    "straw1": "pages/straw1.py", "straw2": "pages/straw2.py",
    "straw3": "pages/straw3.py", "straw4": "pages/straw4.py",
    "straw5": "pages/straw5.py", "straw6": "pages/straw6.py",
    "straw7": "pages/straw7.py",
}


def render_factor_navigation(scores: dict, results: dict | None = None) -> None:
    """Use Streamlit's native router so these links behave exactly like the sidebar."""
    st.markdown('<div class="compact-title">风险因子 · 点击进入详情</div>', unsafe_allow_html=True)
    for straw_id, label in FACTOR_LABELS.items():
        result = (results or {}).get(straw_id, {})
        score = result.get("score") if results is not None else scores.get(straw_id)
        if score is None:
            score_txt, state, color, bar_w = "—", "N/A", "#94a3b8", 0
        else:
            state = result.get("state") or score_to_state(score)
            color = STATE_COLORS.get(state, "#fbbf24")
            score_txt, bar_w = f"{score:.0f}", min(int(score), 100)
        st.markdown(
            f'<div class="factor-native-meta"><span>{score_txt} /100 · {state}</span>'
            f'<div class="straw-bar-wrap"><div class="straw-bar-fill" style="width:{bar_w}%;background:{color};"></div></div></div>',
            unsafe_allow_html=True,
        )
        st.page_link(FACTOR_FILES[straw_id], label=f"{label}　查看详情 →", use_container_width=True)
