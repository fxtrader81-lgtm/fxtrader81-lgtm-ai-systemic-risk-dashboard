"""Factor 06 — AI credit and refinancing pressure."""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from components.ui import (load_css, logic_panel, metric_card, model_evidence_panel, panel,
                           render_data_freshness, render_footer, render_header,
                           spacer)
from config.thresholds import STATE_COLORS
from core.alert_engine import render_alert, render_osci_card
from core.credit_history import build_credit_history_rows
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
        "date": "2026-09-24",
        "issuer": "SoftBank Group",
        "purpose": "美元债100亿美元及欧元债10亿欧元；主要用于OpenAI后续100亿美元投资",
        "size": "合计约111亿美元等值；预计9月29日发行",
        "pricing": "美元债3.5/5.5/7.5年票息8.625%/9.250%/9.750%；欧元债4/6年为7.125%/8.000%",
        "status": "条款已公布；待认购及二级市场验证",
        "source": "https://group.softbank/en/news/press/20260924",
    }
]


def _color_class(state: str) -> str:
    return {"SAFE": "green", "WATCH": "yellow", "WARNING": "orange", "CRITICAL": "red"}.get(state, "gray")


def _latest_date(series: pd.Series) -> str | None:
    if series is None or series.empty:
        return None
    stamp = min(pd.Timestamp(series.dropna().index[-1]).normalize(), pd.Timestamp.now().normalize())
    return stamp.strftime("%Y-%m-%d")


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
    "SAFE": "广泛信用代理尚未显示同步收紧；不代表AI债务安全。",
    "WATCH": "实际融资成本或信用条件已出现早期压力。",
    "WARNING": "信用利差、实际利率或金融条件正在显著压缩再融资空间。",
    "CRITICAL": "信用市场与融资条件已进入危机级收紧区间。",
}.get(state, "有效数据覆盖不足，暂不输出方向性判断。")
st.markdown(render_osci_card(
    "CFRI · 探索性信用压力指标",
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
            desc = "已有发行票息；待可比利差、认购及二级市场数据" if key == "ai_deal" else "数据缺失，不按SAFE处理"
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
    "SAFE": "广泛信用代理未提示同步压力",
    "WATCH": "融资成本抬升，但信用窗口仍然开放",
    "WARNING": "再融资压力上升，需要检查发行与续作条件",
    "CRITICAL": "信用窗口显著收缩，进入融资危机状态",
}.get(state, "数据覆盖不足")
alert_body = (
    f"当前CFRI为 {'N/A' if score is None else f'{score:.1f}/100'}。"
    "广泛信用条件和单一AI发行人的定价必须分开解释；历史代理曾漏掉重大事件，"
    "本分数尚不能证明AI债务风险低。单笔债券事件不会被手工写入总分。"
)
st.markdown(render_alert(state, f"结论：{alert_title}", alert_body), unsafe_allow_html=True)

st.markdown(spacer("sm"), unsafe_allow_html=True)
st.markdown(panel("📈 信用与融资条件历史", '<div class="history-help">HY OAS用于当前市场监控（月末快照）；BAA−10Y用于长历史参照。两者口径不同，不拼接成一条序列。</div>'), unsafe_allow_html=True)
st.plotly_chart(_stress_chart(series), use_container_width=True, config={"displayModeBar": False})

indicator_notes = [
    (
        "BAA−10Y 长期代理", "穆迪 Baa 级公司债收益率 − 美国 10 年期国债收益率",
        "衡量较低投资级企业债相对国债的额外融资成本。利差扩大表示广泛信用风险溢价上升；收窄表示压力缓和。",
        "观察是否持续扩大及其三个月变化；它不是 AI 债券利差，也不能与 HY OAS 拼成同一序列。",
        "历史代理", "baa10y", "bp", 100,
    ),
    (
        "HY OAS", "ICE BofA 美国高收益债指数期权调整利差（High Yield Option-Adjusted Spread）",
        "衡量高收益债相对无风险曲线的信用风险溢价。数值上升表示高风险借款人融资更贵；下降表示融资条件改善。",
        "结合当前水平、三个月变动和持续时间观察；它反映广泛高收益市场，不是某笔 AI 债的实际发行利差。",
        "当前市场监控（月末快照）", "hy_oas", "bp", 100,
    ),
    (
        "10Y TIPS", "美国 10 年期通胀保值国债实际收益率（10-Year TIPS Real Yield）",
        "衡量扣除市场通胀预期后的长期实际利率。上升通常提高长期项目的实际融资门槛并压低未来现金流现值；下降则缓和。",
        "同时看水平和三个月变化；高实际利率提示项目 NPV 压力，但单独不能判定 AI 项目无法偿债。",
        "当前融资成本监控", "real_yield", "%", 1,
    ),
    (
        "NFCI", "芝加哥联储全国金融状况指数（National Financial Conditions Index）",
        "综合衡量美国金融系统的风险、信用和杠杆条件。高于零表示比历史平均更紧；低于零表示更宽松，向上移动代表条件收紧。",
        "结合是否越过零及连续变化观察；它是系统性金融条件的压力确认，不对应单个发行人的再融资报价。",
        "系统性压力确认", "nfci", "指数", 1,
    ),
]
glossary_rows = []
for short_name, full_name, meaning, observation, role, key, unit, multiplier in indicator_notes:
    values = series[key].dropna()
    current = "N/A" if values.empty else f"{float(values.iloc[-1]) * multiplier:+.2f}{unit}（{_latest_date(values)}）"
    glossary_rows.append(
        '<div class="indicator-glossary-item">'
        f'<div class="indicator-glossary-heading"><b>{escape(short_name)}</b><span>{escape(role)}</span></div>'
        f'<div><strong>完整名称：</strong>{escape(full_name)}</div>'
        f'<div><strong>衡量与方向：</strong>{escape(meaning)}</div>'
        f'<div><strong>当前值：</strong>{escape(current)}</div>'
        f'<div><strong>观察方法：</strong>{escape(observation)}</div></div>'
    )
st.markdown(panel("📖 图中指标说明与观察方法", '<div class="indicator-glossary">' + ''.join(glossary_rows) + '</div>'), unsafe_allow_html=True)

deal_rows = "".join(
    f'<tr><td>{escape(item["date"])}</td><td><a href="{escape(item["source"])}" target="_blank">{escape(item["issuer"])}</a></td>'
    f'<td>{escape(item["purpose"])}</td><td>{escape(item["size"])}</td><td>{escape(item["pricing"])}</td><td>{escape(item["status"])}</td></tr>'
    for item in AI_DEALS
)
st.markdown(
    '<div class="panel"><div class="panel-title">🏦 AI融资交易观察</div><div class="table-scroll"><table class="gpu-table"><thead><tr><th>日期</th><th>发行人</th><th>用途</th><th>规模</th><th>发行条款</th><th>状态</th></tr></thead>'
    f'<tbody>{deal_rows}</tbody></table></div><div class="metric-sub">'
    '同一发行人4月美元债3.5年及5.5年票息分别为7.625%和8.250%，本次同期限均上移100bp；'
    '票息变化不等于信用利差变化，可能含基准利率、发行时点和融资需求影响。'
    '<a href="https://group.softbank/en/news/press/20260416" target="_blank">4月发行文件</a>。'
    '目前缺少可比国债利差、认购倍数和二级市场表现，故交易温度仍不计分。</div></div>',
    unsafe_allow_html=True,
)

history_rows = build_credit_history_rows(series, CREDIT_EVENTS)
body = []
for row in history_rows:
    color = STATE_COLORS.get(row["state"], "#94a3b8")
    score_text = "N/A" if row["score"] is None else f"{row['score']:.1f}/100"
    earlier_text = "N/A" if row["earlier_score"] is None else f"{row['earlier_score']:.1f}/100"
    earlier_color = STATE_COLORS.get(row["earlier_state"], "#94a3b8")
    interpretation = "未捕捉" if row["state"] == "SAFE" else "代理提示" if row["state"] != "N/A" else "数据不足"
    body.append(
        f'<tr><td>{row["month"]}</td><td><b>{escape(row["event"])}</b><br><small>{escape(row["description"])}</small></td>'
        f'<td>{row["credit"]}</td><td>{row["real"]}</td><td>{row["nfci"]}</td>'
        f'<td style="color:{earlier_color};font-weight:800">{row["earlier_state"]}<br>{earlier_text}</td>'
        f'<td style="color:{color};font-weight:800">{row["state"]}<br>{score_text}<br><small>{interpretation}</small></td>'
        f'<td>{row["coverage"]}%</td></tr>'
    )
available_cases = [row for row in history_rows if row["score"] is not None]
missed_cases = sum(row["state"] == "SAFE" for row in available_cases)
st.markdown(
    '<div class="panel"><div class="panel-title">📋 历史信用事件复盘</div>'
    '<div class="history-help">分别观察事件前6个月和前3个月的月末值，按当前数据版本重建。'
    'FRED的HY OAS从2026年4月起仅提供近三年，旧事件使用BAA−10Y代理；两者口径不同。'
    'NFCI历史值可能修订，这不是当时真实可见的评分，也不是经过验证的命中率。'
    f'本表{len(available_cases)}个可评分事件中，{missed_cases}个在事件前三个月仍为SAFE（未捕捉）。</div>'
    '<div class="table-scroll"><table class="gpu-table"><thead><tr><th>事件时间</th><th>信用事件</th><th>信用利差（前3个月）</th><th>实际利率（前3个月）</th><th>NFCI（前3个月）</th><th>前6个月代理</th><th>前3个月代理</th><th>覆盖率</th></tr></thead>'
    f'<tbody>{"".join(body)}</tbody></table></div></div>', unsafe_allow_html=True,
)

logic_tab, evidence_tab, source_tab = st.tabs(["检测逻辑", "指标与历史证据", "数据覆盖与来源"])
with logic_tab:
    st.markdown(logic_panel([
    {"text": "<b>信用利差（35%）</b>：实时优先采用HY OAS；长历史仅用BAA−10Y代理并明确标注，不混合口径。"},
    {"text": "<b>实际利率（30%）</b>：10Y TIPS水平占70%，三个月变化占30%，用于衡量项目NPV和真实资金成本。"},
    {"text": "<b>NFCI（25%）</b>：水平占60%，13周变化占40%；正值表示金融条件较长期平均更紧。"},
    {"text": "<b>AI融资交易温度（10%）</b>：只有可比较的最终定价与市场表现齐备时才计分。"},
    {"text": "<b>覆盖政策</b>：有效权重不足75%时输出N/A；缺失指标绝不按SAFE或零分处理。"},
    ], title="⚙️ CFRI评分逻辑"), unsafe_allow_html=True)

with evidence_tab:
    st.markdown(model_evidence_panel(
        sample="历史表为事后选择的信用事件；独立事件数、正常时期对照样本尚未核实。",
        validation=f"前3个月代理回放中{missed_cases}/{len(available_cases)}个可评分事件未捕捉；无可可靠展示的独立样本外命中率与置信区间。",
        boundary="HY OAS在FRED仅保留近三年；更早事件改用不同口径的BAA−10Y代理。广泛指标不能代表单笔AI债券；外生冲击不在可预测范围内。",
        calibration="当前切点为探索性规则，尚未完成按历史发布版本的独立样本外校准。",
    ), unsafe_allow_html=True)

with source_tab:
    render_data_freshness([
        {"name": "高收益信用利差", "source": "FRED · BAMLH0A0HYM2", "updated_at": _latest_date(series["hy_oas"]), "mode": "live"},
        {"name": "长期信用代理", "source": "FRED · BAA10Y", "updated_at": _latest_date(series["baa10y"]), "mode": "live"},
        {"name": "实际利率", "source": "FRED · DFII10", "updated_at": _latest_date(series["real_yield"]), "mode": "live"},
        {"name": "金融条件", "source": "FRED · NFCI", "updated_at": _latest_date(series["nfci"]), "mode": "live"},
        {"name": "AI融资交易", "source": "SoftBank官方发行文件；待认购与二级市场数据", "updated_at": "2026-09-24", "mode": "static"},
    ])
render_footer(f"{source} · 发行文件与事件驱动信息")
