"""
straw6.py — 稻草六 · 美元国债市场预警
股市 × 债市联动分析

数据源:
  - FRED API  : 美国国债收益率 (DGS10, DGS30)
  - FMP API   : 美股指数 (S&P500, NASDAQ, Dow Jones)
  - yfinance  : A股指数 (上证 000001.SS, 深证 399001.SZ)
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz
import yfinance as yf

# =========================================================
# 页面配置
# =========================================================
st.set_page_config(
    page_title="稻草六 · 美元国债市场预警",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# API Keys
# =========================================================
FRED_API_KEY = "9d4d8c74237a32ec198773ca5eb0f4e3"
FMP_API_KEY  = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"

# =========================================================
# 太平洋时间
# =========================================================
def now_pt() -> str:
    tz = pytz.timezone("America/Los_Angeles")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M PT")

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #050816 !important;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.stApp { background-color: #050816 !important; }
section[data-testid="stMain"] > div { background-color: #050816 !important; }
.block-container {
    padding-top: 1.4rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1600px;
    background-color: #050816 !important;
}

[data-testid="stSidebar"] {
    background-color: #0b1120 !important;
    border-right: 1px solid rgba(255,255,255,0.07);
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 18px;
}
.page-title {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
    margin: 0 0 4px 0;
}
.page-sub {
    font-size: 13px;
    color: #94a3b8;
    margin: 0;
}
.ts-label {
    font-size: 13px;
    font-weight: 600;
    color: #cbd5e1;
    text-align: right;
    display: block;
    margin-bottom: 4px;
}
.symbol-badge {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 3px 14px;
    font-size: 12px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 1px;
}

.alert-top-bar {
    background: linear-gradient(135deg, #0b1120 0%, #0d1829 100%);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 32px;
}
.atb-score-wrap { text-align: center; min-width: 100px; }
.atb-score {
    font-size: 64px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -3px;
}
.atb-score-label {
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 4px;
}
.atb-divider {
    width: 1px;
    height: 70px;
    background: rgba(255,255,255,0.08);
    flex-shrink: 0;
}
.atb-state-wrap { min-width: 140px; }
.atb-state-label {
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.atb-state {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
.atb-bar-wrap {
    margin-top: 10px;
    width: 160px;
    height: 5px;
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
}
.atb-bar-fill { height: 5px; border-radius: 3px; }
.atb-conclusion { flex: 1; }
.atb-con-title {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 7px;
}
.atb-con-body {
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.75;
}

.kpi-card {
    background: #0b1120;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 18px 20px 16px;
}
.kpi-label {
    font-size: 13px;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 8px;
    letter-spacing: 0.3px;
}
.kpi-value {
    font-size: 30px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1px;
}
.kpi-sub {
    font-size: 12px;
    color: #64748b;
    margin-top: 6px;
    line-height: 1.5;
}

.ind-card {
    background: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 18px 20px;
    height: 200px;
}
.ind-label {
    font-size: 12px;
    font-weight: 700;
    color: #cbd5e1;
    margin-bottom: 10px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.ind-value {
    font-size: 32px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1.2px;
}
.ind-unit {
    font-size: 13px;
    color: #64748b;
    margin-left: 4px;
}
.ind-badge {
    display: inline-block;
    border-radius: 5px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    margin-top: 8px;
}
.ind-thresh {
    font-size: 11px;
    color: #475569;
    margin-top: 8px;
    line-height: 1.8;
}

.conc-box {
    border-radius: 14px;
    padding: 18px 22px;
    display: flex;
    gap: 14px;
    align-items: flex-start;
    margin: 14px 0;
}
.conc-icon { font-size: 36px; flex-shrink: 0; line-height: 1; }
.conc-title { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
.conc-body  { font-size: 13px; color: #cbd5e1; line-height: 1.75; }

.panel {
    background: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
}
.panel-title {
    font-size: 15px;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 16px;
}

.hr-row {
    display: flex;
    gap: 8px;
    padding: 10px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    align-items: center;
}
.hr-row:last-child { border-bottom: none; }
.hr-date  { font-size: 12px; font-weight: 700; color: #94a3b8; width: 72px; flex-shrink: 0; }
.hr-event { font-size: 12px; color: #e2e8f0; flex: 1; }
.hr-y10   { font-size: 12px; font-weight: 700; color: #5CB85C; width: 52px; text-align: right; }
.hr-drop  { font-size: 12px; font-weight: 700; color: #ef4444; width: 52px; text-align: right; }

.ctrl-label {
    font-size: 13px;
    font-weight: 700;
    color: #cbd5e1;
    margin-bottom: 6px;
}

.c-green  { color: #22c55e; }
.c-red    { color: #ef4444; }
.c-yellow { color: #fbbf24; }
.c-orange { color: #f97316; }
.c-blue   { color: #4F8EF7; }
.c-gray   { color: #94a3b8; }

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
.modebar  { display: none !important; }

.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    gap: 4px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px 8px 0 0;
    padding: 9px 26px;
    color: #64748b;
    font-weight: 700;
    font-size: 14px;
    border: 1px solid transparent;
    border-bottom: none;
}
.stTabs [aria-selected="true"] {
    background: #0b1120 !important;
    color: #60a5fa !important;
    border-color: rgba(255,255,255,0.08) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent;
    padding-top: 22px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 股灾事件
# =========================================================
CRASH_EVENTS = [
    {"date": "1997-10-01", "label": "Asian Crisis",    "desc": "亚洲金融危机·港元保卫战",      "severity": "WARNING"},
    {"date": "1998-08-01", "label": "LTCM/Russia",     "desc": "俄罗斯违约·LTCM崩盘",           "severity": "WARNING"},
    {"date": "2000-03-01", "label": "Dot-com Peak",    "desc": "科网泡沫顶点·纳指跌78%",       "severity": "CRITICAL"},
    {"date": "2001-09-01", "label": "9/11",            "desc": "911恐袭·市场关闭4天",           "severity": "CRITICAL"},
    {"date": "2002-10-01", "label": "Tech Bottom",     "desc": "科网熊市底部",                  "severity": "WARNING"},
    {"date": "2007-08-01", "label": "Subprime",        "desc": "次贷危机苗头·贝尔斯登基金崩盘", "severity": "WARNING"},
    {"date": "2008-09-01", "label": "Lehman",          "desc": "雷曼破产·金融海啸",              "severity": "CRITICAL"},
    {"date": "2010-05-01", "label": "Flash Crash",     "desc": "闪崩·道指单日跌近1000点",       "severity": "WATCH"},
    {"date": "2011-08-01", "label": "US Downgrade",    "desc": "美国主权评级下调·欧债危机",     "severity": "WARNING"},
    {"date": "2015-08-01", "label": "China Crash",     "desc": "A股股灾·人民币贬值",            "severity": "WARNING"},
    {"date": "2018-12-01", "label": "Fed Panic",       "desc": "美联储加息恐慌·圣诞崩盘",       "severity": "WARNING"},
    {"date": "2020-03-01", "label": "COVID",           "desc": "新冠疫情·史上最快熊市",         "severity": "CRITICAL"},
    {"date": "2022-01-01", "label": "Rate Hike",       "desc": "加息周期启动·纳指跌33%",        "severity": "CRITICAL"},
    {"date": "2023-03-01", "label": "SVB Crisis",      "desc": "硅谷银行倒闭·银行业危机",       "severity": "WARNING"},
]

SEV_COLOR = {"WATCH": "#fbbf24", "WARNING": "#f97316", "CRITICAL": "#ef4444"}

# =========================================================
# 数据获取
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred(series_id: str, start: str = "1994-01-01") -> pd.Series:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = dict(
        series_id=series_id, api_key=FRED_API_KEY,
        file_type="json", observation_start=start,
        frequency="m", aggregation_method="eop",
    )
    try:
        obs = requests.get(url, params=params, timeout=15).json().get("observations", [])
        s = pd.Series({o["date"]: float(o["value"]) for o in obs if o["value"] != "."}, name=series_id)
        s.index = pd.to_datetime(s.index)
        return s
    except Exception as e:
        st.warning(f"FRED {series_id}: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fmp(symbol: str, start: str = "1994-01-01") -> pd.Series:
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
    try:
        hist = requests.get(url, params={"apikey": FMP_API_KEY, "from": start}, timeout=20).json().get("historical", [])
        if not hist:
            return pd.Series(dtype=float)
        df = pd.DataFrame(hist)[["date", "close"]]
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date").sort_index()["close"].resample("ME").last()
        s.name = symbol
        return s
    except Exception as e:
        st.warning(f"FMP {symbol}: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_yf(ticker: str, start: str = "1994-01-01") -> pd.Series:
    try:
        df = yf.download(ticker, start=start, interval="1mo", progress=False)
        if df.empty:
            return pd.Series(dtype=float)
        s = df["Close"].squeeze()
        s.index = pd.to_datetime(s.index).to_period("M").to_timestamp("M")
        s.name = ticker
        return s.dropna()
    except Exception as e:
        st.warning(f"yfinance {ticker}: {e}")
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600, show_spinner=False)
def load_all():
    return (
        fetch_fred("DGS10"),
        fetch_fred("DGS30"),
        fetch_fmp("^GSPC"),
        fetch_fmp("^IXIC"),
        fetch_fmp("^DJI"),
        fetch_yf("000001.SS"),
        fetch_yf("399001.SZ"),
    )

# =========================================================
# 预警计算与逻辑渲染
# =========================================================

def render_alert_logic():
    st.markdown("""
    <div class="panel">
      <div class="panel-title">⚙️ 预警逻辑与阈值推导（1994–今历史统计）</div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:22px;">
        <div>
          <div style="font-size:13px;font-weight:700;color:#fbbf24;margin-bottom:8px;">
            🚀 指标②：3M收益率变化速率（权重 ×0.40，最关键）
          </div>
          <div style="font-size:13px;color:#94a3b8;line-height:2;">
            <b style="color:#22c55e;">P75 = +50bps</b> → WATCH：2021Q1（+82bps），短暂调整<br>
            <b style="color:#f97316;">P90 = +100bps</b> → WARNING：2013 Taper（+130bps），-6%<br>
            <b style="color:#ef4444;">P95 = +150bps</b> → CRITICAL：2022（+230bps），-25%
          </div>
        </div>
        <div>
          <div style="font-size:13px;font-weight:700;color:#5CB85C;margin-bottom:8px;">
            📐 指标③：期限利差 30Y-10Y（权重 ×0.25）
          </div>
          <div style="font-size:13px;color:#94a3b8;line-height:2;">
            <b style="color:#ef4444;">倒挂（&lt;0）</b>：历史每次持续倒挂均先于衰退6–18个月<br>
            <b style="color:#f97316;">2006-07</b>：倒挂持续8个月 → 2008金融危机<br>
            <b style="color:#fbbf24;">结构平坦化</b>：需关注长期通胀预期变化
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# 程序入口
if __name__ == "__main__":
    st.markdown('<div class="page-header"><div class="page-title">稻草六 · 美元国债市场预警</div></div>', unsafe_allow_html=True)
    st.write(f"当前系统时间: {now_pt()}")
    render_alert_logic()
