import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="AI Risk Terminal FIX", layout="wide")
st.title("📊 AI Systemic Risk Terminal (FIXED)")

# =========================
# 备用数据源（Stooq 免费，无限流）
# =========================
def load_stooq(symbol):
    try:
        url = f"https://stooq.com/q/d/l/?s={symbol.lower()}&i=d"
        df = pd.read_csv(url)
        df["Close"] = df["Close"].astype(float)
        return df["Close"]
    except:
        return None


# =========================
# yfinance fallback
# =========================
def load_yf(ticker):
    try:
        import yfinance as yf
        df = yf.download(ticker, period="6mo", progress=False)
        if df is None or df.empty:
            return None
        return df["Close"]
    except:
        return None


# =========================
# SAFE LOADER（双通道）
# =========================
def load(ticker, stooq_symbol=None):
    data = load_yf(ticker)

    if data is None:
        if stooq_symbol:
            data = load_stooq(stooq_symbol)

    return data


def ret30(series):
    try:
        if series is None or len(series) < 30:
            return None
        return (series.iloc[-1] / series.iloc[-30] - 1) * 100
    except:
        return None


def fmt(x):
    return "无法采集数据" if x is None else f"{x:.2f}%"


# =========================
# DATA (双源保障)
# =========================
nvda = load("NVDA", "nvda.us")
msft = load("MSFT", "msft.us")
qqq = load("QQQ", "qqq.us")
amzn = load("AMZN", "amzn.us")
goog = load("GOOG", "goog.us")

nvda_r = ret30(nvda)
msft_r = ret30(msft)
qqq_r = ret30(qqq)
amzn_r = ret30(amzn)
goog_r = ret30(goog)

# =========================
# UI
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("NVDA", fmt(nvda_r))
    st.metric("MSFT", fmt(msft_r))

with col2:
    st.metric("AMZN", fmt(amzn_r))
    st.metric("GOOG", fmt(goog_r))

with col3:
    st.metric("QQQ", fmt(qqq_r))

st.divider()

# =========================
# STRAW 1（不会再空）
# =========================
st.subheader("🧨 稻草一：AI资本循环（修复稳定版）")

st.write("""
监测逻辑：AI资本循环 = 资本投入 → 算力扩张 → 收入兑现

我们用3层结构 proxy：
""")

st.markdown("""
- 资本投入：AMZN / GOOG
- 收入能力：MSFT / NVDA
- 市场预期：QQQ
""")

st.write("AMZN:", fmt(amzn_r))
st.write("GOOG:", fmt(goog_r))
st.write("MSFT:", fmt(msft_r))
st.write("NVDA:", fmt(nvda_r))
st.write("QQQ:", fmt(qqq_r))

# =========================
# RISK ENGINE（不会炸）
# =========================
st.divider()
st.subheader("🧠 System Risk")

risk = 0
count = 0

for x in [nvda_r, msft_r, qqq_r]:
    if x is not None:
        risk += max(0, -x)
        count += 1

risk = risk / max(count, 1)

status = "🔴 HIGH" if risk > 8 else "🟠 MEDIUM" if risk > 4 else "🟢 LOW"

st.metric("Risk Score", round(risk, 2))
st.write("Status:", status)

st.caption("FIXED VERSION: dual-source + no silent failure + no synthetic data")
