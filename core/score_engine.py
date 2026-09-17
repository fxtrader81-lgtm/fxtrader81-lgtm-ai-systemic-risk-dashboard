from __future__ import annotations

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
    straw_id: "straw1" ~ "straw6"
    score:    0–100
    """
    if "straw_scores" not in st.session_state:
        st.session_state["straw_scores"] = {}
    st.session_state["straw_scores"][straw_id] = round(score, 1)


# ---- 系统总分 ------------------------------------------------

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
    返回系统总分大卡片 HTML。
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
  <div><div class="system-score-label">COMPUTE-DOLLAR RISK TERMINAL · 系统总分</div>
  <div class="system-score-na">N/A</div><div class="system-score-desc">有效数据覆盖率 {coverage}%：不足以形成可信总分。</div></div>
  <div class="system-score-meta">缺失数据不按安全或中性分处理</div></div>'''
    state     = str((system_result or {}).get("state") or score_to_state(sys_score))
    color     = STATE_COLORS.get(state, "#fbbf24")
    bar_w     = min(int(sys_score), 100)

    descs = {
        "SAFE":     "各风险因子均处于正常区间，当前系统性风险较低。",
        "WATCH":    "部分风险因子出现早期信号，建议加强监测频率。",
        "WARNING":  "多项风险因子同步抬升，系统性风险已进入高危区间。",
        "CRITICAL": "风险因子叠加共振，需立即启动深度尽调与风险对冲。",
    }

    return f"""
<div class="system-score-card">
  <div>
    <div class="system-score-label">COMPUTE-DOLLAR RISK TERMINAL · 系统总分</div>
    <div class="system-score-row"><div class="system-score-num" style="color:{color};">{sys_score:.0f}</div><div class="system-score-scale">/100</div></div>
    <div class="system-score-desc">{descs.get(state, '')}<br><span class="coverage-text">有效权重覆盖率 {coverage}%</span></div>
  </div>
  <div style="text-align:right;">
    <div class="osci-state-label">系统状态</div>
    <div class="system-score-state" style="color:{color};">{state}</div>
    <div class="osci-bar-wrap" style="width:320px; margin-top:14px;">
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
    "straw5": "🏦 05 · AI融资闭环风险",
    "straw6": "📊 06 · 宏观市场预警",
}

FACTOR_PATHS = {
    "straw1": "factor-capex-divergence",
    "straw2": "factor-open-source",
    "straw3": "factor-data-center-assets",
    "straw4": "factor-energy",
    "straw5": "factor-financing-loop",
    "straw6": "factor-macro-market",
}


def render_straw_rows(scores: dict, results: dict | None = None) -> str:
    """
    渲染六项风险因子进度条列表 HTML。
    """
    rows = ""
    for straw_id, label in FACTOR_LABELS.items():
        path = FACTOR_PATHS[straw_id]
        result = (results or {}).get(straw_id, {})
        score  = result.get("score") if results is not None else scores.get(straw_id, None)
        if score is None:
            score_txt  = "—"
            color      = "#94a3b8"
            state_txt  = "N/A"
            bar_w      = 0
        else:
            state     = result.get("state") or score_to_state(score)
            color     = STATE_COLORS.get(state, "#fbbf24")
            score_txt = f"{score:.0f}"
            state_txt = state
            bar_w     = min(int(score), 100)

        rows += f"""
<a class="straw-row factor-link" href="./{path}" target="_self" aria-label="查看{label}详情">
  <div class="straw-name">{label}</div>
  <div class="straw-bar-wrap">
    <div class="straw-bar-fill" style="width:{bar_w}%; background:{color};"></div>
  </div>
  <div class="straw-score" style="color:{color};">{score_txt}</div>
  <div class="straw-state" style="color:{color};">{state_txt}</div>
  <div class="factor-arrow">查看详情 →</div>
</a>
"""
    return f'<div class="panel factor-panel"><div class="compact-title">风险因子</div>{rows}</div>'
