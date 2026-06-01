import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# 1. 配置项与常量
# =========================================================
CURRENT_DEPLOY_GPU = "NVIDIA H100"
CURRENT_RACK_KW = 40.0
LEGACY_RACK_LIMIT_KW = 15.0
UPGRADED_RACK_LIMIT_KW = 30.0
AOF = CURRENT_RACK_KW / LEGACY_RACK_LIMIT_KW

GPU_GENERATIONS = [
    {"gen": "K80/P100", "year": 2016, "rack_kw_min": 5, "rack_kw_max": 8, "status": "legacy"},
    {"gen": "V100",     "year": 2018, "rack_kw_min": 8, "rack_kw_max": 12, "status": "legacy"},
    {"gen": "A100",     "year": 2020, "rack_kw_min": 15, "rack_kw_max": 25, "status": "active"},
    {"gen": "H100",     "year": 2022, "rack_kw_min": 30, "rack_kw_max": 50, "status": "active"},
    {"gen": "B200",     "year": 2024, "rack_kw_min": 60, "rack_kw_max": 120, "status": "current"},
]

# =========================================================
# 2. 页面配置与 CSS 样式
# =========================================================
st.set_page_config(page_title="稻草三：数据中心资产减值", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #050816 !important; color: white; font-family: sans-serif; }
.main-title { font-size: 32px; font-weight: 800; color: #ffffff; margin: 0 0 6px 0; }
.sub-title { font-size: 16px !important; color: #cbd5e1 !important; }
.osci-card { background: linear-gradient(135deg, #0b1120 0%, #0d1829 100%); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 28px 32px; margin-bottom: 20px; display: flex; justify-content: space-between; }
.metric-card { background-color: #0b1120; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 20px; height: 168px; }
.metric-label { color: #ffffff; font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.metric-number { font-size: 38px; font-weight: 800; }
.panel { background-color: #0b1120; border-radius: 14px; padding: 22px; border: 1px solid rgba(255,255,255,0.07); }
.panel-title { font-size: 20px !important; font-weight: 700; margin-bottom: 20px; color: #e2e8f0; }
.green { color: #22c55e; } .red { color: #ef4444; } .yellow { color: #fbbf24; } .orange { color: #f97316; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. 数据获取逻辑
# =========================================================
YF_HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_yf_summary(ticker):
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,defaultKeyStatistics,summaryDetail,price"
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=5)
        return r.json().get("quoteSummary", {}).get("result", [{}])[0] if r.status_code == 200 else None
    except: return None

def fetch_yf_chart(ticker):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1wk&range=1y"
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=5)
        return r.json().get("chart", {}).get("result", [{}])[0].get("meta", {}) if r.status_code == 200 else {}
    except: return {}

def safe_raw(d, key, default=0):
    try: return float(d.get(key, {}).get("raw", default)) if isinstance(d.get(key), dict) else default
    except: return default

@st.cache_data(ttl=3600)
def get_reit_data():
    results = {}
    for t in ["EQIX", "DLR"]:
        s, c = fetch_yf_summary(t), fetch_yf_chart(t)
        if s:
            h = c.get("fiftyTwoWeekHigh", 1)
            results[t] = {"from_high_pct": ((h - c.get("regularMarketPrice", 0)) / h * 100), "rev_growth": safe_raw(s, "revenueGrowth") * 100}
    return results

@st.cache_data(ttl=3600)
def get_liquid_cooling_data():
    results = {}
    for t in ["VRT", "SMCI"]:
        s, c = fetch_yf_summary(t), fetch_yf_chart(t)
        if s: results[t] = {"rev_growth": safe_raw(s, "revenueGrowth") * 100, "price_pos_pct": 50}
    return results

@st.cache_data(ttl=3600)
def get_power_data():
    results = {}
    for t in ["NEE", "SO"]:
        s = fetch_yf_summary(t)
        if s: results[t] = {"rev_growth": safe_raw(s, "revenueGrowth") * 100, "price_pos_pct": 50}
    return results

# =========================================================
# 4. 评分与渲染
# =========================================================
def score_aof(aof):
    if aof < 1.5: return 0, "green", "SAFE"
    elif aof < 3.5: return 50, "orange", "WARNING"
    return 80, "red", "CRITICAL"

st.markdown(f'<div class="main-title">🏗️ 稻草三：数据中心资产技术性减值</div>', unsafe_allow_html=True)

reit_data, lc_data, power_data = get_reit_data(), get_liquid_cooling_data(), get_power_data()
aof_s, aof_color, aof_status = score_aof(AOF)

st.markdown(f"""<div class="osci-card">
    <div><div class="osci-label">DCOI 指数</div><div class="osci-score" style="font-size:60px;">{aof_s}</div></div>
    <div><div class="osci-state">{aof_status}</div></div>
</div>""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="metric-card"><div class="metric-label">AOF 系数</div><div class="metric-number">{AOF:.2f}x</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><div class="metric-label">REIT 压力</div><div class="metric-number">{len(reit_data)}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><div class="metric-label">液冷信号</div><div class="metric-number">{len(lc_data)}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><div class="metric-label">电力压力</div><div class="metric-number">{len(power_data)}</div></div>', unsafe_allow_html=True)

# 下方面板说明
st.markdown('<div class="panel"><div class="panel-title">系统说明</div><p>该仪表盘监测数据中心基础设施资产是否存在技术性减值风险。</p></div>', unsafe_allow_html=True)
