import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Compute-Dollar Risk Terminal", layout="wide")

st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v2)")
st.caption("No synthetic data. Only real market data or explicit missing signals.")


# =========================
# 工具层：安全数据获取
# =========================

@st.cache_data(ttl=3600)
def fetch_yf(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if data is None or data.empty:
            return None
        return data
    except Exception:
        return None


def safe_last(df):
    try:
        if df is None or df.empty:
            return None
        val = df["Close"].iloc[-1]
        return float(val)
    except:
        return None


def safe_ret30(df):
    try:
        if df is None or df.empty:
            return None
        if len(df) < 30:
            return None
        last = float(df["Close"].iloc[-1])
        past = float(df["Close"].iloc[-30])
        if past == 0:
            return None
        return (last / past - 1) * 100
    except:
        return None


def fmt(x):
    if x is None:
        return "无法采集数据"
    return f"{x:.2f}%"


def risk_label(x, yellow, red):
    if x is None:
        return "⚪ 无数据"
    if x >= red:
        return "🔴 CRITICAL"
    elif x >= yellow:
        return "🟠 WARNING"
    else:
        return "🟢 NORMAL"


# =========================
# 数据层
# =========================

nvda = fetch_yf("NVDA")
msft = fetch_yf("MSFT")
qqq  = fetch_yf("QQQ")
amzn = fetch_yf("AMZN")
goog = fetch_yf("GOOGL")
tsla = fetch_yf("TSLA")
dxy  = fetch_yf("DX-Y.NYB")
t10y = fetch_yf("^TNX")


# =========================
# 稻草一：AI资本循环
# =========================

nvda_r = safe_ret30(nvda)
msft_r = safe_ret30(msft)
qqq_r  = safe_ret30(qqq)

capex_proxy = safe_ret30(amzn)
capex_proxy2 = safe_ret30(goog)

st.subheader("💻 稻草1：AI资本循环是否过热")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("NVDA (Demand Proxy)", fmt(nvda_r), risk_label(nvda_r, 5, 15))

with col2:
    st.metric("MSFT (AI Monetization)", fmt(msft_r), risk_label(msft_r, 5, 12))

with col3:
    st.metric("QQQ (Valuation Pressure)", fmt(qqq_r), risk_label(qqq_r, 3, 10))


# =========================
# 稻草2：开源冲击 Proxy
# =========================

st.subheader("🧠 稻草2：开源模型冲击（Proxy）")

with st.container():
    st.metric("GOOGL (Open AI Competition Proxy)", fmt(safe_ret30(goog)))
    st.metric("MSFT Cloud Proxy", fmt(msft_r))


# =========================
# 稻草3：数据中心 / 算力资产风险
# =========================

st.subheader("🏗 稻草3：数据中心资产风险")

with st.container():
    st.metric("NVDA Hardware Cycle", fmt(nvda_r))
    st.metric("AMZN Infra CapEx Proxy", fmt(capex_proxy))


# =========================
# 稻草4：能源瓶颈
# =========================

st.subheader("⚡ 稻草4：能源约束")

with st.container():
    st.metric("10Y Yield (^TNX)", fmt(safe_last(t10y)))
    st.metric("Energy Stress Proxy (DXY)", fmt(safe_last(dxy)))


# =========================
# 稻草5：美元流动性
# =========================

st.subheader("💰 稻草5：美元流动性")

with st.container():
    st.metric("DXY", fmt(safe_last(dxy)))
    st.metric("Rate Shock (^TNX)", fmt(safe_last(t10y)))


# =========================
# System Risk Engine
# =========================

risk = 0
count = 0

for x in [nvda_r, msft_r, qqq_r]:
    if x is not None:
        risk += max(0, -x)
        count += 1

risk_score = risk / max(count, 1)

st.subheader("🧠 System Risk Engine")

if risk_score is None or pd.isna(risk_score):
    st.write("无法计算风险")
else:
    st.metric("Risk Score", f"{risk_score:.2f}")

    if risk_score < 5:
        st.success("🟢 STABLE")
    elif risk_score < 10:
        st.warning("🟠 ELEVATED")
    else:
        st.error("🔴 CRITICAL")


# =========================
# 说明
# =========================

st.caption("""
所有数据均来自公开市场API（yfinance / FRED proxy）。
数据缺失时显示“无法采集数据”，不使用任何虚拟数据。
""")
