import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from components.ui import load_css, render_footer, render_header
from core.alert_engine import render_alert, render_osci_card
from core.score_engine import register_score

load_css()

# =========================================================
# 全局基准参数
# =========================================================

LEGACY_RACK_LIMIT_KW   = 25
UPGRADED_RACK_LIMIT_KW = 50
CURRENT_DEPLOY_GPU     = "H100"
CURRENT_RACK_KW        = 60
AOF = round(CURRENT_RACK_KW / LEGACY_RACK_LIMIT_KW, 2)   # → 2.4x

GPU_GENERATIONS = [
    {"gen": "V100\n(2017)",  "year": 2017, "rack_kw_min": 10,  "rack_kw_max": 20,  "status": "legacy"},
    {"gen": "A100\n(2020)",  "year": 2020, "rack_kw_min": 20,  "rack_kw_max": 30,  "status": "legacy"},
    {"gen": "H100\n(2022)",  "year": 2022, "rack_kw_min": 40,  "rack_kw_max": 80,  "status": "active"},
    {"gen": "H200\n(2024)",  "year": 2024, "rack_kw_min": 60,  "rack_kw_max": 100, "status": "active"},
    {"gen": "B200\n(2025)",  "year": 2025, "rack_kw_min": 100, "rack_kw_max": 140, "status": "current"},
    {"gen": "Rubin\n(2026e)","year": 2026, "rack_kw_min": 180, "rack_kw_max": 220, "status": "next"},
]

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

@st.cache_data(ttl=3600)
def get_reit_data():
    """数据中心 REIT 财务压力：EQIX / DLR"""
    results = {}
    for ticker in ["EQIX", "DLR"]:
        info = fetch_yf_info(ticker)
        if not info:
            continue

        current_p   = safe_get(info, "currentPrice", 0)
        week52_high = safe_get(info, "fiftyTwoWeekHigh")
        week52_low  = safe_get(info, "fiftyTwoWeekLow")
        rev_raw = safe_get(info, "revenueGrowth")
        gross_raw = safe_get(info, "grossMargins")
        rev_growth = rev_raw * 100 if rev_raw is not None else None
        gross_margin = gross_raw * 100 if gross_raw is not None else None

        from_high = ((week52_high - current_p) / week52_high * 100
                     if week52_high > 0 else 0)

        results[ticker] = {
            "rev_growth":    rev_growth,
            "gross_margin":  gross_margin,
            "current_price": current_p,
            "week52_high":   week52_high,
            "week52_low":    week52_low,
            "from_high_pct": from_high,
        }
    return results if results else None


@st.cache_data(ttl=3600)
def get_liquid_cooling_data():
    """液冷设备厂商加速信号：VRT / SMCI"""
    results = {}
    for ticker in ["VRT", "SMCI"]:
        info = fetch_yf_info(ticker)
        if not info:
            continue

        current_p    = safe_get(info, "currentPrice", 0)
        week52_high  = safe_get(info, "fiftyTwoWeekHigh")
        week52_low   = safe_get(info, "fiftyTwoWeekLow")
        rev_raw = safe_get(info, "revenueGrowth")
        gross_raw = safe_get(info, "grossMargins")
        rev_growth = rev_raw * 100 if rev_raw is not None else None
        gross_margin = gross_raw * 100 if gross_raw is not None else None

        price_pos = ((current_p - week52_low) / (week52_high - week52_low) * 100
                     if week52_high > week52_low else 50)

        results[ticker] = {
            "rev_growth":    rev_growth,
            "gross_margin":  gross_margin,
            "current_price": current_p,
            "week52_high":   week52_high,
            "week52_low":    week52_low,
            "price_pos_pct": price_pos,
        }
    return results if results else None


@st.cache_data(ttl=3600)
def get_power_data():
    """电力基础设施压力信号：NEE / SO"""
    results = {}
    for ticker in ["NEE", "SO"]:
        info = fetch_yf_info(ticker)
        if not info:
            continue

        current_p   = safe_get(info, "currentPrice", 0)
        week52_high = safe_get(info, "fiftyTwoWeekHigh")
        week52_low  = safe_get(info, "fiftyTwoWeekLow")
        rev_raw = safe_get(info, "revenueGrowth")
        op_raw = safe_get(info, "operatingMargins")
        rev_growth = rev_raw * 100 if rev_raw is not None else None
        op_margin = op_raw * 100 if op_raw is not None else None

        price_pos = ((current_p - week52_low) / (week52_high - week52_low) * 100
                     if week52_high > week52_low else 50)

        results[ticker] = {
            "rev_growth":    rev_growth,
            "op_margin":     op_margin,
            "current_price": current_p,
            "week52_high":   week52_high,
            "week52_low":    week52_low,
            "price_pos_pct": price_pos,
        }
    return results if results else None


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

