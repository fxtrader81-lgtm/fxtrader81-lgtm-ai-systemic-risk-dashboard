import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from fredapi import Fred
import time

# =========================
# Config
# =========================

st.set_page_config(page_title="AI Compute-Dollar Risk Terminal", layout="wide")

FRED_KEY = st.secrets.get("fred_api_key", None)
fred = Fred(api_key=FRED_KEY) if FRED_KEY else None

# =========================
# Safe utilities
# =========================

def safe_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, pd.Series):
            x = x.iloc[-1]
        if pd.isna(x):
            return None
        return float(x)
    except:
        return None


def pct_change(last, past):
    if last is None or past is None or past == 0:
        return None
    return (last / past - 1) * 100


def safe_download(ticker, period="6mo"):
    try:
        data = yf.download(ticker, period=period, interval="1d", progress=False, threads=False)
        if data is None or data.empty:
            return None
        return data
    except:
        return None


def last_return(df):
    if df is None or df.empty:
        return None
    try:
        close = df["Close"].dropna()
        if len(close) < 30:
            return None
        return pct_change(close.iloc[-1], close.iloc[-30])
    except:
        return None


# =========================
# Data layer
# =========================

@st.cache_data(ttl=3600)
def get_market_data():
    tickers = ["NVDA", "MSFT", "AMZN", "QQQ", "SPY", "VIXY", "DX-Y.NYB"]
    data = {}

    for t in tickers:
        df = safe_download(t)
        data[t] = df
        time.sleep(0.2)  # 防限流

    return data


@st.cache_data(ttl=3600)
def get_fred_data():
    if fred is None:
        return None

    try:
        return {
            "fedfunds": fred.get_series("FEDFUNDS"),
            "dgs10": fred.get_series("DGS10"),
            "m2": fred.get_series("M2SL"),
        }
    except:
        return None


# =========================
# Straw indicators (核心逻辑层)
# =========================

def straw1_ai_capex_risk(market):
    nvda = last_return(market.get("NVDA"))
    msft = last_return(market.get("MSFT"))
    amzn = last_return(market.get("AMZN"))
    qqq = last_return(market.get("QQQ"))

    if any(x is None for x in [nvda, msft, amzn, qqq]):
        return None

    capex_proxy = (msft + amzn) / 2
    revenue_proxy = nvda
    valuation = qqq

    return capex_proxy - revenue_proxy - 0.3 * valuation


def straw2_open_source_pressure(market):
    msft = last_return(market.get("MSFT"))
    qqq = last_return(market.get("QQQ"))
    if msft is None or qqq is None:
        return None
    return qqq - msft


def straw3_datacenter_risk(market):
    nvda = last_return(market.get("NVDA"))
    spy = last_return(market.get("SPY"))
    if nvda is None or spy is None:
        return None
    return nvda - spy


def straw4_energy_pressure(fred_data):
    if fred_data is None:
        return None

    try:
        y10 = fred_data["dgs10"].dropna().iloc[-1]
        fed = fred_data["fedfunds"].dropna().iloc[-1]
        return float(y10 - fed)
    except:
        return None


def straw5_liquidity_pressure(market):
    vix = last_return(market.get("VIXY"))
    dxy = last_return(market.get("DX-Y.NYB"))

    if vix is None or dxy is None:
        return None

    return vix + dxy


# =========================
# Risk engine
# =========================

def risk_score(values):
    clean = [v for v in values if v is not None]
    if len(clean) == 0:
        return 0

    score = 0
    for v in clean:
        score += max(0, v)

    return round(score, 2)


def risk_label(score):
    if score < 5:
        return "🟢 STABLE"
    elif score < 15:
        return "🟠 WARNING"
    else:
        return "🔴 CRITICAL"


# =========================
# UI
# =========================

st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v5)")
st.caption("No synthetic data. Only real market + macro proxies. Missing data shown explicitly.")

market = get_market_data()
fred_data = get_fred_data()

# =========================
# Compute straw values
# =========================

s1 = straw1_ai_capex_risk(market)
s2 = straw2_open_source_pressure(market)
s3 = straw3_datacenter_risk(market)
s4 = straw4_energy_pressure(fred_data)
s5 = straw5_liquidity_pressure(market)

score = risk_score([s1, s2, s3, s4, s5])
status = risk_label(score)

# =========================
# Display helper
# =========================

def fmt(x):
    return "无法采集数据" if x is None else f"{x:.2f}"


# =========================
# Dashboard
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("稻草1 AI资本循环", fmt(s1))
    st.metric("稻草2 开源压力", fmt(s2))

with col2:
    st.metric("稻草3 数据中心风险", fmt(s3))
    st.metric("稻草4 能源压力", fmt(s4))

with col3:
    st.metric("稻草5 流动性压力", fmt(s5))

st.divider()

st.metric("🧠 System Risk Score", score)
st.markdown(f"### {status}")

st.divider()

st.markdown("### 🧨 说明")
st.write("""
这个系统不再依赖单一股票，而是用“市场结构变化率”来表达：

- AI资本是否过热（CapEx vs Revenue）
- 开源是否压制估值
- 数据中心是否过度扩张
- 能源是否约束金融系统
- 美元是否收紧流动性

所有指标均为 proxy，不使用虚拟数据。
""")
