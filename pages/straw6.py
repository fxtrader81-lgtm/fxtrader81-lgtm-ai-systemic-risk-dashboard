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
from components.credit_transmission_views import render_credit_market_evidence
from components.factor_quarterly_panel import render_current_quarter, render_quarterly_history
from config.thresholds import STATE_COLORS
from core.alert_engine import render_alert, render_osci_card
from core.ai_financing_news import load_financing_news, load_softbank_financing_releases
from core.credit_history import build_credit_history_rows
from core.credit_quarterly import (load_archive_metadata, load_history as load_quarterly_history,
                                   make_current_snapshot)
from core.credit_risk import COMPONENTS, compute_credit_metrics
from core.macro_data import load_credit_stress_snapshot, normalize_credit_stress_series
from core.score_engine import register_score


st.set_page_config(page_title="AI信贷与再融资压力", layout="wide", initial_sidebar_state="expanded")
load_css()


CREDIT_EVENTS = [
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
        "date": "2026-10-01",
        "issuer": "Sharon AI",
        "purpose": "以GPU及相关现金流作担保，为客户合同对应的AI算力部署融资；可观察资产抵押和融资成本。",
        "size": "3.56亿美元承诺额度；不等于已提款金额",
        "pricing": "固定利率9.95%，不含费用；高级担保SPV债务安排",
        "status": "公司原始公告称已签署并完成交易；提款及后续表现待核验；不计分",
        "source": "https://sharonai.com/press-releases/sharon-ai-enters-into-gpu-backed-debt-facility-expanding-funding-flexibility-for-ai-factory-deployments/",
    },
    {
        "date": "2026-09-18",
        "issuer": "CoreWeave",
        "purpose": "净收益预计约36.445亿美元，其中约4.988亿美元拟用于封顶看涨交易；余款用于一般公司用途。AI云运营商融资，与本页再融资条件相关。",
        "size": "37亿美元本金；承销商另有最多5亿美元增购选择权",
        "pricing": "2.875%可转高级债，2033年到期；初始转换价约97.85美元/股",
        "status": "官方公告已定价；原预计9月22日结算，实际结算及二级表现待核验；不计分",
        "source": "https://investors.coreweave.com/news/news-details/2026/CoreWeave-Prices-Upsized-3-7-Billion-Convertible-Senior-Notes-Offering/default.aspx",
    },
    {
        "date": "2026-09-24",
        "issuer": "SoftBank Group",
        "purpose": "美元债100亿美元及欧元债10亿欧元；主要用于OpenAI后续100亿美元投资",
        "size": "合计约111亿美元等值；官方文件载明9月29日为预计发行日",
        "pricing": "美元债3.5/5.5/7.5年票息8.625%/9.250%/9.750%；欧元债4/6年为7.125%/8.000%",
        "status": "截至9月24日条款已公布；后续认购及二级市场数据待验证",
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


def _latest_quarter(series: pd.Series) -> str | None:
    if series is None or series.empty:
        return None
    return str(pd.Timestamp(series.dropna().index[-1]).to_period("Q"))


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

with st.spinner("正在读取信用利差、实际利率、金融条件与银行贷款标准…"):
    series, source = load_credit_stress_snapshot()
series = normalize_credit_stress_series(series)
metrics = compute_credit_metrics(
    series["hy_oas"], series["real_yield"], series["nfci"],
    baa_spread=series["baa10y"],
    lending_standards=series["sloos"],
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
    state_detail=f"有效权重覆盖率 {composite['coverage']}% · 银行贷款标准按季度更新",
    components_html="信用利差 ×0.35 · 10Y实际利率 ×0.30<br>NFCI金融条件 ×0.25 · 银行融资可得性 ×0.10",
    score_display="N/A" if score is None else f"{score:.1f}",
), unsafe_allow_html=True)