def score_aof(aof):
    if aof < 1.5:
        return 0, "green", "↗", "SAFE"
    elif aof < 2.5:
        return round((aof - 1.5) / 1.0 * 33), "yellow", "→", "WATCH"
    elif aof < 3.5:
        return round(33 + (aof - 2.5) / 1.0 * 34), "orange", "↘", "WARNING"
    else:
        return round(min(100, 67 + (aof - 3.5) / 0.5 * 33)), "red", "↓", "CRITICAL"


def score_reit(reit_data):
    if not reit_data:
        return 50, "gray", "—", "N/A"
    scores = []
    for d in reit_data.values():
        fh = d.get("from_high_pct", 0)
        rg = d.get("rev_growth")
        ps = 10 if fh < 5 else (35 if fh < 15 else (60 if fh < 25 else (80 if fh < 40 else 95)))
        gs = 50 if rg is None else (10 if rg > 12 else (30 if rg > 6 else (55 if rg > 0 else 80)))
        scores.append(ps * 0.65 + gs * 0.35)
    avg = sum(scores) / len(scores)
    if avg < 25:   return round(avg), "green",  "↗", "SAFE"
    elif avg < 50: return round(avg), "yellow", "→", "WATCH"
    elif avg < 70: return round(avg), "orange", "↘", "WARNING"
    else:          return round(avg), "red",    "↓", "CRITICAL"


def score_liquid(lc_data):
    if not lc_data:
        return 50, "gray", "—", "N/A"
    scores = []
    for d in lc_data.values():
        g  = d.get("rev_growth")
        pp = d.get("price_pos_pct", 50)
        gs = 50 if g is None else (10 if g < 10 else (30 if g < 30 else (55 if g < 60 else (75 if g < 100 else 90))))
        ps = 80 if pp > 80 else (60 if pp > 60 else (40 if pp > 40 else 20))
        scores.append(gs * 0.65 + ps * 0.35)
    avg = sum(scores) / len(scores)
    if avg < 25:   return round(avg), "green",  "↗", "SAFE"
    elif avg < 50: return round(avg), "yellow", "→", "WATCH"
    elif avg < 70: return round(avg), "orange", "↘", "WARNING"
    else:          return round(avg), "red",    "↓", "CRITICAL"


def score_power(power_data):
    if not power_data:
        return 30, "gray", "—", "N/A"
    scores = []
    for d in power_data.values():
        g  = d.get("rev_growth")
        pp = d.get("price_pos_pct", 50)
        gs = 50 if g is None else (15 if g < 3 else (35 if g < 8 else (60 if g < 15 else 80)))
        ps = 70 if pp > 75 else (50 if pp > 50 else (30 if pp > 25 else 15))
        scores.append(gs * 0.6 + ps * 0.4)
    avg = sum(scores) / len(scores)
    if avg < 25:   return round(avg), "green",  "↗", "SAFE"
    elif avg < 45: return round(avg), "yellow", "→", "WATCH"
    elif avg < 65: return round(avg), "orange", "↘", "WARNING"
    else:          return round(avg), "red",    "↓", "CRITICAL"


# =========================================================
# 顶部标题
# =========================================================

render_header("🏗️ 数据中心资产减值", "核心监测维度：GPU迭代速度是否已超出数据中心基础设施的金融折旧周期", symbol="DCOI · 数据中心淘汰指数")

# =========================================================
# 数据加载
# =========================================================

with st.spinner("正在通过 yfinance 拉取 REIT · 液冷厂商 · 电力数据..."):
    reit_data  = get_reit_data()
    lc_data    = get_liquid_cooling_data()
    power_data = get_power_data()

# =========================================================
# 各分项评分
# =========================================================

aof_s,   aof_color,   aof_arrow,   aof_status   = score_aof(AOF)
reit_s,  reit_color,  reit_arrow,  reit_status  = score_reit(reit_data)
lc_s,    lc_color,    lc_arrow,    lc_status    = score_liquid(lc_data)
power_s, power_color, power_arrow, power_status = score_power(power_data)

dcoi = compute_dcoi(aof_s, reit_s, lc_s, power_s)
register_score("straw3", dcoi)
state, state_color, state_hex, state_eng, state_cn = get_state(dcoi)

bar_color_map = {"green": "#22c55e", "yellow": "#fbbf24", "orange": "#f97316", "red": "#ef4444"}
bar_color = bar_color_map.get(state_color, "#94a3b8")

