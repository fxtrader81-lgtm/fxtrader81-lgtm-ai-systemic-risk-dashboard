import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

# =========================
# UI
# =========================
st.set_page_config(page_title="AI Systemic Risk Terminal", layout="wide")
st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v1)")

st.caption("No synthetic data. Only real market signals or explicit missing data.")

# =========================
# Safe utils
# =========================
def safe_float(x):
    try:
        if isinstance(x, pd.Series):
            x = x.dropna()
            if len(x) == 0:
                return None
            return float(x.iloc[-1])
        if pd.isna(x):
            return None
        return float(x)
    except:
        return None


def load(ticker):
    try:
        time.sleep(0.4)
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        return df
    except:
        return None


def return_30d(df):
    if df is None or df.empty:
        return None
    try:
        c = df["Close"].dropna()
        if len(c) < 30:
            return None
        return (float(c.iloc[-1]) / float(c.iloc[-30]) - 1) * 100
    except:
        return None


def risk(score):
    if score is None:
        return "⚪ 无数据"
    if score > 15:
        return "🔴 高风险"
    if score > 8:
        return "🟠 中风险"
    return "🟢 稳定"

# =========================
# DATA LAYER
# =========================

nvda = load("NVDA")
msft = load("MSFT")
qqq = load("QQQ")
tsla = load("TSLA")
dxy = load("DX-Y.NYB")   # 美元指数 proxy
tnx = load("^TNX")       # 10Y yield

nvda_r = return_30d(nvda)
msft_r = return_30d(msft)
qqq_r = return_30d(qqq)
tsla_r = return_30d(tsla)
dxy_r = return_30d(dxy)
tnx_r = return_30d(tnx)

# =========================
# DASHBOARD
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("💻 AI 核心资产（稻草1）")
    st.write("NVDA:", nvda_r, risk(-nvda_r if nvda_r else None))
    st.write("MSFT:", msft_r, risk(-msft_r if msft_r else None))
    st.write("QQQ:", qqq_r, risk(-qqq_r if qqq_r else None))

with col2:
    st.subheader("💰 流动性与美元（稻草5）")
    st.write("DXY:", dxy_r)
    st.write("10Y Yield:", tnx_r)

with col3:
    st.subheader("⚡ AI 高波动资产")
    st.write("TSLA:", tsla_r, risk(-tsla_r if tsla_r else None))

# =========================
# RISK ENGINE
# =========================

st.divider()
st.subheader("🧠 Systemic Risk Engine")

risk_score = 0

# 稻草1：AI CapEx/泡沫 proxy（用 NVDA/MSFT/QQQ）
if nvda_r is not None:
    risk_score += max(0, -nvda_r) * 0.4

if msft_r is not None:
    risk_score += max(0, -msft_r) * 0.3

# 稻草2：市场风险
if qqq_r is not None:
    risk_score += max(0, -qqq_r) * 0.3

# 稻草3：高波动
if tsla_r is not None:
    risk_score += max(0, -tsla_r) * 0.2

# 稻草5：利率压力（简单 proxy）
if tnx_r is not None:
    risk_score += max(0, tnx_r) * 0.1

status = (
    "🔴 SYSTEMIC STRESS" if risk_score > 15 else
    "🟠 ELEVATED RISK" if risk_score > 8 else
    "🟢 STABLE"
)

st.metric("Risk Score", round(risk_score, 2))
st.write("Status:", status)

# =========================
# FIVE STRAWS PANEL
# =========================

st.divider()
st.subheader("🧨 Five Straw Breakdown (AI Bubble Fragility Map)")

st.markdown("""
### 稻草1：AI 收入 vs CapEx 压力（用 NVDA / MSFT / QQQ proxy）
如果 AI 相关资产持续下跌 → 说明资本对 AI 盈利能力开始怀疑

### 稻草2：开源模型冲击（目前无法直接数据化）
观察 proxy：云计算公司（MSFT / AMZN）

### 稻草3：数据中心资产风险（未直接可测）
观察 NVDA / QQQ / utilities proxy

### 稻草4：能源瓶颈
用 10Y yield + DXY proxy 观察资金成本与能源压力

### 稻草5：美元流动性
DXY + 利率上行 = 全球美元回收 → AI 杠杆收缩
""")

# =========================
# FOOTER
# =========================

st.caption("v1: proxy-based systemic risk model | upgrade path: FRED + VIX + energy markets + liquidity spreads")
