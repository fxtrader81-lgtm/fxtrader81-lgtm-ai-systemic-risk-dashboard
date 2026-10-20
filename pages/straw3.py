import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from components.ui import evidence_table, load_css, logic_panel, metric_card, render_data_freshness, render_footer, render_header
from core.alert_engine import render_alert, render_osci_card
from core.score_engine import register_score
from core.aof import load_aof, score_aof, history as aof_history
from components.aof_panel import render_current as render_aof_current, render_history as render_aof_history
from core.reit_pressure import load_reit, history as reit_history
from components.reit_panel import render_current as render_reit_current, render_history as render_reit_history
from core.liquid_signal import load_liquid, history as liquid_history
from components.liquid_panel import render_current as render_liquid_current, render_history as render_liquid_history
from core.power_infrastructure import load_power, history as power_history
from components.power_panel import render_current as render_power_current, render_history as render_power_history

load_css()

# =========================================================
# 全局基准参数
# =========================================================

aof_snapshot = load_aof()
LEGACY_RACK_LIMIT_KW = aof_snapshot["reference"]["baseline_kw"]
CURRENT_DEPLOY_GPU = aof_snapshot["reference"]["model"]
CURRENT_RACK_KW = aof_snapshot["reference"]["rack_kw"]
AOF = aof_snapshot["metrics"]["aof"]

# =========================================================
# 页面配置
# =========================================================

st.set_page_config(page_title="数据中心资产减值", layout="wide")

# =========================================================
# CSS
# =========================================================


# =========================================================
# 数据获取 — yfinance（方案B，自动处理 crumb/cookie）
# =========================================================

def _statement_row(frame, names):
    if frame is None or frame.empty:
        return None
    for name in names:
        if name in frame.index:
            return frame.loc[name].dropna().sort_index(ascending=False)
    return None


def fetch_yf_info(ticker: str) -> dict:
    """Build stable market/financial metrics without relying on Ticker.info."""
    try:
        t = yf.Ticker(ticker)
        history = t.history(period="1y", auto_adjust=True)
        if history is None or history.empty or "Close" not in history:
            return {}

        close = history["Close"].dropna()
        if close.empty:
            return {}

        result = {
            "currentPrice": float(close.iloc[-1]),
            "fiftyTwoWeekHigh": float(history["High"].max()),
            "fiftyTwoWeekLow": float(history["Low"].min()),
            "revenueGrowth": None,
            "grossMargins": None,
            "operatingMargins": None,
        }

        try:
            financials = t.financials
            revenue = _statement_row(financials, ["Total Revenue", "Operating Revenue"])
            gross_profit = _statement_row(financials, ["Gross Profit"])
            operating_income = _statement_row(financials, ["Operating Income"])
            if revenue is not None and len(revenue) >= 2 and float(revenue.iloc[1]) != 0:
                result["revenueGrowth"] = float(revenue.iloc[0] / revenue.iloc[1] - 1)
            if revenue is not None and len(revenue) and float(revenue.iloc[0]) != 0:
                if gross_profit is not None and len(gross_profit):
                    result["grossMargins"] = float(gross_profit.iloc[0] / revenue.iloc[0])
                if operating_income is not None and len(operating_income):
                    result["operatingMargins"] = float(operating_income.iloc[0] / revenue.iloc[0])
        except Exception:
            # Price-based metrics remain valid even if statements are unavailable.
            pass
        return result
    except Exception:
        return {}


def safe_get(d: dict, key: str, default=None):
    value = d.get(key, default)
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def fmt_pct(value):
    return f"{value:+.1f}%" if value is not None else "N/A"


