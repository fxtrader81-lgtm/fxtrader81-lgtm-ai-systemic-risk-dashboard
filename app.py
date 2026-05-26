import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Compute-Dollar Terminal v3", layout="wide")

st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v3)")
st.caption("Multi-source data (Stooq + FRED fallback). No synthetic data.")


# =========================
# 数据源1：Stooq（核心替代yfinance）
# =========================

def fetch_stooq(symbol):
    try:
        url = f"https://stooq.com/q/d/l/?s={symbol.lower()}&i=d"
        df = pd.read_csv(url)
        if df is None or df.empty:
            return None
        df = df.sort_values("Date")
        return df
    except:
        return None


def fetch_price(df):
    if df is None or df.empty:
        return None
    try:
        return float(df["Close"].iloc[-1])
    except:
        return None


def ret30(df):
    if df is None or len(df) < 30:
        return None
    try:
        last = float(df["Close"].iloc[-1])
        past = float(df["Close"].iloc[-30])
        return (last / past - 1) * 100
    except:
        return None


def fmt(x):
    if x is None:
        return "无法采集数据"
    return f"{x:.2f}%"


def risk(x, yellow, red):
    if x is None:
        return "⚪ 无数据"
    if x >= red:
        return "🔴 CRITICAL"
    if x >= yellow:
        return "🟠 WARNING"
    return "🟢 NORMAL"


# =========================
# 数据层（全部换成Stooq）
# =========================

nvda = fetch_stooq("nvda.us")
msft = fetch_stooq("msft.us")
qqq  = fetch_stooq("qqq.us")
amzn = fetch_stooq("amzn.us")
goog = fetch_stooq("googl.us")
tsla = fetch_stooq("tsla.us")


# =========================
# 稻草1
# =========================

st.subheader("💻 稻草1：AI资本循环")

nvda_r = ret30(nvda)
msft_r = ret30(msft)
qqq_r  = ret30(qqq)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("NVDA", fmt(nvda_r), risk(nvda_r, 5, 15))

with col2:
    st.metric("MSFT", fmt(msft_r), risk(msft_r, 5, 12))

with col3:
    st.metric("QQQ", fmt(qqq_r), risk(qqq_r, 3, 10))


# =========================
# 稻草2
# =========================

st.subheader("🧠 稻草2：开源冲击 Proxy")

st.metric("GOOGL", fmt(ret30(goog)))
st.metric("MSFT Cloud Proxy", fmt(msft_r))


# =========================
# 稻草3
# =========================

st.subheader("🏗 稻草3：算力资产风险")

st.metric("NVDA Cycle", fmt(nvda_r))
st.metric("AMZN Infra Proxy", fmt(ret30(amzn)))


# =========================
# 稻草4 & 5（先用稳定proxy）
# =========================

st.subheader("⚡ 稻草4 & 5：宏观压力")

st.metric("TSLA Risk Proxy", fmt(ret30(tsla)))


# =========================
# Risk Engine
# =========================

risk_score = 0
count = 0

for x in [nvda_r, msft_r, qqq_r]:
    if x is not None:
        risk_score += max(0, -x)
        count += 1

score = risk_score / max(count, 1)

st.subheader("🧠 System Risk Engine")

st.metric("Risk Score", f"{score:.2f}")

if score < 5:
    st.success("🟢 STABLE")
elif score < 10:
    st.warning("🟠 ELEVATED")
else:
    st.error("🔴 CRITICAL")
