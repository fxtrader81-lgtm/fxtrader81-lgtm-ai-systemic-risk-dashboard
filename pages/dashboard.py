"""Compute-Dollar Risk Terminal — source-backed system overview."""

from datetime import datetime
from html import escape

import streamlit as st

from components.ui import load_css
from config.thresholds import STATE_COLORS
from core.factor_registry import aggregate_factor_results, load_factor_results
from core.score_engine import render_straw_rows, render_system_card

load_css()

def _conclusion(system, results):
    if not system["available"]:
        return "当前有效数据覆盖不足，系统暂不输出方向性结论。请以右侧各因子的可用状态为准。"
    leaders = sorted((x for x in results.values() if x.get("available")), key=lambda x: x["score"], reverse=True)[:2]
    names = "、".join(x["name"] for x in leaders)
    messages = {
        "SAFE": "当前可用因子整体处于正常区间，尚未形成系统性风险共振。",
        "WATCH": "早期风险信号已经出现，建议提高数据刷新和交叉验证频率。",
        "WARNING": "多个风险因子同步抬升，资本、资产与宏观链条需要重点跟踪。",
        "CRITICAL": "风险因子出现高位共振，应立即开展深度尽调与风险敞口评估。",
    }
    return f"{messages[system['state']]} 当前贡献较高的因子为：{names}。"

with st.spinner("正在汇总六个风险因子…"):
    results = load_factor_results()
system = aggregate_factor_results(results)
scores = {key: item["score"] for key, item in results.items() if item.get("available")}

st.markdown(f"""<div class="dashboard-header"><div><div class="main-title">📡 Compute-Dollar Risk Terminal</div>
<div class="sub-title">AI次贷危机监测系统 · 六个风险因子自动汇总</div></div>
<span class="timestamp-text">🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>""", unsafe_allow_html=True)
st.markdown(render_system_card(scores, system_result=system), unsafe_allow_html=True)

color = STATE_COLORS.get(system["state"], "#64748b")
st.markdown(f"""<div class="dashboard-grid">
<div class="dashboard-conclusion"><div class="conclusion-eyebrow">综合结论</div>
<div class="conclusion-state" style="color:{color};">{escape(system['state'])}</div>
<div class="conclusion-copy">{escape(_conclusion(system, results))}</div>
<div class="conclusion-note">有效权重覆盖率 {system['coverage']}% · 缺失因子不按安全或中性分处理</div></div>
<div class="factor-block"><div class="compact-title">六个风险因子</div>{render_straw_rows(scores, results=results)}</div>
</div>""", unsafe_allow_html=True)

source_items = []
for key in ("straw1", "straw2", "straw3", "straw4", "straw5", "straw6"):
    item = results[key]
    availability = f"{item['coverage']:.0f}%" if item["available"] else "不可用"
    source_items.append(f'<div class="source-status"><b>{escape(item["name"])}</b><span>{availability}</span><small>{escape(item["source"])}</small></div>')
st.markdown('<div class="source-strip"><div class="compact-title">数据覆盖与来源</div>' + "".join(source_items) + "</div>", unsafe_allow_html=True)

if st.button("刷新全部因子数据", use_container_width=False):
    st.cache_data.clear()
    st.rerun()
st.markdown(f'<div class="footer-text">缺失值不填 0、不填 50 · 数据缓存 1 小时 · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>', unsafe_allow_html=True)