def average_present(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


# =========================================================
# 三大指标数据获取函数（全部改用 yfinance）
# =========================================================

# =========================================================
# DCOI 评分计算
# =========================================================

def compute_dcoi(aof_score, reit_stress_score, liquid_signal_score, power_stress_score):
    dcoi = (0.25 * aof_score +
            0.35 * reit_stress_score +
            0.25 * liquid_signal_score +
            0.15 * power_stress_score)
    return round(dcoi, 1)


def get_state(dcoi):
    if dcoi < 25:
        return "SAFE",    "green",  "22c55e", "Compatible Infrastructure",       "基础设施与GPU路线图兼容，资产估值稳定，减值风险低。"
    elif dcoi < 45:
        return "WATCH",   "yellow", "fbbf24", "Upgrade Stress Emerging",         "功率密度跃迁压力出现，液冷需求加速，风冷资产开始承压。"
    elif dcoi < 65:
        return "WARNING", "orange", "f97316", "Asset Repricing Underway",        "风冷资产开始系统性折价，REIT估值承压，改造成本攀升。"
    else:
        return "CRITICAL","red",    "ef4444", "Technical Obsolescence Confirmed","大量AI基建资产技术性贬值信号明确，市场重新定价正在发生。"


# =========================================================
# 分项评分函数（与 v1 完全一致）
# =========================================================

# =========================================================
# 顶部标题
# =========================================================

render_header("🏗️ 数据中心资产减值", "核心监测维度：GPU迭代速度是否已超出数据中心基础设施的金融折旧周期", symbol="DCOI · 数据中心淘汰指数")

# =========================================================
# 数据加载
# =========================================================

with st.spinner("正在通过 yfinance 拉取 REIT · 液冷厂商 · 电力数据..."):
    reit_snapshot = load_reit()
    liquid_snapshot = load_liquid()
    power_snapshot = load_power()

# =========================================================
# 各分项评分
# =========================================================

aof_s,   aof_color,   aof_arrow,   aof_status   = score_aof(AOF)
reit_metrics = reit_snapshot["metrics"]
if reit_metrics:
    reit_s, reit_color, reit_arrow, reit_status = (reit_metrics["score"], reit_metrics["color"],
                                                 reit_metrics["arrow"], reit_metrics["state"])
else:
    reit_s, reit_color, reit_arrow, reit_status = None, "gray", "—", "N/A"
liquid_metrics = liquid_snapshot["metrics"]
if liquid_metrics:
    lc_s, lc_color, lc_arrow, lc_status = (liquid_metrics["score"], liquid_metrics["color"],
                                          liquid_metrics["arrow"], liquid_metrics["state"])
else:
    lc_s, lc_color, lc_arrow, lc_status = None, "gray", "—", "N/A"
power_metrics = power_snapshot["metrics"]
if power_metrics:
    power_s, power_color, power_arrow, power_status = (power_metrics["score"], power_metrics["color"],
                                                       power_metrics["arrow"], power_metrics["state"])
else:
    power_s, power_color, power_arrow, power_status = None, "gray", "—", "N/A"

if reit_metrics and liquid_metrics and power_metrics:
    dcoi = compute_dcoi(aof_s, reit_s, lc_s, power_s)
    register_score("straw3", dcoi)
    state, state_color, state_hex, state_eng, state_cn = get_state(dcoi)
else:
    dcoi = None
    st.session_state.get("straw_scores", {}).pop("straw3", None)
    state, state_color, state_hex = "N/A", "gray", "94a3b8"
    missing_components = []
    if not reit_metrics: missing_components.append("REIT")
    if not liquid_metrics: missing_components.append("液冷相关企业")
    if not power_metrics: missing_components.append("电力相关企业")
    state_eng = " / ".join(missing_components) + " evidence incomplete"
    state_cn = "、".join(missing_components) + "必要数据不完整，完整DCOI暂不可用，不补预设分"

bar_color_map = {"green": "#22c55e", "yellow": "#fbbf24", "orange": "#f97316", "red": "#ef4444"}
bar_color = bar_color_map.get(state_color, "#94a3b8")

# =========================================================
# DCOI 总分大卡片
# =========================================================

st.markdown(render_osci_card(
    "DATA CENTER OBSOLESCENCE INDEX", dcoi, state, f"综合评分：原规则{state}档；参考情景与市场代理组合，非已确认减值" if dcoi is not None else state_cn,
    bar_color=bar_color, state_detail=state_eng,
    components_html="GPU功率压力 ×0.25 · REIT估值 ×0.35<br>液冷信号 ×0.25 · 电力压力 ×0.15",
    score_display=f"{dcoi:.0f}" if dcoi is not None else "N/A",
), unsafe_allow_html=True)

# =========================================================
# 四张指标卡片
# =========================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(metric_card(
        'AOF 机柜适配压力 <span class="source-tag-warn static-data-badge">参考情景</span>',
        f"{AOF}x", aof_color, aof_arrow,
        f"{CURRENT_DEPLOY_GPU} {CURRENT_RACK_KW}kW ÷ 旧机房参考情景 {LEGACY_RACK_LIMIT_KW}kW<br>"
        f"分项{aof_s}分 · {aof_status} · 贡献{aof_s*.25:g}分；不代表全市场资产已减值",
    ), unsafe_allow_html=True)

