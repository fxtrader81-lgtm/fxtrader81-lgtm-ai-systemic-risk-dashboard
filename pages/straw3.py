import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# 补全定义 (补全缺失的 AOF 及 GPU 数据结构)
# =========================================================
CURRENT_DEPLOY_GPU = "NVIDIA H100"
CURRENT_RACK_KW = 40.0
LEGACY_RACK_LIMIT_KW = 15.0
UPGRADED_RACK_LIMIT_KW = 30.0
AOF = CURRENT_RACK_KW / LEGACY_RACK_LIMIT_KW

GPU_GENERATIONS = [
    {"gen": "K80/P100", "year": 2016, "rack_kw_min": 5, "rack_kw_max": 8, "status": "legacy"},
    {"gen": "V100", "year": 2018, "rack_kw_min": 8, "rack_kw_max": 12, "status": "legacy"},
    {"gen": "A100", "year": 2020, "rack_kw_min": 15, "rack_kw_max": 25, "status": "active"},
    {"gen": "H100", "year": 2022, "rack_kw_min": 30, "rack_kw_max": 50, "status": "active"},
    {"gen": "B200", "year": 2024, "rack_kw_min": 60, "rack_kw_max": 120, "status": "current"},
]

# =========================================================
# 页面配置
# =========================================================
st.set_page_config(
    page_title="稻草三：数据中心资产减值",
    layout="wide"
)

# =========================================================
# CSS — 与稻草一/二完全一致的黑金风格
# =========================================================