columns = st.columns(4)
for column, key in zip(columns, COMPONENTS):
    definition = COMPONENTS[key]
    item = metrics.get(key)
    with column:
        if item is None:
            st.markdown(metric_card(f"{definition['label']} ×{definition['weight']:.2f}", "N/A", "gray",
                                    desc="数据缺失，不按SAFE处理"), unsafe_allow_html=True)
            continue
        if key == "credit_spread":
            value = f"{item['value']:.0f}bp"
            change = "" if item["change"] is None else f"3M {item['change']:+.0f}bp"
            desc = f"当前 {item['grade']} · {item.get('proxy', '')}<br>{change}"
        elif key == "real_rate":
            value = f"{item['value']:.2f}%"
            change = "" if item["change"] is None else f"3M {item['change']:+.0f}bp"
            desc = f"当前 {item['grade']}<br>{change}"
        elif key == "lending_standards":
            value = f"{item['value']:+.1f}%"
            change = "" if item["change"] is None else f"较上季 {item['change']:+.1f}个百分点"
            period = _latest_quarter(series["sloos"]) or "季度不可得"
            desc = f"当前 {item['grade']} · {period}<br>{change}"
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
    "本分数描述当前广泛信用市场的压力，不是事件发生前三至六个月的预测信号。"
    "广泛信用条件和单一AI发行人的定价必须分开解释；SAFE不能证明AI债务风险低。"
    "单笔债券事件不会被手工写入总分。"
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
st.markdown(
    '<details class="panel indicator-disclosure">'
    '<summary><span>📖 图中指标说明与观察方法</span>'
    '<span class="indicator-disclosure-action"><span class="disclosure-open-label">展开查看</span>'
    '<span class="disclosure-close-label">收起说明</span><span aria-hidden="true">⌄</span></span></summary>'
    '<div class="indicator-glossary">' + ''.join(glossary_rows) + '</div></details>',
    unsafe_allow_html=True,
)

render_credit_market_evidence()

try:
    news_leads, news_checked_at = load_financing_news()
except Exception:
    news_leads, news_checked_at = [], None

# Do not repeat a reviewed issuer announcement as an unverified RSS headline.
news_leads = [
    lead for lead in news_leads
    if not any(item["date"] == lead["date"] and item["issuer"].lower() in lead["headline"].lower()
               for item in AI_DEALS)
    and "tesla secures $30 billion credit facility to fund ai infrastructure" not in lead["headline"].lower()
][:5]


def _deal_rows(items: list[dict[str, str]]) -> str:
    return "".join(
    f'<tr><td>{escape(item["date"])}</td><td><a href="{escape(item["source"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(item["issuer"])}</a></td>'
    f'<td>{escape(item["purpose"])}</td><td>{escape(item["size"])}</td><td>{escape(item["pricing"])}</td><td>{escape(item["status"])}</td></tr>'
    for item in items
    )


deal_rows = _deal_rows(sorted(AI_DEALS, key=lambda item: item["date"], reverse=True))
st.markdown(
    '<div class="panel"><div class="panel-title">🏦 AI融资事件观察｜非评分证据</div>'
    '<div class="metric-sub">条款及交易状态依据发行人原始公告；已公布、已定价、已完成及已提款各有不同，均不自动计入CFRI评分。</div>'
    '<div class="table-scroll"><table class="gpu-table"><thead><tr><th>日期</th><th>发行人</th><th>用途／关联</th><th>规模</th><th>发行条款</th><th>核验状态</th></tr></thead>'
    f'<tbody>{deal_rows}</tbody></table></div><div class="metric-sub">'
    'SoftBank同一发行人4月美元债3.5年及5.5年票息分别为7.625%和8.250%，9月同期限均上移100bp；'
    '票息变化不等于信用利差变化，可能含基准利率、发行时点和融资需求影响。'
    '<a href="https://group.softbank/en/news/press/20260416" target="_blank">4月发行文件</a>。'
    '目前缺少可比国债利差、认购倍数和二级市场表现，因此只作风险解释，不进入评分。</div></div>',
    unsafe_allow_html=True,
)

news_rows = _deal_rows(news_leads)
if not news_rows:
    news_rows = '<tr><td colspan="6">本轮没有符合关键词与事件类型筛选的新闻线索；不代表全网没有新事件。</td></tr>'
