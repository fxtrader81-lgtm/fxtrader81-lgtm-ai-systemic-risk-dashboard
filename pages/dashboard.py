# =========================================================
# pages/dashboard.py
# Compute-Dollar Risk Terminal — 总览首页
#
# 显示：
#   · 系统总风险评分（加权汇总）
#   · 六根稻草各自评分进度条
#   · 点击可跳转各 Straw 详情页（通过侧边栏导航）
# =========================================================

import streamlit as st
from datetime import datetime
from core.score_engine import (
    render_system_card, render_straw_rows,
    system_risk_score, STRAW_LABELS,
)
from core.alert_engine import score_to_state
from config.thresholds import STATE_COLORS


# ---- 读取已注册的 Straw 评分 --------------------------------
scores = st.session_state.get("straw_scores", {})

# ---- 页眉 ---------------------------------------------------
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:28px;">
  <div>
    <div class="main-title">📡 Compute-Dollar Risk Terminal</div>
    <div class="sub-title">AI次贷危机监测系统 · 六大风险因子实时评分</div>
  </div>
  <div style="text-align:right; padding-top:4px;">
    <span class="timestamp-text">🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ---- 系统总分卡片 -------------------------------------------
st.markdown(render_system_card(scores), unsafe_allow_html=True)

# ---- 六根稻草评分 -------------------------------------------
col_bars, col_tip = st.columns([2, 1])

with col_bars:
    st.markdown('<div class="panel-title">六大风险因子评分</div>', unsafe_allow_html=True)
    st.markdown(render_straw_rows(scores), unsafe_allow_html=True)

with col_tip:
    sys_score = system_risk_score(scores)
    state     = score_to_state(sys_score)
    color     = STATE_COLORS.get(state, "#fbbf24")

    st.markdown(f"""
<div class="panel" style="height:100%;">
  <div class="panel-title">📋 使用说明</div>
  <div class="step-text">
    1. 点击左侧导航栏中的各 <b>Straw</b> 页面查看详情。<br><br>
    2. 每个 Straw 完成加载后，评分自动注册到本页面总览。<br><br>
    3. <b>系统总分</b>为六根稻草加权平均值（未加载的 Straw 默认计 50 分）。<br><br>
    4. 评分标准：<br>
       &nbsp;&nbsp;<span class="green">0–25 SAFE</span> &nbsp;
       <span class="yellow">25–50 WATCH</span> &nbsp;
       <span style="color:#f97316">50–75 WARNING</span> &nbsp;
       <span class="red">75+ CRITICAL</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ---- 页脚 ---------------------------------------------------
if not scores:
    st.info("💡 尚未加载任何 Straw 数据。请点击左侧导航栏进入各 Straw 页面，数据加载后评分将自动汇总至此。")

st.markdown(
    f'<div class="footer-text">Compute-Dollar Risk Terminal · 数据实时采集 · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>',
    unsafe_allow_html=True,
)
