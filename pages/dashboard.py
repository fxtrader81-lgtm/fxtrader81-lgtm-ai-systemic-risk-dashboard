"""Compute-Dollar Risk Terminal — source-backed system overview."""

from datetime import datetime
from html import escape

import streamlit as st

from components.ui import load_css, render_footer
from config.thresholds import STATE_COLORS
from core.factor_registry import aggregate_factor_results, load_factor_results
from core.score_engine import render_factor_navigation, render_system_card

load_css()

def _conclusion(system, results):
    if not system["available"]:
        return "当前有效数据覆盖不足，系统暂不输出方向性结论。"
    leaders = sorted((x for x in results.values() if x.get("available")), key=lambda x: x["score"], reverse=True)[:2]
    names = "、".join(x["name"] for x in leaders)
    messages = {
        "SAFE": "当前可用因子整体处于正常区间，尚未形成系统性风险共振。",
        "WATCH": "早期风险信号已经出现，建议提高数据刷新和交叉验证频率。",
        "WARNING": "多个风险因子同步抬升，资本、资产与宏观链条需要重点跟踪。",
        "CRITICAL": "风险因子出现高位共振，应立即开展深度尽调与风险敞口评估。",
    }
    return f"{messages[system['state']]} 当前贡献较高的因子为：{names}。"


def _state_text(item):
    return item["state"] if item.get("available") else "数据不足"


def _conclusion_report(system, results):
    """Compile the six factor readings into one causal, reader-facing brief."""
    s1, s2, s3 = results["straw1"], results["straw2"], results["straw3"]
    s4, s5, s6 = results["straw4"], results["straw5"], results["straw6"]
    paragraphs = [
        f'<p class="conclusion-summary">{escape(_conclusion(system, results))}</p>',
        (
            '<p><b>核心驱动：</b>资本开支偏离处于 '
            f'<strong>{escape(_state_text(s1))}</strong>，{escape(s1["detail"])}；'
            f'开源商业化压缩同处于 <strong>{escape(_state_text(s2))}</strong>，'
            '说明高投入与商业化承压正在同时出现，盈利兑现速度是当前风险链的首要矛盾。</p>'
        ),
        (
            '<p><b>资产与供给约束：</b>数据中心资产减值和 AI 能源约束分别处于 '
            f'<strong>{escape(_state_text(s3))} / {escape(_state_text(s4))}</strong>。'
            'GPU 适配、相关资产价格、电网排队、成本与效率信号已进入观察区，但尚未形成危机级共振；'
            '若资本开支继续领先需求，这两项会放大折旧、改造和交付压力。</p>'
        ),
        (
            '<p><b>金融传导与宏观缓冲：</b>AI 融资闭环处于 '
            f'<strong>{escape(_state_text(s5))}</strong>，期限错配、资本角色重叠与证券化传染是主要传导路径；'
            f'宏观市场预警为 <strong>{escape(_state_text(s6))}</strong>，该因子依据金融压力、信用利差、金融条件、'
            '股票动量与期限曲线判断跨市场压力是否共振；外生冲击仍需独立监测。</p>'
        ),
    ]
    return "".join(paragraphs)

with st.spinner("正在汇总六个风险因子…"):
    results = load_factor_results()
system = aggregate_factor_results(results)
scores = {key: item["score"] for key, item in results.items() if item.get("available")}

st.markdown(f"""<div class="dashboard-header"><div><div class="main-title">📡 Compute-Dollar Risk Terminal</div>
<div class="sub-title">美元—算力系统性风险监测 · 六维风险综合评估</div></div>
<span class="timestamp-text">🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>""", unsafe_allow_html=True)
st.markdown(render_system_card(scores, system_result=system), unsafe_allow_html=True)

color = STATE_COLORS.get(system["state"], "#94a3b8")
conclusion_col, factor_col = st.columns(2, gap="medium")
with conclusion_col:
    st.markdown(f"""<div class="dashboard-conclusion"><div class="conclusion-eyebrow">综合结论</div>
<div class="conclusion-state" style="color:{color};">{escape(system['state'])}</div>
<div class="conclusion-copy conclusion-report">{_conclusion_report(system, results)}</div>
<div class="conclusion-note">有效权重覆盖率 {system['coverage']}% · 缺失因子不按安全或中性分处理</div></div>""", unsafe_allow_html=True)
with factor_col:
    with st.container(border=True):
        render_factor_navigation(scores, results=results)

source_items = []
for key in ("straw1", "straw2", "straw3", "straw4", "straw5", "straw6"):
    item = results[key]
    availability = f"{item['coverage']:.0f}%" if item["available"] else "不可用"
    source_items.append(f'<div class="source-status"><b>{escape(item["name"])}</b><span>{availability}</span><small>{escape(item["source"])}</small></div>')
st.markdown('<div class="source-strip"><div class="compact-title">数据覆盖与来源</div>' + "".join(source_items) + "</div>", unsafe_allow_html=True)

if st.button("刷新全部因子数据", use_container_width=False):
    st.cache_data.clear()
    st.rerun()
render_footer("六个风险因子自动汇总 · 缺失值不填 0、不填 50 · 数据缓存 1 小时")