st.markdown(
    '<div class="panel"><div class="panel-title">🔎 自动发现 · 待核验新闻线索</div>'
    '<div class="metric-sub">打开本页时检索近期公开新闻，缓存最多6小时；这是标题级初筛，不是全网无遗漏监控。'
    '新闻标题可能误述融资用途、金额或完成状态；没有原始公告／监管文件核验前，不会晋升到上方事件表，也不计分。'
    f'上次检索：{escape(news_checked_at) if news_checked_at else "本次失败，下次打开重试"}。</div>'
    '<div class="table-scroll"><table class="gpu-table"><thead><tr><th>报道日期</th><th>报道对象</th><th>新闻线索／关联</th><th>标题金额</th><th>条款</th><th>核验状态</th></tr></thead>'
    f'<tbody>{news_rows}</tbody></table></div></div>',
    unsafe_allow_html=True,
)

try:
    recent_releases, checked_at = load_softbank_financing_releases()
except Exception:
    recent_releases, checked_at = [], None
release_links = " · ".join(
    f'<a href="{escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
    f'{escape(item["date"][:4] + "-" + item["date"][4:6] + "-" + item["date"][6:])} '
    f'{escape(item["title"])}</a>'
    for item in recent_releases[:5]
)
scan_note = (
    f'上次检查：{escape(checked_at)}。' if checked_at else '本次官方索引检索失败；下次打开会重试。'
)
st.markdown(
    '<div class="panel"><div class="panel-title">🔎 官方披露线索（每周按访问刷新）</div>'
    '<div class="metric-sub">仅检索 SoftBank 官方新闻索引，展示可能相关的融资或投资公告；'
    '标题不是发行条款或成交验证，不自动改写上表，也不计入 CFRI。'
    f'{scan_note}</div>'
    f'<div class="metric-sub">{release_links or "本次未识别到匹配的官方公告。"}</div></div>',
    unsafe_allow_html=True,
)

history_rows = build_credit_history_rows(series, CREDIT_EVENTS)
body = []
for row in history_rows:
    color = STATE_COLORS.get(row["state"], "#94a3b8")
    score_text = "N/A" if row["score"] is None else f"{row['score']:.1f}/100"
    earlier_text = "N/A" if row["earlier_score"] is None else f"{row['earlier_score']:.1f}/100"
    earlier_color = STATE_COLORS.get(row["earlier_state"], "#94a3b8")
    interpretation = "未见广泛压力" if row["state"] == "SAFE" else "广泛压力抬升" if row["state"] != "N/A" else "数据不足"
    body.append(
        f'<tr><td>{row["month"]}</td><td><b>{escape(row["event"])}</b><br><small>{escape(row["description"])}</small></td>'
        f'<td>{row["credit"]}</td><td>{row["real"]}</td><td>{row["nfci"]}</td><td>{row["sloos"]}</td>'
        f'<td style="color:{earlier_color};font-weight:800">{row["earlier_state"]}<br>{earlier_text}</td>'
        f'<td style="color:{color};font-weight:800">{row["state"]}<br>{score_text}<br><small>{interpretation}</small></td>'
        f'<td>{row["coverage"]}%</td></tr>'
    )
available_cases = [row for row in history_rows if row["score"] is not None]
safe_cases = sum(row["state"] == "SAFE" for row in available_cases)
earlier_cases = [row for row in history_rows if row["earlier_score"] is not None]
earlier_safe_cases = sum(row["earlier_state"] == "SAFE" for row in earlier_cases)
history_summary = (
    f'前6个月{earlier_safe_cases}/{len(earlier_cases)}、前3个月{safe_cases}/{len(available_cases)}个可评分事件仍为SAFE。'
    if available_cases and earlier_cases else '当前历史数据覆盖不足，暂不能汇总可评分事件。'
)
st.markdown(
    '<div class="panel"><div class="panel-title">📋 历史信用事件复盘</div>'
    '<div class="history-help">分别观察事件前6个月和前3个月的月末值，按当前数据版本重建；这些是事前压力快照，不是事件预测。'
    'SLOOS为季度调查，表示美国大中型企业工商业贷款标准净收紧比例，并非AI专项信贷报价。'
    'FRED的HY OAS从2026年4月起仅提供近三年，旧事件使用BAA−10Y代理；两者口径不同。'
    '1998和2002年事件因10Y TIPS实际利率序列尚未开始、有效权重只有60%，从评分表移除。'
    'NFCI历史值可能修订，这不是当时真实可见的评分，也不是经过验证的命中率。'
    f'{history_summary}SAFE只表示该时点尚未出现足以触发本模型的广泛信用压力；'
    '突发事件、局部信用风险及尚未扩散的脆弱性可能不反映在这些指标里。</div>'
    '<div class="table-scroll"><table class="gpu-table"><thead><tr><th>事件时间</th><th>信用事件</th><th>信用利差（前3个月）</th><th>实际利率（前3个月）</th><th>NFCI（前3个月）</th><th>银行标准净收紧（前3个月）</th><th>前6个月代理</th><th>前3个月代理</th><th>覆盖率</th></tr></thead>'
    f'<tbody>{"".join(body)}</tbody></table></div></div>', unsafe_allow_html=True,
)