# =========================================================
# DCOI 总分大卡片
# =========================================================

st.markdown(render_osci_card(
    "DATA CENTER OBSOLESCENCE INDEX", dcoi, state, f"综合评分：{state_cn}",
    bar_color=bar_color, state_detail=state_eng,
    components_html="GPU功率压力 ×0.25 · REIT估值 ×0.35<br>液冷信号 ×0.25 · 电力压力 ×0.15",
    score_display=f"{dcoi:.0f}",
), unsafe_allow_html=True)

# =========================================================
# 四张指标卡片
# =========================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""<div class="metric-card">
  <div class="metric-label">AOF 资产淘汰 <span class="source-tag-warn static-data-badge">⚠ 静态基准</span></div>
  <div class="metric-row">
    <span class="metric-number {aof_color}">{AOF}x</span>
    <span class="metric-arrow {aof_color}">{aof_arrow}</span>
  </div>
  <div class="metric-desc">
    {CURRENT_DEPLOY_GPU} 机柜 {CURRENT_RACK_KW}kW ÷ 老机房上限 {LEGACY_RACK_LIMIT_KW}kW<br>
    倍数越高，存量风冷机房技术性报废越严重
  </div>
</div>""", unsafe_allow_html=True)

with c2:
    if reit_data:
        eqix   = reit_data.get("EQIX", {})
        dlr    = reit_data.get("DLR",  {})
        eqix_h = eqix.get("from_high_pct", 0)
        dlr_h  = dlr.get("from_high_pct",  0)
        avg_h  = (eqix_h + dlr_h) / 2
        eqix_g = eqix.get("rev_growth")
        dlr_g  = dlr.get("rev_growth")
        desc2    = f"EQIX 距52周高点 -{eqix_h:.1f}% · DLR -{dlr_h:.1f}%<br>营收增速 EQIX {fmt_pct(eqix_g)} · DLR {fmt_pct(dlr_g)}"
        display2 = f"-{avg_h:.1f}%"
    else:
        desc2    = "yfinance 数据暂时无法获取<br>请稍后刷新重试"
        display2 = "N/A"
    st.markdown(f"""<div class="metric-card">
  <div class="metric-label">REIT 估值压力 <span class="source-tag">YF</span></div>
  <div class="metric-row">
    <span class="metric-number {reit_color}">{display2}</span>
    <span class="metric-arrow {reit_color}">{reit_arrow}</span>
  </div>
  <div class="metric-desc">{desc2}</div>
</div>""", unsafe_allow_html=True)

with c3:
    if lc_data:
        vrt      = lc_data.get("VRT",  {})
        smci     = lc_data.get("SMCI", {})
        vrt_g    = vrt.get("rev_growth")
        smci_g   = smci.get("rev_growth")
        vrt_pos  = vrt.get("price_pos_pct", 50)
        smci_pos = smci.get("price_pos_pct", 50)
        avg_g    = average_present([vrt_g, smci_g])
        desc3    = (f"Vertiv营收增速 {fmt_pct(vrt_g)} · SMCI {fmt_pct(smci_g)}<br>"
                    f"股价位置 VRT {vrt_pos:.0f}% · SMCI {smci_pos:.0f}% (52周区间)")
        display3 = fmt_pct(avg_g)
    else:
        desc3    = "yfinance 数据暂时无法获取<br>请稍后刷新重试"
        display3 = "N/A"
    st.markdown(f"""<div class="metric-card">
  <div class="metric-label">液冷加速信号 <span class="source-tag">YF</span></div>
  <div class="metric-row">
    <span class="metric-number {lc_color}">{display3}</span>
    <span class="metric-arrow {lc_color}">{lc_arrow}</span>
  </div>
  <div class="metric-desc">{desc3}</div>
</div>""", unsafe_allow_html=True)

with c4:
    if power_data:
        nee     = power_data.get("NEE", {})
        so      = power_data.get("SO",  {})
        nee_g   = nee.get("rev_growth")
        so_g    = so.get("rev_growth")
        nee_pos = nee.get("price_pos_pct", 50)
        so_pos  = so.get("price_pos_pct",  50)
        avg_pg  = average_present([nee_g, so_g])
        desc4   = (f"NEE增速 {fmt_pct(nee_g)} · SO增速 {fmt_pct(so_g)}<br>"
                   f"股价位置 NEE {nee_pos:.0f}% · SO {so_pos:.0f}% (52周区间)")
        display4 = fmt_pct(avg_pg)
    else:
        desc4    = "yfinance 数据暂时无法获取<br>请稍后刷新重试"
        display4 = "N/A"
    st.markdown(f"""<div class="metric-card">
  <div class="metric-label">电力基础设施 <span class="source-tag">YF</span></div>
  <div class="metric-row">
    <span class="metric-number {power_color}">{display4}</span>
    <span class="metric-arrow {power_color}">{power_arrow}</span>
  </div>
  <div class="metric-desc">{desc4}</div>