with c2:
    if reit_metrics:
        eqix, dlr = reit_snapshot["rows"]
        desc2 = (f"EQIX距一年高点 -{eqix['metrics']['from_high_pct']:.1f}% · "
                 f"DLR -{dlr['metrics']['from_high_pct']:.1f}%<br>"
                 f"年度营收同比 EQIX {fmt_pct(eqix['metrics']['rev_growth'])} · "
                 f"DLR {fmt_pct(dlr['metrics']['rev_growth'])}<br>"
                 f"分项{reit_s}分 · {reit_status} · 价格/财年与完整算式见下方说明")
        display2 = f"-{reit_metrics['mean_drawdown']:.1f}%"
    else:
        desc2 = f"必要数据覆盖{reit_snapshot['coverage']}/2家公司，暂不评分<br>不按一家求平均、不补0或50分；历史有效值保留供查阅"
        display2 = "N/A"
    st.markdown(metric_card('REIT 估值压力 <span class="source-tag">YF · 自动取数</span>', display2,
                            reit_color, reit_arrow, desc2), unsafe_allow_html=True)

with c3:
    if liquid_metrics:
        vrt, smci = liquid_snapshot["rows"]
        desc3 = (f"年度总营收同比 VRT {fmt_pct(vrt['metrics']['rev_growth'])} · "
                 f"SMCI {fmt_pct(smci['metrics']['rev_growth'])}<br>"
                 f"股价位置 VRT {vrt['metrics']['price_pos_pct']:.0f}% · "
                 f"SMCI {smci['metrics']['price_pos_pct']:.0f}%（一年区间）<br>"
                 f"分项{lc_s}分 · {lc_status} · 公司总营收代理，非液冷业务收入；财年/算式见下方")
        display3 = fmt_pct(liquid_metrics["mean_growth"])
    else:
        desc3 = f"必要数据覆盖{liquid_snapshot['coverage']}/2家公司，暂不评分<br>不按一家平均、不补0或50分；历史资料保留供查阅"
        display3 = "N/A"
    st.markdown(metric_card('液冷加速信号（相关企业代理） <span class="source-tag">YF · 自动取数</span>', display3,
                            lc_color, lc_arrow, desc3), unsafe_allow_html=True)

with c4:
    if power_metrics:
        nee, so = power_snapshot["rows"]
        desc4 = (f"年度公司总营收同比 NEE {fmt_pct(nee['metrics']['rev_growth'])} · "
                 f"SO {fmt_pct(so['metrics']['rev_growth'])}<br>"
                 f"股价位置 NEE {nee['metrics']['price_pos_pct']:.0f}% · "
                 f"SO {so['metrics']['price_pos_pct']:.0f}%（一年区间）<br>"
                 f"分项{power_s}分 · {power_status} · 相关企业代理，非实际用电量或电网容量；财年/算式见下方")
        display4 = fmt_pct(power_metrics["mean_growth"])
    else:
        desc4 = f"必要数据覆盖{power_snapshot['coverage']}/2家公司，暂不评分<br>不按一家平均，不补0/50或整项30分；历史记录保留供查阅"
        display4 = "N/A"
    st.markdown(metric_card('电力基础设施（相关企业代理） <span class="source-tag">YF · 自动取数</span>', display4,
                            power_color, power_arrow, desc4), unsafe_allow_html=True)

# =========================================================
# Alert 结论框
# =========================================================

