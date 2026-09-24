"""Factor 06 — AI credit and refinancing pressure."""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from components.ui import (load_css, logic_panel, metric_card, panel,
                           render_data_freshness, render_footer, render_header,
                           spacer)
from config.thresholds import STATE_COLORS
from core.alert_engine import render_alert, render_osci_card
from core.credit_risk import COMPONENTS, compute_credit_metrics
from core.macro_data import load_credit_stress_snapshot
from core.score_engine import register_score


st.set_page_config(page_title="AI信贷与再融资压力", layout="wide", initial_sidebar_state="expanded")
load_css()


CREDIT_EVENTS = [
    ("1998-08", "俄罗斯违约与LTCM危机", "主权违约与高杠杆头寸冲击全球流动性。"),
    ("2002-07", "企业信用危机", "电信与科技企业去杠杆推动公司债压力上升。"),
    ("2007-08", "次贷信用显性化", "结构化信用产品和银行间融资风险开始外溢。"),
    ("2008-09", "雷曼破产", "融资链冻结并触发全球信用利差急剧扩大。"),
    ("2011-08", "欧债与美国评级冲击", "主权信用担忧推高全球避险与融资压力。"),
    ("2015-12", "能源高收益债危机", "能源债违约风险上升，而股票市场跌幅相对有限。"),
    ("2020-03", "美元流动性冲击", "疫情冲击导致信用市场和短期融资市场迅速失灵。"),
    ("2022-06", "加息与科技信用重估", "实际利率上升压缩久期资产与高增长企业融资空间。"),
    ("2023-03", "美国区域银行危机", "久期错配和存款外流冲击银行信用传导。"),
]


AI_DEALS = [
    {
        "date": "2026-09-21",
        "issuer": "SoftBank Group",
        "purpose": "拟为OpenAI后续投资及相关融资安排发行多币种债券",
        "size": "约111.5亿美元（待最终发行确认）",
        "pricing": "等待最终收益率、国债利差、认购倍数与二级市场表现",
        "status": "观察中",
        "source": "https://www.reuters.com/business/media-telecom/softbank-group-launches-over-10-billion-bonds-openai-investment-term-sheet-shows-2026-09-21/",
    }
]


def _color_class(state: str) -> str:
    return {"SAFE": "green", "WATCH": "yellow", "WARNING": "orange", "CRITICAL": "red"}.get(state, "gray")


def _latest_date(series: pd.Series) -> str | None:
    if series is None or series.empty:
        return None
    stamp = min(pd.Timestamp(series.dropna().index[-1]).normalize(), pd.Timestamp.now().normalize())
    return stamp.strftime("%Y-%m-%d")


def _as_of(series: pd.Series, month: str) -> pd.Series:
    if series is None or series.empty:
        return pd.Series(dtype=float)
    cutoff = pd.Period(month, freq="M") - 3
    indexed = series.copy()
    indexed.index = pd.to_datetime(indexed.index).to_period("M")
    return indexed[indexed.index <= cutoff]


def _history_rows(series: dict[str, pd.Series]) -> list[dict]:
    rows = []
    for month, event, description in CREDIT_EVENTS:
        metrics = compute_credit_metrics(
            _as_of(series["hy_oas"], month),
            _as_of(series["real_yield"], month),
            _as_of(series["nfci"], month),
            baa_spread=_as_of(series["baa10y"], month),
        )
        composite = metrics["composite"]
        credit = metrics.get("credit_spread")
        rows.append({
            "month": month,
            "event": event,
            "description": description,
            "score": composite["score"],
            "state": composite["grade"],
            "coverage": composite["coverage"],
            "credit": "N/A" if not credit else f"{credit['value']:.0f}bp · {credit.get('proxy', '')}",
            "real": "N/A" if "real_rate" not in metrics else f"{metrics['real_rate']['value']:.2f}%",
            "nfci": "N/A" if "financial_conditions" not in metrics else f"{metrics['financial_conditions']['value']:+.2f}",
        })
    return rows