st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #050816 !important;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.stApp { background-color: #050816 !important; }
section[data-testid="stMain"] > div { background-color: #050816 !important; }
.block-container {
    padding-top: 1.8rem;
    padding-left: 2.2rem;
    padding-right: 2.2rem;
    max-width: 1600px;
    background-color: #050816 !important;
}

.main-title {
    font-size: 32px; font-weight: 800; color: #ffffff;
    margin: 0 0 6px 0; letter-spacing: -0.5px;
}
.sub-title {
    font-size: 16px !important;
    color: #cbd5e1 !important;
    margin: 0;
}
.timestamp-text { font-size: 13px; color: #475569; margin-bottom: 8px; display: block; }
.symbol-badge {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 3px 16px;
    font-size: 13px; font-weight: 600; color: #94a3b8; letter-spacing: 1px;
}

/* DCOI 总分大卡片 */
.osci-card {
    background: linear-gradient(135deg, #0b1120 0%, #0d1829 100%);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.osci-left { display: flex; flex-direction: column; gap: 6px; }
.osci-label { font-size: 13px; font-weight: 600; color: #475569; letter-spacing: 1.5px; text-transform: uppercase; }
.osci-score { font-size: 72px; font-weight: 800; line-height: 1; letter-spacing: -3px; }
.osci-desc { font-size: 15px; color: #94a3b8; margin-top: 4px; }
.osci-right { text-align: right; }
.osci-state-label { font-size: 13px; color: #475569; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
.osci-state { font-size: 28px; font-weight: 800; letter-spacing: 0.5px; }
.osci-bar-wrap { margin-top: 12px; width: 280px; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; }
.osci-bar-fill { height: 6px; border-radius: 3px; }

/* 指标卡片 */
.metric-card {
    background-color: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 20px 22px 18px;
    height: 168px;
}
.metric-label {
    color: #ffffff; font-size: 18px; font-weight: 600;
    margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.4px;
}
.metric-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 14px; }
.metric-number { font-size: 38px; font-weight: 800; line-height: 1; letter-spacing: -1.5px; }
.metric-arrow { font-size: 20px; font-weight: 700; }
.metric-desc, .metric-desc p {
    color: #cbd5e1 !important;
    font-size: 15px !important;
    line-height: 1.6;
}

.green  { color: #22c55e; }
.red    { color: #ef4444; }
.yellow { color: #fbbf24; }
.orange { color: #f97316; }
.gray   { color: #94a3b8; }

/* Alert 结论框 */
.alert-box {
    margin: 18px 0; background: #120e00;
    border: 1px solid rgba(251,191,36,0.18);
    border-radius: 14px; padding: 22px 26px;
    display: flex; gap: 18px; align-items: flex-start;
}
.alert-box-red {
    margin: 18px 0; background: #120000;
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 14px; padding: 22px 26px;
    display: flex; gap: 18px; align-items: flex-start;
}
.alert-box-green {
    margin: 18px 0; background: #001208;
    border: 1px solid rgba(34,197,94,0.2);
    border-radius: 14px; padding: 22px 26px;
    display: flex; gap: 18px; align-items: flex-start;
}
.alert-icon { font-size: 44px; flex-shrink: 0; line-height: 1; }
.alert-title {
    font-size: 23px !important;
    font-weight: 700;
    margin-bottom: 10px;
}
.alert-text, .alert-text p {
    font-size: 17px !important;
    color: #cbd5e1 !important;
    line-height: 1.75;
}

/* Panel */
.panel {
    background-color: #0b1120; border-radius: 14px;
    padding: 22px; border: 1px solid rgba(255,255,255,0.07);
}
.panel-title {
    font-size: 20px !important;
    font-weight: 700;
    margin-bottom: 20px;
    color: #e2e8f0;
}

.logic-step { display: flex; gap: 12px; margin-bottom: 13px; align-items: flex-start; }
.step-num {
    width: 22px; height: 22px; min-width: 22px; border-radius: 50%;
    background: #1e3a5f; color: #60a5fa; font-size: 12px; font-weight: 700;
    display: flex; align-items: center; justify-content: center; margin-top: 2px;
}
.step-text, .logic-step p {
    font-size: 16px !important;
    color: #cbd5e1 !important;
    line-height: 1.6;
}
.threshold-block { margin-left: 34px; margin-top: 8px; }
.threshold-row {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 12px; border-radius: 7px; margin-bottom: 6px;
    background: rgba(255,255,255,0.02);
}
.t-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.t-label, .threshold-row p {
    font-size: 15px !important;
    color: #cbd5e1 !important;
    flex: 1;
}
.t-arrow { font-size: 13px; color: #475569; }
.t-status { font-size: 15px !important; font-weight: 600; }

/* 数据源标签 */
.source-tag {
    display: inline-block;
    background: rgba(96,165,250,0.1);
    border: 1px solid rgba(96,165,250,0.2);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 12px;
    color: #60a5fa;
    margin-left: 8px;
}
.source-tag-gray {
    display: inline-block;
    background: rgba(148,163,184,0.1);
    border: 1px solid rgba(148,163,184,0.2);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 12px;
    color: #94a3b8;
    margin-left: 8px;
}
.source-tag-warn {
    display: inline-block;
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.25);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 12px;
    color: #fbbf24;
    margin-left: 8px;
}

/* AOF 功率密度表格 */
.gpu-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
.gpu-table th {
    font-size: 12px; color: #475569; text-transform: uppercase;
    letter-spacing: 0.5px; padding: 8px 12px; text-align: left;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.gpu-table td {
    font-size: 14px; color: #cbd5e1; padding: 9px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
}
.gpu-table tr:last-child td { border-bottom: none; }
.gpu-gen-active { color: #fbbf24; font-weight: 700; }
.gpu-gen-danger { color: #ef4444; font-weight: 700; }

.footer-text { margin-top: 14px; color: #1e293b; font-size: 11px; text-align: right; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
.modebar { display: none !important; }

</style>
""", unsafe_allow_html=True)

# =========================================================
# 数据获取配置 — Yahoo Finance
# =========================================================

YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

def fetch_yf_summary(ticker):
    url = (
        f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
        f"?modules=financialData,defaultKeyStatistics,summaryDetail,price"
    )
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        result = data.get("quoteSummary", {}).get("result", [])
        if not result:
            return None
        merged = {}
        for module in result[0].values():
            if isinstance(module, dict):
                merged.update(module)
        return merged
    except Exception:
        return None


def fetch_yf_chart(ticker):
    url = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?interval=1wk&range=1y"
    )
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        return {
            "current_price":   meta.get("regularMarketPrice", 0),
            "week52_high":    meta.get("fiftyTwoWeekHigh", 0),
            "week52_low":     meta.get("fiftyTwoWeekLow", 0),
            "prev_close":     meta.get("chartPreviousClose", 0),
        }
    except Exception:
        return None


def safe_raw(d, key, default=0):
    try:
        v = d.get(key, {})
        if isinstance(v, dict):
            return float(v.get("raw", default))
        return float(v) if v is not None else default
    except Exception:
        return default


@st.cache_data(ttl=3600)
def get_reit_data():
    results = {}
    for ticker in ["EQIX", "DLR"]:
        summary = fetch_yf_summary(ticker)
        chart   = fetch_yf_chart(ticker)
        if not summary and not chart:
            continue

        rev_growth   = safe_raw(summary or {}, "revenueGrowth")    * 100 if summary else 0
        gross_margin = safe_raw(summary or {}, "grossMargins")     * 100 if summary else 0
        debt_equity  = safe_raw(summary or {}, "debtToEquity")             if summary else 0
        current_p    = (chart or {}).get("current_price", 0)
        week52_high  = (chart or {}).get("week52_high",   0)
        week52_low   = (chart or {}).get("week52_low",    0)

        from_high = ((week52_high - current_p) / week52_high * 100
                      if week52_high > 0 else 0)

        results[ticker] = {
            "rev_growth":    rev_growth,
            "gross_margin":  gross_margin,
            "debt_equity":   debt_equity,
            "current_price": current_p,
            "week52_high":   week52_high,
            "week52_low":    week52_low,
            "from_high_pct": from_high,
        }
    return results if results else None


@st.cache_data(ttl=3600)
def get_liquid_cooling_data():
    results = {}
    for ticker in ["VRT", "SMCI"]:
        summary = fetch_yf_summary(ticker)
        chart   = fetch_yf_chart(ticker)
        if not summary and not chart:
            continue

        rev_growth   = safe_raw(summary or {}, "revenueGrowth") * 100 if summary else 0
        gross_margin = safe_raw(summary or {}, "grossMargins")  * 100 if summary else 0
        current_p    = (chart or {}).get("current_price", 0)
        week52_high  = (chart or {}).get("week52_high",   0)
        week52_low   = (chart or {}).get("week52_low",    0)

        price_pos = ((current_p - week52_low) / (week52_high - week52_low) * 100
                      if week52_high > week52_low else 50)

        results[ticker] = {
            "rev_growth":   rev_growth,
            "gross_margin": gross_margin,
            "current_price": current_p,
            "week52_high":  week52_high,
            "week52_low":   week52_low,
            "price_pos_pct": price_pos,
        }
    return results if results else None


@st.cache_data(ttl=3600)
def get_power_data():
    results = {}
    for ticker in ["NEE", "SO"]:
        summary = fetch_yf_summary(ticker)
        chart   = fetch_yf_chart(ticker)
        if not summary and not chart:
            continue

        rev_growth  = safe_raw(summary or {}, "revenueGrowth") * 100 if summary else 0
        op_margin   = safe_raw(summary or {}, "operatingMargins") * 100 if summary else 0
        current_p   = (chart or {}).get("current_price", 0)
        week52_high = (chart or {}).get("week52_high",   0)
        week52_low  = (chart or {}).get("week52_low",    0)

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


def compute_dcoi(aof_score, reit_stress_score, liquid_signal_score, power_stress_score):
    dcoi = (0.25 * aof_score +
            0.35 * reit_stress_score +
            0.25 * liquid_signal_score +
            0.15 * power_stress_score)
    return round(dcoi, 1)


def get_state(dcoi):
    if dcoi < 25:
        return "SAFE", "green", "22c55e", "Compatible Infrastructure", "基础设施与GPU路线图兼容，资产估值稳定，减值风险低。"
    elif dcoi < 45:
        return "WATCH", "yellow", "fbbf24", "Upgrade Stress Emerging", "功率密度跃迁压力出现，液冷需求加速，风冷资产开始承压。"
    elif dcoi < 65:
        return "WARNING", "orange", "f97316", "Asset Repricing Underway", "风冷资产开始系统性折价，REIT估值承压，改造成本攀升。"
    else:
        return "CRITICAL", "red", "ef4444", "Technical Obsolescence Confirmed", "大量AI基建资产技术性贬值信号明确，市场重新定价正在发生。"


def score_aof(aof):
    if aof < 1.5: return 0, "green", "↗", "SAFE"
    elif aof < 2.5:
        s = (aof - 1.5) / 1.0 * 33
        return round(s), "yellow", "→", "WATCH"
    elif aof < 3.5:
        s = 33 + (aof - 2.5) / 1.0 * 34
        return round(s), "orange", "↘", "WARNING"
    else:
        s = min(100, 67 + (aof - 3.5) / 0.5 * 33)
        return round(s), "red", "↓", "CRITICAL"


def score_reit(reit_data):
    if not reit_data: return 50, "gray", "—", "N/A"
    scores = []
    for ticker, d in reit_data.items():
        from_high = d.get("from_high_pct", 0)
        rev_g     = d.get("rev_growth", 5)
        ps = 10 if from_high < 5 else 35 if from_high < 15 else 60 if from_high < 25 else 80 if from_high < 40 else 95
        gs = 10 if rev_g > 12 else 30 if rev_g > 6 else 55 if rev_g > 0 else 80
        scores.append(ps * 0.65 + gs * 0.35)
    avg = sum(scores) / len(scores) if scores else 50
    return (round(avg), "green", "↗", "SAFE") if avg < 25 else (round(avg), "yellow", "→", "WATCH") if avg < 50 else (round(avg), "orange", "↘", "WARNING") if avg < 70 else (round(avg), "red", "↓", "CRITICAL")


def score_liquid(lc_data):
    if not lc_data: return 50, "gray", "—", "N/A"
    scores = []
    for ticker, d in lc_data.items():
        g = d.get("rev_growth", 0) or 0
        price_pos = d.get("price_pos_pct", 50)
        gs = 10 if g < 10 else 30 if g < 30 else 55 if g < 60 else 75 if g < 100 else 90
        ps = 80 if price_pos > 80 else 60 if price_pos > 60 else 40 if price_pos > 40 else 20
        scores.append(gs * 0.65 + ps * 0.35)
    avg = sum(scores) / len(scores) if scores else 50
    return (round(avg), "green", "↗", "SAFE") if avg < 25 else (round(avg), "yellow", "→", "WATCH") if avg < 50 else (round(avg), "orange", "↘", "WARNING") if avg < 70 else (round(avg), "red", "↓", "CRITICAL")


def score_power(power_data):
    if not power_data: return 30, "gray", "—", "N/A"
    scores = []
    for ticker, d in power_data.items():
        g = d.get("rev_growth", 0) or 0
        price_pos = d.get("price_pos_pct", 50)
        gs = 15 if g < 3 else 35 if g < 8 else 60 if g < 15 else 80
        ps = 70 if price_pos > 75 else 50 if price_pos > 50 else 30 if price_pos > 25 else 15
        scores.append(gs * 0.6 + ps * 0.4)
    avg = sum(scores) / len(scores) if scores else 30
    return (round(avg), "green", "↗", "SAFE") if avg < 25 else (round(avg), "yellow", "→", "WATCH") if avg < 45 else (round(avg), "orange", "↘", "WARNING") if avg < 65 else (round(avg), "red", "↓", "CRITICAL")


# =========================================================
# 主程序
# =========================================================

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 20px;">
  <div>
    <div class="main-title">🏗️ 稻草三：数据中心资产技术性减值</div>
    <div class="sub-title">核心检测维度：AI时代GPU迭代速度是否已超出数据中心基础设施的金融折旧周期</div>
  </div>
  <div style="text-align:right; padding-top:4px;">
    <span class="timestamp-text">🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    <span class="symbol-badge">DCOI · 数据中心淘汰指数</span>
  </div>
</div>
""", unsafe_allow_html=True)

with st.spinner("正在拉取数据..."):
    reit_data  = get_reit_data()
    lc_data    = get_liquid_cooling_data()
    power_data = get_power_data()

aof_s,   aof_color,   aof_arrow,   aof_status   = score_aof(AOF)
reit_s,  reit_color,  reit_arrow,  reit_status  = score_reit(reit_data)
lc_s,    lc_color,    lc_arrow,    lc_status    = score_liquid(lc_data)
power_s, power_color, power_arrow, power_status = score_power(power_data)

dcoi  = compute_dcoi(aof_s, reit_s, lc_s, power_s)
state, state_color, state_hex, state_eng, state_cn = get_state(dcoi)
bar_color = {"green": "#22c55e", "yellow": "#fbbf24", "orange": "#f97316", "red": "#ef4444"}.get(state_color, "#94a3b8")

st.markdown(f"""
<div class="osci-card">
  <div class="osci-left">
    <div class="osci-label">DATA CENTER OBSOLESCENCE INDEX</div>
    <div style="display:flex; align-items:baseline; gap:12px;">
      <div class="osci-score {state_color}">{dcoi}</div>
      <div style="font-size:18px; color:#475569; font-weight:600;">/100</div>
    </div>
    <div class="osci-desc">综合评分：{state_cn}</div>
    <div class="osci-bar-wrap">
      <div class="osci-bar-fill" style="width:{dcoi}%; background:{bar_color};"></div>
    </div>
  </div>
  <div class="osci-right">
    <div class="osci-state-label">SYSTEM STATE</div>
    <div class="osci-state {state_color}">{state}</div>
    <div style="margin-top:8px; font-size:14px; color:#64748b;">{state_eng}</div>
  </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">AOF 资产淘汰</div><div class="metric-row"><span class="metric-number {aof_color}">{AOF:.1f}x</span></div><div class="metric-desc">{CURRENT_DEPLOY_GPU} vs 老机房</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">REIT 估值压力</div><div class="metric-row"><span class="metric-number {reit_color}">{reit_s}</span></div><div class="metric-desc">市场重定价信号</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">液冷加速</div><div class="metric-row"><span class="metric-number {lc_color}">{lc_s}</span></div><div class="metric-desc">需求爆发信号</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">电力压力</div><div class="metric-row"><span class="metric-number {power_color}">{power_s}</span></div><div class="metric-desc">物理约束信号</div></div>', unsafe_allow_html=True)

lp, rp = st.columns([1, 1.5])
with lp:
    st.markdown('<div class="panel"><div class="panel-title">⚙️ 检测逻辑</div><p>基于功率密度跃迁与金融资产折旧的联动模型。</p></div>', unsafe_allow_html=True)
with rp:
    st.markdown('<div class="panel"><div class="panel-title">⚡ GPU 功率密度跃迁</div>', unsafe_allow_html=True)
    fig = go.Figure(data=[go.Bar(x=[g["gen"] for g in GPU_GENERATIONS], y=[(g["rack_kw_min"]+g["rack_kw_max"])/2 for g in GPU_GENERATIONS])])
    fig.update_layout(height=250, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#ffffff"))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<p style="font-size:12px; color:#475569;">数据来源：Yahoo Finance / 内部基准模拟</p>', unsafe_allow_html=True)
