"""AI financing loop and securitization contagion risk."""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from components.ui import load_css, metric_card, render_data_freshness, render_footer, render_header
from config.thresholds import STATE_COLORS
from core.alert_engine import render_alert, render_osci_card
from core.factor_registry import load_factor_results
from core.score_engine import register_score
from core.straw5_engine import SOURCES, STATIC_INPUTS, load_straw5_analysis, state_for


st.set_page_config(page_title="AI融资闭环风险", layout="wide")
load_css()


def _color_class(state: str) -> str:
    return {"SAFE": "green", "WATCH": "yellow", "WARNING": "orange", "CRITICAL": "red"}.get(state, "gray")


def _component_card(label: str, component: dict, detail: str, badge: str = "") -> str:
    score = component.get("score")
    label_html = f'{label} <span class="source-tag-warn static-data-badge">{badge}</span>' if badge else label
    if score is None:
        return metric_card(label_html, "N/A", "gray", "—", f"数据未覆盖 · {detail}")
    state = state_for(score)
    return metric_card(label_html, f"{score:.1f}", _color_class(state), "", f"{state} · {detail}")


def _relationship_figure() -> go.Figure:
    labels = [
        "NVIDIA", "AI云/算力公司", "大客户", "资产/项目SPV", "银行与债券投资者", "数据中心设施"
    ]
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=labels,
            color=["#76b900", "#60a5fa", "#a78bfa", "#fbbf24", "#f97316", "#94a3b8"],
            pad=24,
            thickness=18,
            line=dict(color="#0b1120", width=1),
        ),
        link=dict(
            source=[0, 0, 2, 1, 4, 3],
            target=[1, 3, 1, 3, 3, 5],
            value=[4, 2, 4, 4, 5, 5],
            label=[
                "股权投资 + GPU供应", "容量兜底/信用支持", "take-or-pay合同",
                "合同与设备担保", "资产级贷款/担保票据", "建设与租赁融资",
            ],
            color=[
                "rgba(118,185,0,.35)", "rgba(118,185,0,.22)", "rgba(167,139,250,.28)",
                "rgba(96,165,250,.28)", "rgba(249,115,22,.28)", "rgba(251,191,36,.25)",
            ],
        ),
    ))
    fig.update_layout(
        height=430,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="#0b1120",
        plot_bgcolor="#0b1120",
        font=dict(color="#cbd5e1", size=13, family="Arial, PingFang SC, Microsoft YaHei"),
    )
    return fig


def _duration_figure() -> go.Figure:
    rows = [
        ("OEM融资期限（代表值）", 2.5, "#22c55e"),
        ("客户合同WAL", 4.0, "#60a5fa"),
        ("证券化预期偿还", 5.0, "#fbbf24"),
        ("GPU会计寿命", 6.0, "#a78bfa"),
        ("设施基础租约（样本）", 15.0, "#f97316"),
        ("证券化法定最终到期（中值）", 27.5, "#ef4444"),
    ]
    fig = go.Figure(go.Bar(
        x=[row[1] for row in rows],
        y=[row[0] for row in rows],
        orientation="h",
        marker_color=[row[2] for row in rows],
        text=[f"{row[1]:g}年" for row in rows],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x} 年<extra></extra>",
    ))
    fig.update_layout(
        height=430,
        margin=dict(l=12, r=45, t=20, b=45),
        paper_bgcolor="#0b1120",
        plot_bgcolor="#0b1120",
        font=dict(color="#cbd5e1", size=12, family="Arial, PingFang SC, Microsoft YaHei"),
        xaxis=dict(title="年", range=[0, 31], gridcolor="rgba(255,255,255,.07)", zeroline=False),
        yaxis=dict(autorange="reversed", gridcolor="rgba(255,255,255,0)"),
        showlegend=False,
    )
    return fig


render_header(
    "🏦 AI融资闭环风险",
    "核心监测维度：押在AI基础设施上的债务，在资本闭环与资产减值叠加下能否安全到期",
    symbol="AFSI · AI FINANCING STRESS",
)

with st.spinner("正在读取SEC季度基准、信用ETF代理与数据中心资产减值指数…"):
    factor_results = load_factor_results()
    dcoi_score = factor_results.get("straw3", {}).get("score") if factor_results.get("straw3", {}).get("available") else None
    analysis = load_straw5_analysis(dcoi_score)

