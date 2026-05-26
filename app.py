import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

# -----------------------------
# 页面
# -----------------------------
st.set_page_config(page_title="AI Systemic Risk Dashboard", layout="wide")
st.title("📊 AI Compute-Dollar Systemic Risk Dashboard")

# -----------------------------
# 工具函数
# -----------------------------
def safe_float(x):
    """严格转换，不允许造数"""
    try:
        if isinstance(x, pd.Series):
            x = x.dropna()
            if len(x) == 0:
                return None
            return float(x.iloc[-1])

        if isinstance(x, np.ndarray):
            return float(x[-1])

        if pd.isna(x):
            return None

        return float(x)

    except:
        return None


def risk_label(value, yellow=10, red=20):
    if value is None:
        return "⚪ 无法计算"

    if value >= red:
        return "🔴 高风险"
    elif value >= yellow:
        return "🟠 中风险"
    else:
        return "🟢 正常"


# -----------------------------
# 数据采集（严格模式）
# -----------------------------
@st.cache_data(ttl=3600)
def load_data(ticker):
    try:
        time.sleep(0.5)  # 防限流
        data = yf.download(ticker, period="3mo", interval="1d", progress=False)

        if data is None or data.empty:
            return None

        return data

    except:
        return None


def get_return(df, name):
    if df is None:
        st.warning(f"{name}: 无法采集数据")
        return None

    try:
        close = df["Close"].dropna()

        if len(close) < 30:
            st.warning(f"{name}: 数据不足30天")
            return None

        last = safe_float(close.iloc[-1])
        past = safe_float(close.iloc[-30])

        if last is None or past is None:
            st.warning(f"{name}: 数据异常")
            return None

        return (last / past - 1) * 100

    except:
        st.warning(f"{name}: 处理失败")
        return None


# -----------------------------
# 获取数据
# -----------------------------
nvda = load_data("NVDA")
qqq = load_data("QQQ")

nvda_return = get_return(nvda, "NVDA")
qqq_return = get_return(qqq, "QQQ")

# -----------------------------
# 展示
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("NVDA")
    if nvda_return is None:
        st.write("无法采集数据")
    else:
        st.metric("30D Return (%)", f"{nvda_return:.2f}")
        st.write("Risk:", risk_label(-nvda_return, 10, 20))

with col2:
    st.subheader("QQQ")
    if qqq_return is None:
        st.write("无法采集数据")
    else:
        st.metric("30D Return (%)", f"{qqq_return:.2f}")
        st.write("Risk:", risk_label(-qqq_return, 7, 15))

# -----------------------------
# 系统风险
# -----------------------------
st.subheader("🧠 System Risk Index")

if nvda_return is None and qqq_return is None:
    st.error("无法采集足够数据，系统风险无法计算")
else:
    score = 0

    if nvda_return is not None:
        score += max(0, -nvda_return) * 0.6

    if qqq_return is not None:
        score += max(0, -qqq_return) * 0.4

    status = (
        "🔴 SYSTEM STRESS" if score > 15 else
        "🟠 ELEVATED RISK" if score > 8 else
        "🟢 STABLE"
    )

    st.write("Score:", round(score, 2))
    st.write("Status:", status)

# -----------------------------
st.caption("No synthetic data. Only real market data or explicit missing signals.")
