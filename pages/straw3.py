import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# 初始配置与常量定义 (修正 NameError 的关键)
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
# 页面配置
# =========================================================
st.set_page_config(page_title="稻草三：数据中心资产减值", layout="wide")

# (此处保留你原有的 CSS 代码块，保持风格一致)
st.markdown("""
<style>
.stApp { background-color: #050816 !important; }
.main-title { font-size: 32px; font-weight: 800; color: #ffffff; }
.metric-card { background-color: #0b1120; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 20px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# API 数据获取函数 (保持原样)
# =========================================================
YF_HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_yf_summary(ticker):
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,defaultKeyStatistics,summaryDetail,price"
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=5)
        if r.status_code != 200: return None
        result = r.json().get("quoteSummary", {}).get("result", [])
        return result[0] if result else None
    except: return None

def fetch_yf_chart(ticker):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1wk&range=1y"
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=5)
        meta = r.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
        return {
            "current_price": meta.get("regularMarketPrice", 0),
            "week52_high": meta.get("fiftyTwoWeekHigh", 0),
            "week52_low": meta.get("fiftyTwoWeekLow", 0)
        }
    except: return None

def safe_raw(d, key, default=0):
    try:
        val = d.get(key, {})
        return float(val.get("raw", default)) if isinstance(val, dict) else float(val)
    except: return default

# =========================================================
# 评分逻辑函数 (保持原样)
# =========================================================
def score_aof(aof):
    if aof < 1.5: return 0, "green", "↗", "SAFE"
    elif aof < 2.5: return round((aof - 1.5) / 1.0 * 33), "yellow", "→", "WATCH"
    elif aof < 3.5: return round(33 + (aof - 2.5) / 1.0 * 34), "orange", "↘", "WARNING"
    else: return min(100, round(67 + (aof - 3.5) / 0.5 * 33)), "red", "↓", "CRITICAL"

# ... (其余 get_reit_data, score_reit, score_liquid, score_power 等函数保持原逻辑)
# 为节省篇幅，此处省略函数定义，请直接使用你原来的函数体

# =========================================================
# 主程序运行逻辑
# =========================================================

# 1. 顶部标题
st.markdown(f"""
<div style="display:flex; justify-content:space-between;">
  <div><div class="main-title">🏗️ 稻草三：数据中心资产技术性减值</div></div>
  <div><span class="timestamp-text">🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>
</div>
""", unsafe_allow_html=True)

# 2. 数据获取
with st.spinner("正在拉取市场数据..."):
    # 补充调用你的数据函数
    reit_data = get_reit_data() # 请确保你代码中保留了此函数
    lc_data = get_liquid_cooling_data()
    power_data = get_power_data()

# 3. 计算评分
aof_s, aof_color, aof_arrow, aof_status = score_aof(AOF)
# (继续后续评分逻辑...)

# 4. 渲染界面
# (继续后续代码...)