alert_map = {
    "SAFE": {
        "box_class": "alert-box-green", "icon": "✅", "title_color": "#22c55e",
        "title": "结论：当前组合评分较低，仍需核验机柜适配和资产减值情况",
        "body": f'当前 DCOI = <span class="green"><b>{dcoi}</b></span>，处于原规则的安全区间。AOF只描述选定机柜与25kW参考情景的适配压力，不能据此证明所有存量机房兼容或没有资产减值。'
    },
    "WATCH": {
        "box_class": "alert-box", "icon": "👁", "title_color": "#fbbf24",
        "title": "结论：组合评分进入观察区，关注机柜升级和资产端信号",
        "body": f'当前 DCOI = <span class="yellow"><b>{dcoi}</b></span>，进入原规则的观察区间。AOF反映参考方案的适配压力，不证明存量机房正在报废。需核验运营商实际改造资本开支、订单和财报减值披露。'
    },
    "WARNING": {
        "box_class": "alert-box", "icon": "⚠️", "title_color": "#f97316",
        "title": "结论：组合评分偏高，需核验机柜改造压力与资产重新定价",
        "body": f'当前 DCOI = <span class="orange"><b>{dcoi}</b></span>，进入原规则的高危区间。AOF参考机柜的切换本身会抬高评分，不能将分差解释为市场突然恶化或已确认资产减值；需结合运营商改造支出与实际减值披露核验，金融传导另需跨因子确认。'
    },
    "CRITICAL": {
        "box_class": "alert-box-red", "icon": "🔴", "title_color": "#ef4444",
        "title": "结论：组合评分达到高风险档，不等于已确认会计减值或金融传导",
        "body": f'当前 DCOI = <span class="red"><b>{dcoi}</b></span>，进入原规则的危机区间。AOF只是特定高密度机柜对25kW旧机房容量情景的压力，不能证明市场普遍报废、改造成本接近重建或已发生资产减值。应核验运营商实际改造支出、财报减值与信贷数据；本因子单独不构成系统性金融危机。'
    }
}

alert_map["N/A"] = {
    "title": state_cn if dcoi is None else "必要数据不完整，完整DCOI暂不可用",
    "body": "缺失公司、年度营收或价格区间不按安全/中性分处理；其余分项继续展示，旧有效记录可在相应历史资料中查阅，不冒充本次结果。",
}
alert = alert_map.get(state, alert_map["WATCH"])
st.markdown(render_alert(state, alert["title"], alert["body"]), unsafe_allow_html=True)

# =========================================================
# GPU 功率密度图直接展示；方法和精确数据留在底部标签页。
# =========================================================

