import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# 1. 核心配置与参数
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
# 2. 数据获取函数定义
# =========================================================
def fetch_yf_summary(ticker):
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,defaultKeyStatistics,summaryDetail,price"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code != 200: return None
        result = r.json().get("quoteSummary", {}).get("result", [])
        return result[0] if result else None
    except: return None

def fetch_yf_chart(ticker):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1wk&range=1y"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        meta = r.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
        return {"current_price": meta.get("regularMarketPrice", 0), "week52_high": meta.get("fiftyTwoWeekHigh", 0), "week52_low": meta.get("fiftyTwoWeekLow", 0)}
    except: return None

def safe_raw(d, key, default=0):
    try:
        v = d.get(key, {})
        return float(v.get("raw", default)) if isinstance(v, dict) else float(v)
    except: return default

@st.cache_data(ttl=3600)
def get_reit_data():
    results = {}
    for ticker in ["EQIX", "DLR"]:
        summary, chart = fetch_yf_summary(ticker), fetch_yf_chart(ticker)
        if not summary and not chart: continue
        results[ticker] = {
            "rev_growth": safe_raw(summary or {}, "revenueGrowth") * 100,
            "from_high_pct": ((chart.get("week52_high", 0) - chart.get("current_price", 0)) / chart.get("week52_high", 1)) * 100
        }
    return results

@st.cache_data(ttl=3600)
def get_liquid_cooling_data():
    results = {}
    for ticker in ["VRT", "SMCI"]:
        summary, chart = fetch_yf_summary(ticker), fetch_yf_chart(ticker)
        if summary: results[ticker] = {"rev_growth": safe_raw(summary or {}, "revenueGrowth") * 100, "price_pos_pct": 50}
    return results

@st.cache_data(ttl=3600)
def get_power_data():
    results = {}
    for ticker in ["NEE", "SO"]:
        summary = fetch_yf_summary(ticker)
        if summary: results[ticker] = {"rev_growth": safe_raw(summary or {}, "revenueGrowth") * 100, "price_pos_pct": 50}
    return results

# =========================================================
# 3. 评分函数定义
# =========================================================
def score_aof(aof):
    if aof < 1.5: return 0, "green", "↗", "SAFE"
    elif aof < 2.5: return round((aof - 1.5) / 1.0 * 33), "yellow", "→", "WATCH"
    else: return 80, "red", "↓", "CRITICAL"

# =========================================================
# 4. 主程序 (防止逻辑错位)
# =========================================================
st.set_page_config(page_title="稻草三：数据中心资产减值", layout="wide")

st.title("🏗️ 稻草三：数据中心资产技术性减值")

with st.spinner("正在拉取实时数据..."):
    reit_data = get_reit_data()
    lc_data = get_liquid_cooling_data()
    power_data = get_power_data()

aof_s, color, arrow, status = score_aof(AOF)

st.metric("AOF 淘汰系数", f"{AOF:.2f}x", delta=status)
st.write(f"当前 REIT 样本数据: {list(reit_data.keys()) if reit_data else '暂无数据'}")
