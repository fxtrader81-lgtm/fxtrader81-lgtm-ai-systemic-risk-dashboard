"""Factor 05 — structural AI financing vulnerability."""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from components.ui import (coverage_panel, load_css, logic_panel, metric_card,
                           render_data_freshness, render_footer, render_header)
from config.thresholds import STATE_COLORS
from core.alert_engine import render_alert, render_osci_card
from core.factor_registry import load_factor_results
from core.score_engine import register_score
from core.straw5_engine import SOURCES, STATIC_INPUTS, load_straw5_analysis, state_for


st.set_page_config(page_title="AI融资结构脆弱性", layout="wide")
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
    "🏦 AI融资结构脆弱性",
    "核心监测维度：押在AI基础设施上的债务，在资本闭环与资产减值叠加下能否安全到期",
    symbol="AFVI · AI FINANCING VULNERABILITY",
)

with st.spinner("正在读取SEC季度基准、融资结构证据与数据中心资产减值指数…"):
    factor_results = load_factor_results()
    dcoi_score = factor_results.get("straw3", {}).get("score") if factor_results.get("straw3", {}).get("available") else None
    analysis = load_straw5_analysis(dcoi_score)

score = analysis["score"]
state = analysis["state"]
color = STATE_COLORS.get(state, "#94a3b8")
confidence_cn = {"NORMAL": "正常置信度", "LOW CONFIDENCE": "低置信度", "INSUFFICIENT": "覆盖不足"}[analysis["confidence"]]

st.markdown(render_osci_card(
    "AFVI · AI FINANCING VULNERABILITY INDEX",
    score,
    state,
    f"综合评分：期限错配与资本闭环是结构主因；有效权重覆盖率 {analysis['coverage']}%。",
    state_detail=f"{confidence_cn} · 本页不使用信用市场价格，市场触发由因子06负责",
    components_html="期限错配 ×0.35 · 资本闭环 ×0.25<br>证券化与契约结构 ×0.20 · 抵押品脆弱度 ×0.20",
    score_display=f"{score:.1f}",
), unsafe_allow_html=True)

components = analysis["components"]
cols = st.columns(4)
cards = [
    _component_card("期限错配 ×0.35", components["term_mismatch"], "合同、设备、租约与偿还期限", "⚠ 静态披露"),
    _component_card("资本闭环依赖 ×0.25", components["capital_loop"], "投资、供应、担保与购买角色重叠", "⚠ 静态披露"),
    _component_card("证券化与契约结构 ×0.20", components["securitization"], "偿还期限、契约与尾部再融资结构", "⚠ 静态披露"),
    _component_card("抵押品脆弱度 ×0.20", components["collateral"], "直接引用数据中心资产减值指数，不重复计算底层信号"),
]
for column, card in zip(cols, cards):
    with column:
        st.markdown(card, unsafe_allow_html=True)

credit_state = factor_results.get("straw6", {}).get("state", "N/A")
market_state = factor_results.get("straw7", {}).get("state", "N/A")
cascade = state in {"WARNING", "CRITICAL"} and credit_state in {"WARNING", "CRITICAL"} and market_state in {"WATCH", "WARNING", "CRITICAL"}
critical_cascade = cascade and (state == "CRITICAL" or credit_state == "CRITICAL") and market_state in {"WARNING", "CRITICAL"}
if cascade:
    title = "CRITICAL CASCADE：融资结构、信用与市场同步恶化" if critical_cascade else "CASCADE：融资结构脆弱性已向信用和市场传导"
    body = f"融资结构={state}，信贷与再融资={credit_state}，宏观市场确认={market_state}。应优先检查再融资、抵押品折价与容量兜底的共同敞口。"
else:
    title = {
        "SAFE": "融资结构尚未形成系统性压力",
        "WATCH": "结构性错配已出现，尚未触发级联预警",
        "WARNING": "融资结构风险升高，但信用与市场尚未同时确认",
        "CRITICAL": "融资结构处于高位，等待外部信用与市场确认",
    }.get(state, "数据覆盖不足，暂不形成风险结论")
    body = (
        f"当前 AFVI {score:.1f}/100；信贷与再融资={credit_state}，宏观市场确认={market_state}。"
        "只有05达到WARNING、06达到WARNING且07至少WATCH时才触发CASCADE。"
    )