def _stress_chart(series: dict[str, pd.Series]) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        subplot_titles=("信用利差", "10Y实际利率", "NFCI金融条件"),
    )
    if not series["baa10y"].empty:
        fig.add_trace(go.Scatter(x=series["baa10y"].index, y=series["baa10y"] * 100,
                                 name="BAA−10Y长期代理", line=dict(color="#60a5fa", width=2)), row=1, col=1)
    if not series["hy_oas"].empty:
        fig.add_trace(go.Scatter(x=series["hy_oas"].index, y=series["hy_oas"] * 100,
                                 name="HY OAS", line=dict(color="#f97316", width=2.5)), row=1, col=1)
    if not series["real_yield"].empty:
        fig.add_trace(go.Scatter(x=series["real_yield"].index, y=series["real_yield"],
                                 name="10Y TIPS", line=dict(color="#fbbf24", width=2)), row=2, col=1)
    if not series["nfci"].empty:
        fig.add_trace(go.Scatter(x=series["nfci"].index, y=series["nfci"],
                                 name="NFCI", line=dict(color="#a78bfa", width=2)), row=3, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,.25)", row=3, col=1)
    fig.update_yaxes(title_text="bp", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    fig.update_yaxes(title_text="指数", row=3, col=1)
    fig.update_layout(
        height=720,
        paper_bgcolor="#0b1120",
        plot_bgcolor="#0b1120",
        font=dict(color="#e2e8f0", size=14, family="Arial, PingFang SC, Microsoft YaHei"),
        margin=dict(l=40, r=20, t=55, b=30),
        hovermode="x unified",
        legend=dict(
            orientation="h", y=1.08, x=0,
            font=dict(color="#f8fafc", size=15, family="Arial, PingFang SC, Microsoft YaHei"),
            bgcolor="rgba(11,17,32,.88)",
        ),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.05)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,.05)", zeroline=False)
    return fig


render_header(
    "💳 AI信贷与再融资压力",
    "核心监测维度：外部信用市场是否正在提高AI项目融资成本或关闭再融资窗口",
    symbol="CFRI · CREDIT & REFINANCING",
)

with st.spinner("正在读取信用利差、实际利率与金融条件数据…"):
    series, source = load_credit_stress_snapshot()
metrics = compute_credit_metrics(
    series["hy_oas"], series["real_yield"], series["nfci"],
    baa_spread=series["baa10y"],
)
composite = metrics["composite"]
score, state = composite["score"], composite["grade"]
if score is not None:
    register_score("straw6", score)

summary = {
    "SAFE": "广泛信用利差与融资条件尚未显示系统性收紧。",
    "WATCH": "实际融资成本或信用条件已出现早期压力。",
    "WARNING": "信用利差、实际利率或金融条件正在显著压缩再融资空间。",
    "CRITICAL": "信用市场与融资条件已进入危机级收紧区间。",
}.get(state, "有效数据覆盖不足，暂不输出方向性判断。")
st.markdown(render_osci_card(
    "CFRI · AI CREDIT & REFINANCING PRESSURE",
    score, state, f"综合评分：{summary}",
    bar_color=STATE_COLORS.get(state, "#94a3b8"),
    state_detail=f"有效权重覆盖率 {composite['coverage']}% · AI交易定价尚未纳入评分",
    components_html="信用利差 ×0.35 · 10Y实际利率 ×0.30<br>NFCI金融条件 ×0.25 · AI融资交易温度 ×0.10",
    score_display="N/A" if score is None else f"{score:.1f}",
), unsafe_allow_html=True)

columns = st.columns(4)
for column, key in zip(columns, COMPONENTS):
    definition = COMPONENTS[key]
    item = metrics.get(key)
    with column:
        if item is None:
            desc = "等待足够的发行定价与二级市场数据" if key == "ai_deal" else "数据缺失，不按SAFE处理"
            st.markdown(metric_card(f"{definition['label']} ×{definition['weight']:.2f}", "N/A", "gray", desc=desc), unsafe_allow_html=True)
            continue
        if key == "credit_spread":
            value = f"{item['value']:.0f}bp"
            change = "" if item["change"] is None else f"3M {item['change']:+.0f}bp"
            desc = f"当前 {item['grade']} · {item.get('proxy', '')}<br>{change}"
        elif key == "real_rate":
            value = f"{item['value']:.2f}%"
            change = "" if item["change"] is None else f"3M {item['change']:+.0f}bp"
            desc = f"当前 {item['grade']}<br>{change}"
        else:
            value = f"{item['value']:+.2f}"
            change = "" if item["change"] is None else f"13周 {item['change']:+.2f}"
            desc = f"当前 {item['grade']}<br>{change}"
        st.markdown(metric_card(f"{definition['label']} ×{definition['weight']:.2f}", value,
                                _color_class(item["grade"]), desc=desc), unsafe_allow_html=True)

alert_title = {
    "SAFE": "信用市场尚未确认AI融资压力",
    "WATCH": "融资成本抬升，但信用窗口仍然开放",
    "WARNING": "再融资压力上升，需要检查发行与续作条件",
    "CRITICAL": "信用窗口显著收缩，进入融资危机状态",
}.get(state, "数据覆盖不足")
alert_body = (
    f"当前CFRI为 {'N/A' if score is None else f'{score:.1f}/100'}。"
    "广泛信用条件和单一AI发行人的定价必须分开解释；单笔债券事件不会被手工写入总分。"
)
st.markdown(render_alert(state, alert_title, alert_body), unsafe_allow_html=True)

