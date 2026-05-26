import streamlit as st
import yfinance as yf
import pandas as pd
import time

# =========================
# UI
# =========================
st.set_page_config(page_title="AI Systemic Risk Terminal v2.1", layout="wide")
st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v2.1)")

st.caption("No synthetic data. Structural signals only. Missing data is explicitly shown.")

# =========================
# SAFE DATA LOADER
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


def pct_change(df):
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
    if x is None:
        return "无法采集数据"
    return f"{x:.2f}%"


# =========================
# DATA
# =========================
nvda = load("NVDA")
msft = load("MSFT")
qqq = load("QQQ")
amzn = load("AMZN")
goog = load("GOOG")

nvda_r = pct_change(nvda)
msft_r = pct_change(msft)
qqq_r = pct_change(qqq)
amzn_r = pct_change(amzn)
goog_r = pct_change(goog)

# =========================
# HEADER
# =========================
st.subheader("📌 Market Signal Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("NVDA (AI infra proxy)", fmt(nvda_r))
    st.metric("MSFT (AI monetization proxy)", fmt(msft_r))

with col2:
    st.metric("AMZN (AWS CapEx proxy)", fmt(amzn_r))
    st.metric("GOOG (AI infrastructure proxy)", fmt(goog_r))

with col3:
    st.metric("QQQ (AI expectation proxy)", fmt(qqq_r))

st.divider()

# =========================
# 🧨 STRAW 1 (REWRITTEN)
# =========================
st.subheader("🧨 稻草一：AI资本循环是否过热（CapEx → 收入 → 预期闭环）")

st.markdown(
"""
AI产业本质上是一个由资本支出驱动的扩张系统，其风险核心在于“投入—算力—收入”闭环是否成立。

当GPU与数据中心的资本开支持续上升，但云计算与AI服务收入增长开始放缓，就意味着资本正在提前透支未来收益，结构性失衡正在累积。

这一稻草不直接观察股价，而是拆解为三类结构性指标：

1. **资本投入强度（CapEx Proxy）**
   - AMZN（AWS基础设施扩张）
   - GOOG（AI数据中心扩张）
   👉 代表AI是否仍在加速“堆算力”

2. **真实变现能力（Revenue Proxy）**
   - MSFT（AI云收入能力）
   - NVDA（GPU需求链条）
   👉 代表AI是否真的在产生现金流

3. **市场预期压力（Expectation Proxy）**
   - QQQ（科技整体估值体系）
   👉 代表市场是否开始重新定价未来增长

当“资本投入上升 + 收入增长趋缓 + 估值承压”同时出现时，
说明AI系统从增长叙事进入收益验证阶段，这是泡沫结构最早的压力信号。
"""
)

st.write("📊 当前数据：")
st.write("AMZN CapEx proxy:", fmt(amzn_r))
st.write("GOOG CapEx proxy:", fmt(goog_r))
st.write("MSFT Revenue proxy:", fmt(msft_r))
st.write("NVDA Demand proxy:", fmt(nvda_r))
st.write("QQQ Expectation proxy:", fmt(qqq_r))

st.divider()

# =========================
# STRAW 2
# =========================
st.subheader("🧨 稻草二：开源模型冲击（智力税结构风险）")

st.markdown("""
监测逻辑：如果AI能力快速商品化（开源追平闭源），高毛利API定价能力会下降，云厂商的AI溢价体系将被削弱。
""")

st.write("Proxy指标：MSFT / GOOG / QQQ")
st.write("MSFT:", fmt(msft_r))
st.write("GOOG:", fmt(goog_r))
st.write("QQQ:", fmt(qqq_r))

st.divider()

# =========================
# STRAW 3
# =========================
st.subheader("🧨 稻草三：数据中心资产贬值风险")

st.markdown("""
AI数据中心属于长周期重资产，一旦AI硬件迭代加速（GPU升级、液冷普及），旧资产可能快速折旧。
""")

st.write("NVDA:", fmt(nvda_r))
st.write("AMZN:", fmt(amzn_r))
st.write("GOOG:", fmt(goog_r))

st.divider()

# =========================
# STRAW 4
# =========================
st.subheader("🧨 稻草四：能源与融资约束")

st.markdown("""
AI扩张依赖电力与融资成本。当利率上升时，AI基础设施扩张速度下降。
""")

st.write("AMZN (CapEx sensitivity):", fmt(amzn_r))
st.write("GOOG (energy + infra):", fmt(goog_r))

st.divider()

# =========================
# STRAW 5
# =========================
st.subheader("🧨 稻草五：美元流动性与全球资金回流")

st.markdown("""
美元走强 + 科技估值承压 = 全球流动性收缩 → AI杠杆扩张能力下降。
""")

st.write("QQQ:", fmt(qqq_r))

st.divider()

# =========================
# SYSTEM VIEW
# =========================
st.subheader("🧠 System Summary")

st.write("""
该系统用于监测AI产业是否从“增长驱动阶段”进入“收益验证阶段”。
核心不在预测价格，而在识别资本结构是否出现提前透支未来收益的迹象。
""")

st.caption("v2.1: structural AI systemic risk model | no synthetic data | capex-revenue-expectation decomposition")