</div>""", unsafe_allow_html=True)

# =========================================================
# Alert 结论框
# =========================================================

alert_map = {
    "SAFE": {
        "box_class": "alert-box-green", "icon": "✅", "title_color": "#22c55e",
        "title": "结论：数据中心基础设施与GPU路线图仍然兼容，资产减值风险低",
        "body": f'当前 DCOI = <span class="green"><b>{dcoi}</b></span>，处于安全区间。现有数据中心资产能够支撑当前主流GPU部署需求，REIT估值稳定，市场尚未对底层资产进行系统性重新定价。'
    },
    "WATCH": {
        "box_class": "alert-box", "icon": "👁", "title_color": "#fbbf24",
        "title": "结论：GPU功率密度跃迁压力出现，液冷改造需求开始爆发",
        "body": f'当前 DCOI = <span class="yellow"><b>{dcoi}</b></span>，进入观察区间。AOF系数显示老机房兼容性开始下降，液冷厂商订单加速是风冷资产进入折旧加速期的领先信号。建议关注 EQIX/DLR 下季度财报中的 impairment charges 与 retrofit CapEx 数字。'
    },
    "WARNING": {
        "box_class": "alert-box", "icon": "⚠️", "title_color": "#f97316",
        "title": "结论：风冷资产开始系统性折价，数据中心REIT估值承压",
        "body": f'当前 DCOI = <span class="orange"><b>{dcoi}</b></span>，进入高危区间。市场正在重新定价 AI 基础设施资产：AI-ready液冷机房溢价扩大，传统风冷机房折价加剧。注意：这是资产端信号，尚未构成金融传导事件。需联动资本开支偏离共同确认。'
    },
    "CRITICAL": {
        "box_class": "alert-box-red", "icon": "🔴", "title_color": "#ef4444",
        "title": "结论：AI基础设施技术性减值信号明确，需与资本开支偏离联动确认传导",
        "body": f'当前 DCOI = <span class="red"><b>{dcoi}</b></span>，进入危机区间。大量存量数据中心资产面临提前技术性报废：GPU迭代速度已远超机房设计寿命，液冷改造成本接近重建，REIT底层资产价值受损。注意：CASCADE事件（CMBS暴雷/信贷收缩）需要资本开支偏离与资产减值联动触发；本因子单独不构成系统性金融危机。建议监控各大银行10-Q中对数据中心抵押贷款的拨备变化。'
    }
}

alert = alert_map.get(state, alert_map["WATCH"])
st.markdown(render_alert(state, alert["title"], alert["body"]), unsafe_allow_html=True)

# =========================================================
# 下方面板：检测逻辑 + GPU 功率密度图
# =========================================================

lp, rp = st.columns([1, 1.5])

with lp:
    st.markdown("""<div class="panel">
  <div class="panel-title">⚙️ 检测逻辑</div>
  <div class="logic-step">
    <div class="step-num">1</div>
    <div class="step-text"><b>AOF 资产淘汰系数（×0.25）</b>：当前主流GPU机柜功率 ÷ 老机房设计上限，倍数越高代表存量机房技术性报废越严重</div>
  </div>
  <div class="threshold-block">
    <div class="threshold-row"><div class="t-dot" style="background:#22c55e;"></div><div class="t-label">AOF &lt; 1.5x</div><div class="t-arrow">→</div><div class="t-status green">SAFE</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#fbbf24;"></div><div class="t-label">AOF 1.5–2.5x</div><div class="t-arrow">→</div><div class="t-status yellow">WATCH</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#f97316;"></div><div class="t-label">AOF 2.5–3.5x</div><div class="t-arrow">→</div><div class="t-status orange">WARNING</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#ef4444;"></div><div class="t-label">AOF &gt; 3.5x</div><div class="t-arrow">→</div><div class="t-status red">CRITICAL</div></div>
  </div>
  <div class="logic-step" style="margin-top:14px;">
    <div class="step-num">2</div>
    <div class="step-text"><b>REIT 估值压力（×0.35）</b>：EQIX/DLR 距52周高点跌幅，市场对底层资产的直接重定价信号</div>
  </div>
  <div class="threshold-block">
    <div class="threshold-row"><div class="t-dot" style="background:#22c55e;"></div><div class="t-label">距高点 &lt; 5%</div><div class="t-arrow">→</div><div class="t-status green">SAFE</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#fbbf24;"></div><div class="t-label">距高点 5–15%</div><div class="t-arrow">→</div><div class="t-status yellow">WATCH</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#f97316;"></div><div class="t-label">距高点 15–25%</div><div class="t-arrow">→</div><div class="t-status orange">WARNING</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#ef4444;"></div><div class="t-label">距高点 &gt; 25%</div><div class="t-arrow">→</div><div class="t-status red">CRITICAL</div></div>
  </div>
  <div class="logic-step" style="margin-top:14px;">
    <div class="step-num">3</div>
    <div class="step-text"><b>液冷加速信号（×0.25）</b>：Vertiv/SMCI 营收增速，液冷厂商爆发 = 风冷淘汰加速</div>
  </div>
  <div class="logic-step" style="margin-top:6px;">
    <div class="step-num">4</div>
    <div class="step-text"><b>电力压力（×0.15）</b>：NEE/SO 相对强弱，电力需求旺盛是功率密度危机的物理证据</div>
  </div>
