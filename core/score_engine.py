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

def system_risk_score(scores: dict) -> float:
    """
    加权平均各 Straw 分数 → System Risk Score (0–100)
    scores: {"straw1": 82, "straw2": 61, ...}
    缺失的 Straw 用 50（中性）填充。
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for straw_id, weight in STRAW_WEIGHTS.items():
        score = scores.get(straw_id, 50.0)
        weighted_sum += score * weight
        total_weight += weight
    if total_weight == 0:
        return 50.0
    return round(weighted_sum / total_weight, 1)


# ---- Dashboard 渲染工具 -------------------------------------

def render_system_card(scores: dict) -> str:
    """
    返回系统总分大卡片 HTML。
    scores: {"straw1": 82, ...}
    """
    sys_score = system_risk_score(scores)
    state     = score_to_state(sys_score)
    color     = STATE_COLORS.get(state, "#fbbf24")
    bar_w     = min(int(sys_score), 100)

    descs = {
        "SAFE":     "各风险因子均处于正常区间，AI次贷危机系统性风险较低。",
        "WATCH":    "部分风险因子出现早期信号，建议加强监测频率。",
        "WARNING":  "多项风险因子同步抬升，系统性风险已进入高危区间。",
        "CRITICAL": "风险因子叠加共振，需立即启动深度尽调与风险对冲。",
    }

    return f"""
<div class="system-score-card">
  <div>
    <div class="system-score-label">🌾 Compute-Dollar Risk Terminal · 系统总分</div>
    <div class="system-score-num" style="color:{color};">{sys_score:.0f}</div>
    <div class="system-score-desc">{descs.get(state, '')}</div>
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


STRAW_LABELS = {
    "straw1": "🌾 Straw 1 · AI资本开支循环",
    "straw2": "💻 Straw 2 · 开源压缩风险",
    "straw3": "🏗 Straw 3 · 数据中心资产减值",
    "straw4": "⚡ Straw 4 · 全球AI能源控制",
    "straw5": "🏦 Straw 5 · 金融证券化风险",
    "straw6": "📊 Straw 6 · 宏观市场预警",
}


def render_straw_rows(scores: dict) -> str:
    """
    渲染六根稻草进度条列表 HTML。
    """
    rows = ""
    for straw_id, label in STRAW_LABELS.items():
        score  = scores.get(straw_id, None)
        if score is None:
            score_txt  = "—"
            color      = "#475569"
            state_txt  = "N/A"
            bar_w      = 0
        else:
            state     = score_to_state(score)
            color     = STATE_COLORS.get(state, "#fbbf24")
            score_txt = f"{score:.0f}"
            state_txt = state
            bar_w     = min(int(score), 100)

        rows += f"""
<div class="straw-row">
  <div class="straw-name">{label}</div>
  <div class="straw-bar-wrap">
    <div class="straw-bar-fill" style="width:{bar_w}%; background:{color};"></div>
  </div>
  <div class="straw-score" style="color:{color};">{score_txt}</div>
  <div class="straw-state" style="color:{color};">{state_txt}</div>
</div>
"""
    return f'<div class="panel">{rows}</div>'