def _render_detection_logic():
    st.markdown(logic_panel([
        {"text": "<b>AOF 机柜适配压力（×0.25）</b>：已复核的GB200 NVL72整柜功率参考120kW ÷ 项目旧机房容量情景25kW＝4.8倍。不是主流部署占比或减值比例；参数切换与旧版2.4倍存在口径断点。沿用原分数映射，未重校准，本期100分、贡献25分", "thresholds": [
            ("#22c55e", "AOF < 1.5x", "SAFE", "green"),
            ("#fbbf24", "1.5 ≤ AOF < 2.5x", "WATCH", "yellow"),
            ("#f97316", "2.5 ≤ AOF < 3.5x", "WARNING", "orange"),
            ("#ef4444", "AOF ≥ 3.5x", "CRITICAL", "red"),
        ]},
        {"text": "<b>REIT 估值压力（×0.35）</b>：固定EQIX/DLR。回撤＝（一年调整后日内最高价－最新调整后日收盘价）÷最高价；跌幅&lt;5/15/25/40%及以上对应价格分10/35/60/80/95。最新两个年度营收同比&gt;12/&gt;6/&gt;0%及以下对应增长分10/30/55/80。每家公司＝价格分×65%＋增长分×35%；两家公司平均后按原规则取整，状态按取整前均分判断。两家必要数据必须完整，不填0或50分。总览共用本入口；以下是REIT分项状态，不是股价跌幅或整页状态。", "thresholds": [
            ("#22c55e", "REIT均分 < 25", "SAFE", "green"),
            ("#fbbf24", "25 ≤ REIT均分 < 50", "WATCH", "yellow"),
            ("#f97316", "50 ≤ REIT均分 < 70", "WARNING", "orange"),
            ("#ef4444", "REIT均分 ≥ 70", "CRITICAL", "red"),
        ]},
        {"text": "<b>液冷加速信号（相关企业代理，×0.25）</b>：固定VRT/SMCI。公司年度总营收同比&lt;10/30/60/100%及以上对应增长分10/30/55/75/90；股价位置＝（最新调整后日收盘－一年调整后日内最低）÷（最高－最低），位置&gt;80/&gt;60/&gt;40%及以下对应价格分80/60/40/20。每家公司＝增长分×65%＋价格分×35%；两家公司平均后取整，状态按取整前均分判断。两家必要资料完整才评分，不补0/50。不是液冷分部收入、增速加速度或风冷淘汰证明；总览共用本入口。", "thresholds": [
            ("#22c55e", "液冷分项均分 < 25", "SAFE", "green"),
            ("#fbbf24", "25 ≤ 液冷分项均分 < 50", "WATCH", "yellow"),
            ("#f97316", "50 ≤ 液冷分项均分 < 70", "WARNING", "orange"),
            ("#ef4444", "液冷分项均分 ≥ 70", "CRITICAL", "red"),
        ]},
        {"text": "<b>电力基础设施（相关企业代理，×0.15）</b>：固定NEE/SO。年度公司总营收同比&lt;3/8/15%及以上对应增长分15/35/60/80；股价位置＝（最新调整后日收盘－一年调整后日内最低）÷（最高－最低），位置&gt;75/&gt;50/&gt;25%及以下对应价格分70/50/30/15。每家公司＝增长分×60%＋价格分×40%，两家公司平均后取整，状态按取整前均分判断。两家必要资料完整才评分，不填0/50/整项30分。只是公司经营与股价代理，不是数据中心用电、电网容量或缺电程度；总览共用本入口。", "thresholds": [
            ("#22c55e", "电力分项均分 < 25", "SAFE", "green"),
            ("#fbbf24", "25 ≤ 电力分项均分 < 45", "WATCH", "yellow"),
            ("#f97316", "45 ≤ 电力分项均分 < 65", "WARNING", "orange"),
            ("#ef4444", "电力分项均分 ≥ 65", "CRITICAL", "red"),
        ]},
    ]), unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="panel-title">⚡ GPU 功率密度代际参考与本期 AOF 方案（单机柜 kW）</div>', unsafe_allow_html=True)
    legacy_chart = next(r["reference"]["chart_reference"] for r in aof_history()
                        if r["reference"]["id"] == "legacy-h100-60kw-25kw")
    generations = legacy_chart["generations"]
    mids = [(g["rack_kw_min"]+g["rack_kw_max"])/2 for g in generations]
    labels = [g["gen"].replace(" (", "<br>(") for g in generations]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="原六代示意参数（未核验，不参与本期评分）",
        x=labels, y=mids, marker_color=["#334155", "#334155", "#f97316", "#f97316", "#ef4444", "#7c3aed"],
        text=[f"{v:g}kW" for v in mids], textposition="outside",
        textfont=dict(color="#cbd5e1", size=14),
        error_y=dict(type="data", symmetric=False,
                     array=[g["rack_kw_max"]-v for g,v in zip(generations,mids)],
                     arrayminus=[v-g["rack_kw_min"] for g,v in zip(generations,mids)],
                     color="#64748b", thickness=2),
        customdata=[[g["rack_kw_min"],g["rack_kw_max"]] for g in generations],
        hovertemplate="%{x}<br>旧版示意范围：%{customdata[0]}–%{customdata[1]}kW<br>柱高为范围中点，未核验配置、不参与本期评分<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="GB200 NVL72（本期已复核参考方案）",
        x=["GB200 NVL72<br>本期AOF参考"], y=[CURRENT_RACK_KW],
        marker_color="#60a5fa", text=[f"{CURRENT_RACK_KW:g}kW"],
        textposition="outside", textfont=dict(color="#e2e8f0", size=16),
        hovertemplate="本期GB200 NVL72整柜参考<br>%{y}kW ÷ 25kW情景＝4.8倍<br>不是现场实时负载<extra></extra>",
    ))
    fig.add_hline(y=LEGACY_RACK_LIMIT_KW, line_color="#22c55e", line_dash="dash",
                  annotation_text=f"{LEGACY_RACK_LIMIT_KW:g}kW容量参考情景（AOF分母）",
                  annotation_font_color="#22c55e", annotation_position="top left")
    fig.add_hline(y=legacy_chart["upgraded_rack_limit_kw"], line_color="#fbbf24", line_dash="dot",
                  annotation_text="旧版50kW示意线（未核验，不参与评分）",
                  annotation_font_color="#fbbf24", annotation_position="top left")
    fig.update_layout(
        height=370, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=14), margin=dict(l=10, r=20, t=25, b=10),
        xaxis=dict(showgrid=False, zeroline=False, categoryorder="array",
                   categoryarray=labels+["GB200 NVL72<br>本期AOF参考"]),
        yaxis=dict(title="机柜功率（kW）", range=[0,max(max(g["rack_kw_max"] for g in generations),CURRENT_RACK_KW)*1.15],
                   gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        legend=dict(orientation="h", y=-.25, x=0, font=dict(color="#cbd5e1",size=13)),
        barmode="group",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="text-dim">原六代范围和中点完整保留，属于旧版未核验示意，并非实际部署或淘汰证据；蓝柱是本期已复核的整柜参考。本期AOF只按120÷25＝4.8计算，不将七根柱子平均。历史资料保留原标签及原始参数。</div>', unsafe_allow_html=True)

# =========================================================
# 页脚
# =========================================================

logic_tab, evidence_tab, source_tab = st.tabs(["检测逻辑", "指标与历史证据", "数据覆盖与来源"])
with logic_tab:
    _render_detection_logic()
with evidence_tab:
    with st.container(key="aof_evidence"):
        aof_tab, reit_tab, liquid_tab, power_tab = st.tabs(["AOF", "REIT", "液冷", "电力"])
        with aof_tab:
            with st.expander("本期数据与计算说明", expanded=False):
                render_aof_current(aof_snapshot)
            with st.expander("历史记录与原始资料", expanded=False):
                render_aof_history(aof_snapshot, aof_history())
        with reit_tab:
            with st.expander("本期数据与计算说明", expanded=False):
                render_reit_current(reit_snapshot)
            with st.expander("历史记录与原始资料", expanded=False):
                render_reit_history(reit_snapshot, reit_history())
        with liquid_tab:
            with st.expander("本期数据与计算说明", expanded=False):
                render_liquid_current(liquid_snapshot)
            with st.expander("历史记录与原始资料", expanded=False):
                render_liquid_history(liquid_snapshot, liquid_history())
        with power_tab:
            with st.expander("本期数据与计算说明", expanded=False):
                render_power_current(power_snapshot)
            with st.expander("历史记录与原始资料", expanded=False):
                render_power_history(power_snapshot, power_history())
with source_tab:
    render_data_freshness([
        {"name": "电力相关企业价格与年度总营收", "source": f"Yahoo Finance · 固定NEE / SO · 覆盖{power_snapshot['coverage']}/2", "updated_at": "；".join(f"{r['ticker']}价格{r.get('price_date','未取得')}/财年{r['annual_revenue'][0]['period_end'] if r['annual_revenue'] else '未取得'}" for r in power_snapshot["rows"]), "mode": "live"},
        {"name": "液冷相关企业价格与年度总营收", "source": f"Yahoo Finance · 固定VRT / SMCI · 覆盖{liquid_snapshot['coverage']}/2", "updated_at": "；".join(f"{r['ticker']}价格{r.get('price_date','未取得')}/财年{r['annual_revenue'][0]['period_end'] if r['annual_revenue'] else '未取得'}" for r in liquid_snapshot["rows"]), "mode": "live"},
        {"name": "REIT价格与年度营收", "source": f"Yahoo Finance · 固定EQIX / DLR · 覆盖{reit_snapshot['coverage']}/2", "updated_at": "；".join(f"{r['ticker']}价格{r.get('price_date','未取得')}/财年{r['annual_revenue'][0]['period_end'] if r['annual_revenue'] else '未取得'}" for r in reit_snapshot["rows"]), "mode": "live"},
        {"name": "AOF参考情景（非实时负载）", "source": "NVIDIA MGX官方资料（2025-05-16） · 项目25kW情景", "updated_at": aof_snapshot["reference"]["reviewed_date"] + " 参数复核，非实测日期", "mode": "static"},
    ])
render_footer("Yahoo Finance · 每小时缓存 · AOF 经确认的固定参考情景（非自动追新型号）")