score = analysis["score"]
state = analysis["state"]
color = STATE_COLORS.get(state, "#94a3b8")
market = analysis["market"]
confidence_cn = {"NORMAL": "正常置信度", "LOW CONFIDENCE": "低置信度", "INSUFFICIENT": "覆盖不足"}[analysis["confidence"]]
market_line = (
    f"HYG 3M {market['metrics']['hyg_3m_return']:+.1%} · HYXF相对 {market['metrics']['hyxf_relative']:+.1%}"
    if market["score"] is not None else "HYG/HYXF 当前不可用"
)

st.markdown(render_osci_card(
    "AFSI · AI FINANCING STRESS INDEX",
    score,
    state,
    f"综合评分：期限错配与资本闭环是结构主因；有效权重覆盖率 {analysis['coverage']}%。",
    state_detail=f"{confidence_cn} · {market_line}",
    components_html="期限错配 ×0.35 · 资本闭环 ×0.25<br>证券化传染 ×0.25 · 抵押品脆弱度 ×0.15",
    score_display=f"{score:.1f}",
), unsafe_allow_html=True)

components = analysis["components"]
cols = st.columns(4)
cards = [
    _component_card("期限错配 ×0.35", components["term_mismatch"], "合同、设备、租约与偿还期限", "⚠ 静态披露"),
    _component_card("资本闭环依赖 ×0.25", components["capital_loop"], "投资、供应、担保与购买角色重叠", "⚠ 静态披露"),
    _component_card("证券化传染 ×0.25", components["securitization"], "结构风险 + HYG/HYXF市场代理", "◐ 静态+实时"),
    _component_card("抵押品脆弱度 ×0.15", components["collateral"], "直接引用数据中心资产减值指数，不重复评分"),
]
for column, card in zip(cols, cards):
    with column:
        st.markdown(card, unsafe_allow_html=True)

straw1_state = factor_results.get("straw1", {}).get("state", "N/A")
straw3_state = factor_results.get("straw3", {}).get("state", "N/A")
cascade = (
    (state == "CRITICAL" and straw1_state in {"WARNING", "CRITICAL"})
    or (state in {"WARNING", "CRITICAL"} and straw3_state == "CRITICAL")
)
if cascade:
    title = "CASCADE：融资压力与上游风险已形成联动"
    body = f"融资闭环为 {state}，资本开支偏离为 {straw1_state}，资产减值为 {straw3_state}。应优先检查再融资、抵押品折价与容量兜底的共同敞口。"
else:
    title = {
        "SAFE": "融资结构尚未形成系统性压力",
        "WATCH": "结构性错配已出现，尚未触发级联预警",
        "WARNING": "融资闭环风险升高，但级联条件尚未同时满足",
        "CRITICAL": "融资风险处于高位，等待上游因子确认级联",
    }.get(state, "数据覆盖不足，暂不形成风险结论")
    body = (
        f"当前 AFSI {score:.1f}/100；资本开支偏离={straw1_state}，资产减值={straw3_state}。"
        "融资闭环因子单独不会触发 CASCADE；只有与资本开支偏离或抵押品减值共同恶化时才升级。"
    )