st.markdown(render_alert("CRITICAL" if critical_cascade else "WARNING" if cascade else state, f"结论：{title}", body), unsafe_allow_html=True)

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
    st.markdown(logic_panel([
        {"text": "<b>期限错配（35%）</b>：合同WAL与GPU寿命、设施租约及债务尾部期限的缺口。"},
        {"text": "<b>资本闭环（25%）</b>：投资者、供应商、容量兜底方与信用支持方是否重叠。"},
        {"text": "<b>证券化与契约结构（20%）</b>：预期偿还、法定最终到期、契约和担保结构；不再混入HYG/HYXF价格。"},
        {"text": "<b>抵押品脆弱度（20%）</b>：直接引用数据中心资产减值指数；前者看资产是否过时，本页看债务有多少依赖这些资产。"},
        {"text": "<b>缺失值政策</b>：按可用权重重算；覆盖≥75%正常，50–75%标注LOW CONFIDENCE，低于50%输出N/A。", "thresholds": [
            ("#22c55e", "0–24.9", "SAFE", "green"),
            ("#fbbf24", "25–49.9", "WATCH", "yellow"),
            ("#f97316", "50–74.9", "WARNING", "orange"),
            ("#ef4444", "75–100", "CRITICAL", "red"),
        ]},
    ], title="⚙️ AFSI 评分逻辑"), unsafe_allow_html=True)

with tab2:
    st.markdown(f"""
<div class="panel"><div class="panel-title">📋 当前覆盖实体与证据链</div>
<table class="gpu-table"><thead><tr><th>对象</th><th>可观察结构</th><th>本页用途</th><th>状态</th></tr></thead><tbody>
<tr><td>CoreWeave</td><td>约4年合同WAL、6年GPU会计寿命、资产级担保融资</td><td>期限错配 / 抵押品</td><td class="gpu-gen-active">已覆盖</td></tr>
<tr><td>NVIDIA ↔ CoreWeave</td><td>股权、GPU供应、容量与信用支持角色重叠</td><td>资本闭环</td><td class="gpu-gen-active">已覆盖</td></tr>
<tr><td>Helios / Galaxy</td><td>15年基础租约与剩余容量购买安排</td><td>长期承诺样本</td><td class="gpu-gen-active">已覆盖</td></tr>
<tr><td>数据中心证券化</td><td>约5年预期偿还、25–30年法定最终到期的行业结构</td><td>尾部再融资风险</td><td class="gpu-gen-active">行业代理</td></tr>
<tr><td>市场价格信号</td><td>已迁移至因子06：AI信贷与再融资压力</td><td>避免结构与市场重复计分</td><td class="gpu-gen-active">已拆分</td></tr>
</tbody></table></div>""", unsafe_allow_html=True)

with tab3:
    source_rows = "".join(
        f'<tr><td><a href="{escape(item["url"])}" target="_blank">{escape(item["item"])}</a></td>'
        f'<td>{escape(item["period"])}</td><td>{escape(item["cadence"])}</td><td>{escape(item["note"])}</td></tr>'
        for item in SOURCES
    )
    render_data_freshness([
        {"name": "融资结构证据", "source": "SEC公司披露与行业函件", "updated_at": STATIC_INPUTS["as_of"], "mode": "static"},
        {"name": "抵押品脆弱度", "source": "数据中心资产减值指数联动", "updated_at": "每小时缓存", "mode": "live"},
    ])
    evidence_table = f'<table class="gpu-table"><thead><tr><th>数据项</th><th>期间</th><th>更新节奏</th><th>解释</th></tr></thead><tbody>{source_rows}</tbody></table>'
    st.markdown(coverage_panel(analysis["coverage"], confidence_cn, color, evidence_table,
                               "私人AI云披露不足时保留“未披露”，不会默认SAFE。"), unsafe_allow_html=True)

if score is not None:
    register_score("straw5", score)

render_footer("SEC公司披露与行业函件（季度静态维护） · 数据中心资产减值指数 · 市场价格信号见因子06")