st.markdown(spacer("sm"), unsafe_allow_html=True)
st.markdown(panel("📈 信用与融资条件历史", '<div class="history-help">HY OAS用于实时监控；BAA−10Y用于长历史参照。两者口径不同，不拼接成一条伪造序列。</div>'), unsafe_allow_html=True)
st.plotly_chart(_stress_chart(series), use_container_width=True, config={"displayModeBar": False})

deal_rows = "".join(
    f'<tr><td>{escape(item["date"])}</td><td><a href="{escape(item["source"])}" target="_blank">{escape(item["issuer"])}</a></td>'
    f'<td>{escape(item["purpose"])}</td><td>{escape(item["size"])}</td><td>{escape(item["pricing"])}</td><td>{escape(item["status"])}</td></tr>'
    for item in AI_DEALS
)
st.markdown(
    '<div class="panel"><div class="panel-title">🏦 AI融资交易观察</div><table class="gpu-table"><thead><tr><th>日期</th><th>发行人</th><th>用途</th><th>规模</th><th>待观察定价</th><th>状态</th></tr></thead>'
    f'<tbody>{deal_rows}</tbody></table><div class="metric-sub">只有最终收益率、国债利差、同评级溢价、认购倍数和二级市场表现齐备后，交易温度才进入评分。</div></div>',
    unsafe_allow_html=True,
)

history_rows = _history_rows(series)
body = []
for row in history_rows:
    color = STATE_COLORS.get(row["state"], "#94a3b8")
    score_text = "N/A" if row["score"] is None else f"{row['score']:.1f}/100"
    body.append(
        f'<tr><td>{row["month"]}</td><td><b>{escape(row["event"])}</b><br><small>{escape(row["description"])}</small></td>'
        f'<td>{row["credit"]}</td><td>{row["real"]}</td><td>{row["nfci"]}</td>'
        f'<td style="color:{color};font-weight:800">{row["state"]}<br>{score_text}</td><td>{row["coverage"]}%</td></tr>'
    )
st.markdown(
    '<div class="panel"><div class="panel-title">📋 历史信用事件复盘</div>'
    '<div class="history-help">全部状态只使用事件前三个月已经可获得的数据。早期事件数据覆盖不足时显示N/A，不补写安全分。</div>'
    '<table class="gpu-table"><thead><tr><th>事件时间</th><th>信用事件</th><th>信用利差</th><th>实际利率</th><th>NFCI</th><th>事前状态</th><th>覆盖率</th></tr></thead>'
    f'<tbody>{"".join(body)}</tbody></table></div>', unsafe_allow_html=True,
)

st.markdown(logic_panel([
    {"text": "<b>信用利差（35%）</b>：实时优先采用HY OAS；长历史仅用BAA−10Y代理并明确标注，不混合口径。"},
    {"text": "<b>实际利率（30%）</b>：10Y TIPS水平占70%，三个月变化占30%，用于衡量项目NPV和真实资金成本。"},
    {"text": "<b>NFCI（25%）</b>：水平占60%，13周变化占40%；正值表示金融条件较长期平均更紧。"},
    {"text": "<b>AI融资交易温度（10%）</b>：只有可比较的最终定价与市场表现齐备时才计分。"},
    {"text": "<b>覆盖政策</b>：有效权重不足75%时输出N/A；缺失指标绝不按SAFE或零分处理。"},
], title="⚙️ CFRI评分逻辑"), unsafe_allow_html=True)

render_data_freshness([
    {"name": "高收益信用利差", "source": "FRED · BAMLH0A0HYM2", "updated_at": _latest_date(series["hy_oas"]), "mode": "live"},
    {"name": "长期信用代理", "source": "FRED · BAA10Y", "updated_at": _latest_date(series["baa10y"]), "mode": "live"},
    {"name": "实际利率", "source": "FRED · DFII10", "updated_at": _latest_date(series["real_yield"]), "mode": "live"},
    {"name": "金融条件", "source": "FRED · NFCI", "updated_at": _latest_date(series["nfci"]), "mode": "live"},
    {"name": "AI融资交易", "source": "发行文件与可信新闻；当前等待最终定价", "updated_at": "2026-09-21", "mode": "static"},
])
render_footer(f"{source} · 发行文件与事件驱动信息")
