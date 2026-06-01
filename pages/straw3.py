import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

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
.main-title { font-size: 32px; font-weight: 800; color: #ffffff; margin: 0 0 6px 0; letter-spacing: -0.5px; }
.sub-title { font-size: 16px !important; color: #cbd5e1 !important; margin: 0; }
.timestamp-text { font-size: 13px; color: #475569; margin-bottom: 8px; display: block; }
.symbol-badge {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 3px 16px;
    font-size: 13px; font-weight: 600; color: #94a3b8; letter-spacing: 1px;
}
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
.metric-card {
    background-color: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 20px 22px 18px;
    height: 168px;
}
.metric-label { color: #ffffff; font-size: 18px; font-weight: 600; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.4px; }
.metric-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 14px; }
.metric-number { font-size: 38px; font-weight: 800; line-height: 1; letter-spacing: -1.5px; }
.metric-arrow { font-size: 20px; font-weight: 700; }
.metric-desc { color: #cbd5e1 !important; font-size: 15px !important; line-height: 1.6; }
.green { color: #22c55e; } .red { color: #ef4444; } .yellow { color: #fbbf24; } .orange { color: #f97316; }
.alert-box, .alert-box-red, .alert-box-green { margin: 18px 0; border-radius: 14px; padding: 22px 26px; display: flex; gap: 18px; align-items: flex-start; }
.alert-box { background: #120e00; border: 1px solid rgba(251,191,36,0.18); }
.alert-box-red { background: #120000; border: 1px solid rgba(239,68,68,0.25); }
.alert-box-green { background: #001208; border: 1px solid rgba(34,197,94,0.2); }
.alert-icon { font-size: 44px; flex-shrink: 0; line-height: 1; }
.alert-title { font-size: 23px !important; font-weight: 700; margin-bottom: 10px; }
.alert-text { font-size: 17px !important; color: #cbd5e1 !important; line-height: 1.75; }
.panel { background-color: #0b1120; border-radius: 14px; padding: 22px; border: 1px solid rgba(255,255,255,0.07); }
.panel-title { font-size: 20px !important; font-weight: 700; margin-bottom: 20px; color: #e2e8f0; }
.logic-step { display: flex; gap: 12px; margin-bottom: 13px; align-items: flex-start; }
.step-num { width: 22px; height: 22px; min-width: 22px; border-radius: 50%; background: #1e3a5f; color: #60a5fa; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-top: 2px; }
.step-text { font-size: 16px !important; color: #cbd5e1 !important; line-height: 1.6; }
.threshold-block { margin-left: 34px; margin-top: 8px; }
.threshold-row { display: flex; align-items: center; gap: 8px; padding: 7px 12px; border-radius: 7px; margin-bottom: 6px; background: rgba(255,255,255,0.02); }
.t-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.t-label { font-size: 15px !important; color: #cbd5e1 !important; flex: 1; }
.t-status { font-size: 15px !important; font-weight: 600; }
.source-tag, .source-tag-warn { display: inline-block; border-radius: 6px; padding: 2px 10px; font-size: 12px; margin-left: 8px; }
.source-tag { background: rgba(96,165,250,0.1); border: 1px solid rgba(96,165,250,0.2); color: #60a5fa; }
.source-tag-warn { background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.25); color: #fbbf24; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 常量与数据逻辑
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

def fetch_yf_summary(ticker):
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,price"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            data = r.json().get("quoteSummary", {}).get("result", [{}])[0]
            merged = {}
            for m in data.values():
                if isinstance(m, dict): merged.update(m)
            return merged
    except: return None
    return None

def fetch_yf_chart(ticker):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1wk"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            meta = r.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
            return {"current_price": meta.get("regularMarketPrice", 0), "week52_high": meta.get("fiftyTwoWeekHigh", 0), "week52_low": meta.get("fiftyTwoWeekLow", 0)}
    except: return None
    return None

def safe_raw(d, key, default=0):
    try: return float(d.get(key, {}).get("raw", default)) if isinstance(d.get(key), dict) else default
    except: return default

# =========================================================
# 渲染页面
# =========================================================
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 20px;">
  <div>
    <div class="main-title">🏗️ 稻草三：数据中心资产技术性减值</div>
    <div class="sub-title">核心检测维度：AI算力迭代速度与基础设施折旧周期</div>
  </div>
  <div style="text-align:right;">
    <span class="timestamp-text">🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    <span class="symbol-badge">DCOI 指数</span>
  </div>
</div>
""", unsafe_allow_html=True)

# 模拟数据计算
aof_s = min(100, round((AOF - 1.0) * 30))
dcoi = 42 # 演示基准
state_color = "yellow"
state = "WATCH"

st.markdown(f"""
<div class="osci-card">
  <div class="osci-left">
    <div class="osci-label">DCOI SCORE</div>
    <div class="osci-score {state_color}">{dcoi}</div>
    <div class="osci-desc">当前状态: 观察区间 (Upgrade Stress)</div>
  </div>
  <div class="osci-right">
    <div class="osci-state {state_color}">{state}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# 图表部分
lp, rp = st.columns([1, 1.5])
with lp:
    st.markdown('<div class="panel"><div class="panel-title">⚙️ 检测逻辑</div><div class="logic-step"><div class="step-num">1</div><div class="step-text">AOF 功率压力计算中...</div></div></div>', unsafe_allow_html=True)

with rp:
    st.markdown('<div class="panel"><div class="panel-title">⚡ GPU 功率密度跃迁</div>', unsafe_allow_html=True)
    fig = go.Figure(data=[go.Bar(x=[g["gen"] for g in GPU_GENERATIONS], y=[(g["rack_kw_min"]+g["rack_kw_max"])/2 for g in GPU_GENERATIONS])])
    fig.update_layout(height=250, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#64748b"))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