logic_tab, evidence_tab, source_tab = st.tabs(["检测逻辑", "指标与历史证据", "数据覆盖与来源"])
with logic_tab:
    st.markdown(logic_panel([
    {"text": "<b>信用利差（35%）</b>：实时优先采用HY OAS；长历史仅用BAA−10Y代理并明确标注，不混合口径。"},
    {"text": "<b>实际利率（30%）</b>：10Y TIPS水平占70%，三个月变化占30%，用于衡量项目NPV和真实资金成本。"},
    {"text": "<b>NFCI（25%）</b>：水平占60%，13周变化占40%；正值表示金融条件较长期平均更紧。"},
    {"text": "<b>银行融资可得性（10%）</b>：采用美联储SLOOS中大中型企业工商业贷款标准净收紧比例；≤5%为0分，>5–10%为33分，>10–20%为67分，>20%为100分。季度自动更新。"},
    {"text": "<b>AI融资事件</b>：保留发行、贷款与担保结构作为解释证据；因条款口径不统一、缺少系统可比市场数据，不再占用评分权重。"},
    {"text": "<b>覆盖政策</b>：有效权重不足75%时输出N/A；缺失指标绝不按SAFE或零分处理。"},
    ], title="⚙️ CFRI评分逻辑"), unsafe_allow_html=True)

with evidence_tab:
    current_quarter = make_current_snapshot(metrics, series)
    quarterly_history = load_quarterly_history()
    archive_metadata = load_archive_metadata()
    render_current_quarter(current_quarter, container_key="credit_quarterly_current")
    render_quarterly_history(
        quarterly_history, current_quarter, archive_metadata["legacy_method_evidence"],
        container_key="credit_quarterly_history", page_number="06",
        page_title="AI信贷与再融资压力", file_prefix="factor06-credit",
        method_summary=archive_metadata["method_notes"],
    )
    st.markdown(model_evidence_panel(
        sample="历史表为事后选择的信用事件；独立事件数、正常时期对照样本尚未核实。",
        validation=f"{history_summary}这些结果不支持把CFRI当作事件前三至六个月的预测器；无可可靠展示的独立样本外命中率与置信区间。",
        boundary="HY OAS在FRED仅保留近三年；更早事件改用不同口径的BAA−10Y代理。广泛指标不能代表单笔AI债券；外生冲击不在可预测范围内。",
        calibration="当前切点为探索性规则，尚未完成按历史发布版本的独立样本外校准。",
    ), unsafe_allow_html=True)

with source_tab:
    render_data_freshness([
        {"name": "高收益信用利差", "source": "FRED · BAMLH0A0HYM2", "updated_at": _latest_date(series["hy_oas"]), "mode": "live"},
        {"name": "长期信用代理", "source": "FRED · BAA10Y", "updated_at": _latest_date(series["baa10y"]), "mode": "live"},
        {"name": "实际利率", "source": "FRED · DFII10", "updated_at": _latest_date(series["real_yield"]), "mode": "live"},
        {"name": "金融条件", "source": "FRED · NFCI", "updated_at": _latest_date(series["nfci"]), "mode": "live"},
        {"name": "银行融资可得性", "source": "美联储SLOOS / FRED · DRTSCILM", "updated_at": _latest_date(series["sloos"]), "mode": "live"},
        {"name": "AI融资事件（非评分）", "source": "发行人官方公告；不自动改变CFRI", "updated_at": "2026-10-01", "mode": "static"},
        {"name": "SoftBank官方披露线索", "source": "SoftBank新闻索引；访问时最多每周检索一次", "updated_at": checked_at, "mode": "live"},
    ])
render_footer(f"{source} · 发行文件与事件驱动信息")
