import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

# =========================
# UI
# =========================
st.set_page_config(page_title="AI Systemic Risk Terminal v2", layout="wide")
st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v2)")

st.caption("No synthetic data. All signals are real market data or explicit missing values.")

# =========================
# SAFE TOOLS
# =========================
def load(ticker):
    try:
        time.sleep(0.3)
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        return df
    except:
        return None


def ret_30(df):
    try:
        if df is None or df.empty:
            return None
        c = df["Close"].dropna()
        if len(c) < 30:
            return None
        return (float(c.iloc[-1]) / float(c.iloc[-30]) - 1) * 100
    except:
        return None


def fmt(x):
    return "无法采集数据" if x is None else f"{x:.2f}%"


# =========================
# DATA LAYER
# =========================
nvda = load("NVDA")
msft = load("MSFT")
qqq = load("QQQ")
tsla = load("TSLA")
dxy = load("DX-Y.NYB")
tnx = load("^TNX")

nvda_r = ret_30(nvda)
msft_r = ret_30(msft)
qqq_r = ret_30(qqq)
tsla_r = ret_30(tsla)
dxy_r = ret_30(dxy)
tnx_r = ret_30(tnx)

# =========================
# RISK ENGINE (simple but stable)
# =========================
risk_score = 0

if nvda_r is not None:
    risk_score += max(0, -nvda_r) * 0.4

if msft_r is not None:
    risk_score += max(0, -msft_r) * 0.3

if qqq_r is not None:
    risk_score += max(0, -qqq_r) * 0.3

if tsla_r is not None:
    risk_score += max(0, -tsla_r) * 0.2

if tnx_r is not None:
    risk_score += max(0, tnx_r) * 0.1

status = (
    "🔴 SYSTEMIC STRESS" if risk_score > 15 else
    "🟠 ELEVATED RISK" if risk_score > 8 else
    "🟢 STABLE"
)

# =========================
# HEADER DASHBOARD
# =========================
colA, colB, colC = st.columns(3)

with colA:
    st.metric("System Risk Score", round(risk_score, 2))
    st.write("Status:", status)

with colB:
    st.metric("DXY (USD proxy)", fmt(dxy_r))
    st.metric("10Y Yield (pressure)", fmt(tnx_r))

with colC:
    st.metric("NVDA (AI core)", fmt(nvda_r))
    st.metric("MSFT (AI cloud)", fmt(msft_r))

st.divider()

# =========================
# STRAW 1
# =========================
st.subheader("🧨 稻草一：AI 收入 vs CapEx 压力（AI 资产泡沫）")

st.markdown("**监测逻辑：** AI 公司靠未来利润定价，如果 AI 核心资产持续下跌，说明市场开始怀疑 AI 盈利能力。")

st.markdown("**指标体系：**")
st.write("- NVDA 30日收益率（GPU需求 proxy）")
st.write("- MSFT 30日收益率（AI云收入 proxy）")
st.write("- QQQ 30日收益率（AI科技整体估值）")

st.markdown("**当前数据：**")
st.write("NVDA:", fmt(nvda_r))
st.write("MSFT:", fmt(msft_r))
st.write("QQQ:", fmt(qqq_r))

st.divider()

# =========================
# STRAW 2
# =========================
st.subheader("🧨 稻草二：开源模型冲击（智力税崩塌风险）")

st.markdown("**监测逻辑：** 如果AI能力商品化（开源追平闭源），云厂商溢价会下降。")

st.markdown("**指标体系：**")
st.write("- MSFT（云AI定价能力 proxy）")
st.write("- QQQ（AI行业整体定价能力）")

st.markdown("**当前数据：**")
st.write("MSFT:", fmt(msft_r))
st.write("QQQ:", fmt(qqq_r))

st.divider()

# =========================
# STRAW 3
# =========================
st.subheader("🧨 稻草三：数据中心资产风险（重资产贬值）")

st.markdown("**监测逻辑：** AI数据中心是长周期资产，如果科技资产回撤，意味着未来CapEx可能收缩。")

st.markdown("**指标体系：**")
st.write("- NVDA（GPU资产链）")
st.write("- QQQ（科技资本开支预期）")

st.markdown("**当前数据：**")
st.write("NVDA:", fmt(nvda_r))
st.write("QQQ:", fmt(qqq_r))

st.divider()

# =========================
# STRAW 4
# =========================
st.subheader("🧨 稻草四：能源瓶颈（热力学约束）")

st.markdown("**监测逻辑：** AI = 电力工业，如果利率+能源成本上升，扩张速度下降。")

st.markdown("**指标体系：**")
st.write("- 10Y国债收益率（资金成本）")
st.write("- DXY美元指数（全球流动性收缩 proxy）")

st.markdown("**当前数据：**")
st.write("10Y Yield:", fmt(tnx_r))
st.write("DXY:", fmt(dxy_r))

st.divider()

# =========================
# STRAW 5
# =========================
st.subheader("🧨 稻草五：美元流动性收缩（AI杠杆系统核心风险）")

st.markdown("**监测逻辑：** AI投资依赖美元流动性，利率上升 + 美元走强 = 全球资金回流美国 = AI融资收缩。")

st.markdown("**指标体系：**")
st.write("- DXY（美元回流强度）")
st.write("- 10Y Yield（融资成本）")

st.markdown("**当前数据：**")
st.write("DXY:", fmt(dxy_r))
st.write("10Y:", fmt(tnx_r))

st.divider()

# =========================
# FINAL VIEW
# =========================
st.subheader("🧠 System Summary")

st.write("这是一个基于五大风险稻草的 AI 次贷结构监测模型。")
st.write("核心不是预测市场，而是监测 AI 资本结构是否进入去杠杆阶段。")

st.caption("v2: structured risk engine | data-driven | no synthetic values")