</div>""", unsafe_allow_html=True)

with rp:
    st.markdown('<div class="panel"><div class="panel-title">⚡ GPU 功率密度代际跃迁（单机柜 kW）</div>', unsafe_allow_html=True)

    gens     = [g["gen"]          for g in GPU_GENERATIONS]
    rack_mid = [(g["rack_kw_min"] + g["rack_kw_max"]) / 2 for g in GPU_GENERATIONS]
    rack_min = [g["rack_kw_min"]  for g in GPU_GENERATIONS]
    rack_max = [g["rack_kw_max"]  for g in GPU_GENERATIONS]
    statuses = [g["status"]       for g in GPU_GENERATIONS]

    bar_colors = []
    for s in statuses:
        if s == "legacy":   bar_colors.append("#334155")
        elif s == "active": bar_colors.append("#f97316")
        elif s == "current":bar_colors.append("#ef4444")
        else:               bar_colors.append("#7c3aed")

    fig = go.Figure()

    fig.add_shape(type="line", x0=-0.5, x1=len(gens) - 0.5,
                  y0=LEGACY_RACK_LIMIT_KW, y1=LEGACY_RACK_LIMIT_KW,
                  line=dict(color="#22c55e", width=1.5, dash="dash"))
    fig.add_annotation(x=len(gens) - 0.6, y=LEGACY_RACK_LIMIT_KW + 6,
                       text=f"传统风冷上限 {LEGACY_RACK_LIMIT_KW}kW",
                       showarrow=False, font=dict(color="#22c55e", size=11), xanchor="right")

    fig.add_shape(type="line", x0=-0.5, x1=len(gens) - 0.5,
                  y0=UPGRADED_RACK_LIMIT_KW, y1=UPGRADED_RACK_LIMIT_KW,
                  line=dict(color="#fbbf24", width=1.5, dash="dot"))
    fig.add_annotation(x=len(gens) - 0.6, y=UPGRADED_RACK_LIMIT_KW + 6,
                       text=f"改造风冷上限 {UPGRADED_RACK_LIMIT_KW}kW",
                       showarrow=False, font=dict(color="#fbbf24", size=11), xanchor="right")

    fig.add_trace(go.Bar(
        x=gens, y=rack_mid,
        marker_color=bar_colors, marker_line_width=0, width=0.6,
        error_y=dict(
            type="data", symmetric=False,
            array=[mx - mid for mx, mid in zip(rack_max, rack_mid)],
            arrayminus=[mid - mn for mn, mid in zip(rack_min, rack_mid)],
            color="rgba(255,255,255,0.2)", thickness=2,
        ),
        text=[f"{int(mid)}kW" for mid in rack_mid],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=13),
    ))

    fig.update_layout(
        height=310,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", size=12),
        margin=dict(l=10, r=20, t=10, b=10),
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#94a3b8", size=13)),
        yaxis=dict(
            title="机柜功率 (kW)", gridcolor="rgba(255,255,255,0.05)", zeroline=False,
            tickfont=dict(color="#94a3b8", size=11), title_font=dict(color="#94a3b8", size=11),
        ),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
<div class="legend-row">
  <div class="legend-item"><div class="legend-dot" style="background:#334155;"></div>历史世代（已淘汰）</div>
  <div class="legend-item"><div class="legend-dot" style="background:#f97316;"></div>当前主力部署</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ef4444;"></div>最新一代（在售）</div>
  <div class="legend-item"><div class="legend-dot" style="background:#7c3aed;"></div>下一代（路线图）</div>
</div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 页脚
# =========================================================

render_footer("Yahoo Finance · 每小时缓存 · AOF 基准参数人工校准")