st.markdown(render_alert("CRITICAL" if cascade else state, title, body), unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    st.markdown('<div class="panel-title">🔗 融资关系与风险传导</div>', unsafe_allow_html=True)
    st.plotly_chart(_relationship_figure(), use_container_width=True, config={"displayModeBar": False})
    st.caption("关系图为结构示意，连线宽度表达关系类型，不代表美元金额。")
with right:
    st.markdown('<div class="panel-title">⏳ 期限阶梯与错配窗口</div>', unsafe_allow_html=True)
    st.plotly_chart(_duration_figure(), use_container_width=True, config={"displayModeBar": False})
    st.caption("期限来自不同披露与行业样本，用于识别结构错配，不表示同一项目的完整现金流表。")

tab1, tab2, tab3 = st.tabs(["检测逻辑", "实体与结构证据", "数据覆盖与来源"])
with tab1:
    st.markdown(f"""
<div class="panel">
  <div class="panel-title">⚙️ AFSI 评分逻辑</div>
  <div class="logic-step"><div class="step-num">1</div><div class="step-text"><b>期限错配（35%）</b>：合同WAL与GPU寿命、设施租约及债务尾部期限的缺口。</div></div>
  <div class="logic-step"><div class="step-num">2</div><div class="step-text"><b>资本闭环（25%）</b>：投资者、供应商、容量兜底方与信用支持方是否重叠。</div></div>
  <div class="logic-step"><div class="step-num">3</div><div class="step-text"><b>证券化传染（25%）</b>：40%结构证据 + 60% HYG/HYXF市场代理。ETF不是AI数据中心ABS直接利差。</div></div>
  <div class="logic-step"><div class="step-num">4</div><div class="step-text"><b>抵押品脆弱度（15%）</b>：直接引用数据中心资产减值指数；前者看资产是否过时，本页看债务有多少依赖这些资产。</div></div>
  <div class="logic-step"><div class="step-num">5</div><div class="step-text"><b>缺失值政策</b>：按可用权重重算；覆盖≥75%正常，50–75%标注LOW CONFIDENCE，低于50%输出N/A。</div></div>
  <div class="threshold-block">
    <div class="threshold-row"><div class="t-dot" style="background:#22c55e"></div><div class="t-label">0–24.9</div><div class="t-arrow">→</div><div class="t-status green">SAFE</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#fbbf24"></div><div class="t-label">25–49.9</div><div class="t-arrow">→</div><div class="t-status yellow">WATCH</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#f97316"></div><div class="t-label">50–74.9</div><div class="t-arrow">→</div><div class="t-status orange">WARNING</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#ef4444"></div><div class="t-label">75–100</div><div class="t-arrow">→</div><div class="t-status red">CRITICAL</div></div>
  </div>
</div>""", unsafe_allow_html=True)

with tab2:
    market_value = market_line if market["score"] is not None else f"不可用：{market.get('error') or '未知原因'}"
    st.markdown(f"""
<div class="panel"><div class="panel-title">📋 当前覆盖实体与证据链</div>
<table class="gpu-table"><thead><tr><th>对象</th><th>可观察结构</th><th>本页用途</th><th>状态</th></tr></thead><tbody>
<tr><td>CoreWeave</td><td>约4年合同WAL、6年GPU会计寿命、资产级担保融资</td><td>期限错配 / 抵押品</td><td class="gpu-gen-active">已覆盖</td></tr>
<tr><td>NVIDIA ↔ CoreWeave</td><td>股权、GPU供应、容量与信用支持角色重叠</td><td>资本闭环</td><td class="gpu-gen-active">已覆盖</td></tr>
<tr><td>Helios / Galaxy</td><td>15年基础租约与剩余容量购买安排</td><td>长期承诺样本</td><td class="gpu-gen-active">已覆盖</td></tr>
<tr><td>数据中心证券化</td><td>约5年预期偿还、25–30年法定最终到期的行业结构</td><td>尾部再融资风险</td><td class="gpu-gen-active">行业代理</td></tr>
<tr><td>HYG / HYXF</td><td>{escape(market_value)}</td><td>信用市场传染代理</td><td>{'已更新 '+escape(market['updated']) if market['updated'] else 'N/A'}</td></tr>
</tbody></table></div>""", unsafe_allow_html=True)

with tab3:
    source_rows = "".join(
        f'<tr><td><a href="{escape(item["url"])}" target="_blank">{escape(item["item"])}</a></td>'
        f'<td>{escape(item["period"])}</td><td>{escape(item["cadence"])}</td><td>{escape(item["note"])}</td></tr>'
        for item in SOURCES
    )
    render_data_freshness([
        {"name": "信用市场代理", "source": "Yahoo Finance · HYG / HYXF", "updated_at": market.get("updated") or "不可用", "mode": "live" if market.get("updated") else "fallback"},
        {"name": "融资结构证据", "source": "SEC公司披露与行业函件", "updated_at": STATIC_INPUTS["as_of"], "mode": "static"},
        {"name": "抵押品脆弱度", "source": "数据中心资产减值指数联动", "updated_at": "每小时缓存", "mode": "live"},
    ])
    st.markdown(f"""<div class="panel"><div class="metric-desc">有效权重覆盖率 <b style="color:{color};">{analysis['coverage']}%</b> · {confidence_cn}</div>
<table class="gpu-table"><thead><tr><th>数据项</th><th>期间</th><th>更新节奏</th><th>解释</th></tr></thead><tbody>{source_rows}</tbody></table>
<div class="metric-sub">私人AI云披露不足时保留“未披露”，不会默认SAFE。</div></div>""", unsafe_allow_html=True)

if score is not None:
    register_score("straw5", score)

render_footer("SEC公司披露与行业函件（季度静态维护） · Yahoo Finance HYG/HYXF（小时缓存） · 数据中心资产减值指数")
