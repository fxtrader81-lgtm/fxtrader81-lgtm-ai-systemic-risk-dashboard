"""Compute-Dollar Risk Terminal — source-backed system overview."""

from html import escape

import streamlit as st

from components.ui import (dashboard_conclusion, dashboard_header, load_css,
                           metric_card, render_footer, source_strip)
from config.thresholds import STATE_COLORS, STRAW_WEIGHTS
from core.factor_registry import aggregate_factor_results, load_factor_results
from core.score_engine import render_factor_navigation, render_system_card

load_css()

def _conclusion(system, results):
    if not system["available"]:
        return "当前有效数据覆盖不足，系统暂不输出方向性结论。"
    leaders = sorted(
        (results[key] for key in STRAW_WEIGHTS if results.get(key, {}).get("available")),
        key=lambda x: x["score"], reverse=True,
    )[:2]
    names = "、".join(x["name"] for x in leaders)
    messages = {
        "SAFE": "AI结构性风险因子整体处于正常区间。",
        "WATCH": "AI结构层已出现早期信号，建议提高数据刷新和交叉验证频率。",
        "WARNING": "多项AI结构因子同步抬升；是否向金融市场传导，需结合06与07判断。",
        "CRITICAL": "AI结构脆弱性处于高位；只有信贷和市场同步确认时才进入CASCADE。",
    }
    return f"{messages[system['state']]} 当前贡献较高的因子为：{names}。"


def _state_text(item):
    return item["state"] if item.get("available") else "数据不足"


def _conclusion_report(system, results):
    """Compile seven factor readings into one causal, reader-facing brief."""
    s1, s2, s3 = results["straw1"], results["straw2"], results["straw3"]
    s4, s5 = results["straw4"], results["straw5"]
    s6, s7 = results["straw6"], results["straw7"]
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
            '<p><b>融资结构与外部信用：</b>AI 融资结构脆弱性处于 '
            f'<strong>{escape(_state_text(s5))}</strong>，期限错配、资本角色重叠与证券化传染是主要传导路径；'
            f'AI信贷与再融资压力为 <strong>{escape(_state_text(s6))}</strong>，依据信用利差、实际利率与金融条件判断融资窗口。</p>'
        ),
        (
            '<p><b>市场确认：</b>宏观与跨市场预警为 '
            f'<strong>{escape(_state_text(s7))}</strong>，依据股票动量与回撤、VIX、利率冲击、金融市场压力与期限曲线判断。'
            f'当前阶段为 <strong>{escape(system.get("phase", "常态监测"))}</strong>；外生冲击仍需独立监测。</p>'
        ),
    ]
    return "".join(paragraphs)

with st.spinner("正在汇总七个风险因子…"):
    results = load_factor_results()
system = aggregate_factor_results(results)
scores = {key: item["score"] for key, item in results.items() if item.get("available")}

st.markdown(
    dashboard_header(
        "📡 Compute-Dollar Risk Terminal",
        "美元—算力系统性风险监测 · 七维风险分层评估",
    ),
    unsafe_allow_html=True,
)
st.markdown(render_system_card(scores, system_result=system), unsafe_allow_html=True)

credit, market = results["straw6"], results["straw7"]
credit_color = {"SAFE": "green", "WATCH": "yellow", "WARNING": "orange", "CRITICAL": "red"}.get(credit["state"], "gray")
market_color = {"SAFE": "green", "WATCH": "yellow", "WARNING": "orange", "CRITICAL": "red"}.get(market["state"], "gray")
phase_color = "red" if system.get("critical_cascade") else "orange" if system.get("cascade") else "yellow" if "压力" in system.get("phase", "") else "blue"
credit_score_text = "N/A" if credit["score"] is None else f'{credit["score"]:.0f}/100'
market_score_text = "N/A" if market["score"] is None else f'{market["score"]:.0f}/100'
phase_full = system.get("phase", "常态监测")
phase_short = {
    "结构性积累期，尚未市场传导": "结构性积累",
    "结构高风险，市场承压但信贷未确认": "传导待确认",
    "宏观压力，AI体系暂时隔离": "宏观压力隔离",
    "融资压力观察期": "融资压力观察",
    "CASCADE 联动": "CASCADE",
    "危机传导期": "危机传导",
}.get(phase_full, phase_full)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(metric_card("06 · AI信贷与再融资压力", credit["state"], credit_color,
                            desc=f"{credit_score_text} · 外部融资触发层"), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card("07 · 宏观与跨市场预警", market["state"], market_color,
                            desc=f"{market_score_text} · 市场确认放大层"), unsafe_allow_html=True)
with c3:
    st.markdown(metric_card("系统传导阶段", phase_short, phase_color,
                            desc=f"{phase_full}<br>CASCADE要求05与06均达WARNING，且07至少WATCH"), unsafe_allow_html=True)

color = STATE_COLORS.get(system["state"], "#94a3b8")
conclusion_col, factor_col = st.columns(2, gap="medium")
with conclusion_col:
    st.markdown(dashboard_conclusion(system["state"], color, _conclusion_report(system, results),
                                     system["coverage"]), unsafe_allow_html=True)
with factor_col:
    with st.container(border=True):
        render_factor_navigation(scores, results=results)

source_items = []
for key in ("straw1", "straw2", "straw3", "straw4", "straw5", "straw6", "straw7"):
    item = results[key]
    availability = f"{item['coverage']:.0f}%" if item["available"] else "不可用"
    source_items.append({"name": item["name"], "availability": availability, "source": item["source"]})
st.markdown(source_strip(source_items), unsafe_allow_html=True)

if st.button("刷新全部因子数据", use_container_width=False):
    st.cache_data.clear()
    st.rerun()
render_footer("七个风险因子分层监测 · 结构总分仅汇总01–05 · 缺失值不填0、不填50 · 数据缓存1小时")
