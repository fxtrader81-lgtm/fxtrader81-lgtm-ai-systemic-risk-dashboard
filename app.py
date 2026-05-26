import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from fredapi import Fred
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# ==========================================================
# CONFIG
# ==========================================================

st.set_page_config(
    page_title="AI Compute-Dollar Risk Dashboard",
    layout="wide"
)

st.title("📉 AI Compute-Dollar Systemic Risk Dashboard")
st.markdown(
    "Monitoring the financial stability of the AI infrastructure bubble"
)

# ==========================================================
# FRED CONFIG
# ==========================================================
# Create a free API key:
# https://fred.stlouisfed.org/docs/api/api_key.html
# Then add into Streamlit secrets:
# [general]
# fred_api_key="YOUR_KEY"

try:
    fred = Fred(api_key=st.secrets["general"]["fred_api_key"])
except:
    fred = None
    st.warning("FRED API key missing. Some macro data unavailable.")

# ==========================================================
# DATA HELPERS
# ==========================================================

def get_stock_data(ticker, period="2y"):
    try:
        data = yf.download(ticker, period=period, auto_adjust=True)
        return data
    except:
        return pd.DataFrame()


def get_fred_series(series_id):
    try:
        if fred is None:
            return None
        s = fred.get_series(series_id)
        df = pd.DataFrame(s, columns=[series_id])
        df.index = pd.to_datetime(df.index)
        return df
    except:
        return None


def calculate_risk_level(value, yellow, red, reverse=False):
    """
    reverse=False:
        higher value = more dangerous

    reverse=True:
        lower value = more dangerous
    """

    if reverse:
        if value <= red:
            return "🔴 CRITICAL"
        elif value <= yellow:
            return "🟠 WARNING"
        else:
            return "🟢 HEALTHY"

    else:
        if value >= red:
            return "🔴 CRITICAL"
        elif value >= yellow:
            return "🟠 WARNING"
        else:
            return "🟢 HEALTHY"


# ==========================================================
# SECTION 1
# AI CAPEX / MARKET STRESS
# ==========================================================

st.header("1️⃣ AI CapEx & Market Stress")

nvda = get_stock_data("NVDA")
msft = get_stock_data("MSFT")
meta = get_stock_data("META")
qqq = get_stock_data("QQQ")

col1, col2, col3 = st.columns(3)

if not nvda.empty:
    nvda_return = (
        nvda["Close"].iloc[-1] / nvda["Close"].iloc[-30] - 1
    ) * 100

    risk = calculate_risk_level(
        -nvda_return,
        yellow=10,
        red=20
    )

    col1.metric(
        "NVDA 30D Return",
        f"{nvda_return:.2f}%"
    )

    col1.markdown(f"Risk Signal: {risk}")

if not qqq.empty:
    qqq_return = (
        qqq["Close"].iloc[-1] / qqq["Close"].iloc[-30] - 1
    ) * 100

    risk = calculate_risk_level(
        -qqq_return,
        yellow=7,
        red=15
    )

    col2.metric(
        "QQQ 30D Return",
        f"{qqq_return:.2f}%"
    )

    col2.markdown(f"Risk Signal: {risk}")

ai_proxy_index = (
    nvda["Close"] + msft["Close"] + meta["Close"]
) / 3

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=ai_proxy_index.index,
        y=ai_proxy_index,
        name="AI Proxy Index"
    )
)

fig.update_layout(height=400)
st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# SECTION 2
# LIQUIDITY & INTEREST RATE RISK
# ==========================================================

st.header("2️⃣ Dollar Liquidity & Interest Rate Risk")

us10y = get_fred_series("DGS10")
real_rate = get_fred_series("DFII10")
hy_spread = get_fred_series("BAMLH0A0HYM2")

col1, col2, col3 = st.columns(3)

if us10y is not None:
    latest_10y = us10y.dropna().iloc[-1][0]

    risk = calculate_risk_level(
        latest_10y,
        yellow=4.5,
        red=5.25
    )

    col1.metric(
        "US 10Y Yield",
        f"{latest_10y:.2f}%"
    )

    col1.markdown(f"Risk Signal: {risk}")

if real_rate is not None:
    latest_real = real_rate.dropna().iloc[-1][0]

    risk = calculate_risk_level(
        latest_real,
        yellow=2.0,
        red=2.5
    )

    col2.metric(
        "Real Interest Rate",
        f"{latest_real:.2f}%"
    )

    col2.markdown(f"Risk Signal: {risk}")

if hy_spread is not None:
    latest_hy = hy_spread.dropna().iloc[-1][0]

    risk = calculate_risk_level(
        latest_hy,
        yellow=4.5,
        red=6.0
    )

    col3.metric(
        "High Yield Spread",
        f"{latest_hy:.2f}%"
    )

    col3.markdown(f"Risk Signal: {risk}")

# ==========================================================
# SECTION 3
# ENERGY STRESS
# ==========================================================

st.header("3️⃣ AI Energy Stress")

natgas = get_stock_data("NG=F")
utilities = get_stock_data("XLU")

col1, col2 = st.columns(2)

if not natgas.empty:
    natgas_change = (
        natgas["Close"].iloc[-1] / natgas["Close"].iloc[-90] - 1
    ) * 100

    risk = calculate_risk_level(
        natgas_change,
        yellow=20,
        red=40
    )

    col1.metric(
        "Natural Gas 90D Change",
        f"{natgas_change:.2f}%"
    )

    col1.markdown(f"Risk Signal: {risk}")

if not utilities.empty:
    util_change = (
        utilities["Close"].iloc[-1] /
        utilities["Close"].iloc[-90] - 1
    ) * 100

    col2.metric(
        "Utilities ETF 90D Change",
        f"{util_change:.2f}%"
    )

# ==========================================================
# SECTION 4
# AI BUBBLE TEMPERATURE INDEX
# ==========================================================

st.header("4️⃣ AI Systemic Risk Index")

risk_score = 0
max_score = 5

# 10Y risk
if us10y is not None:
    if latest_10y > 5.25:
        risk_score += 1

# HY spread risk
if hy_spread is not None:
    if latest_hy > 6:
        risk_score += 1

# NVDA crash risk
if not nvda.empty:
    if nvda_return < -20:
        risk_score += 1

# Natural gas risk
if not natgas.empty:
    if natgas_change > 40:
        risk_score += 1

# QQQ risk
if not qqq.empty:
    if qqq_return < -15:
        risk_score += 1

risk_percent = (risk_score / max_score) * 100

if risk_percent < 25:
    risk_label = "🟢 GREEN"
elif risk_percent < 50:
    risk_label = "🟡 YELLOW"
elif risk_percent < 75:
    risk_label = "🟠 ORANGE"
else:
    risk_label = "🔴 RED"

st.metric(
    "AI Systemic Risk Index",
    f"{risk_percent:.0f}/100"
)

st.markdown(f"## Current Regime: {risk_label}")

# ==========================================================
# SECTION 5
# RISK INTERPRETATION ENGINE
# ==========================================================

st.header("5️⃣ Market Interpretation Engine")

messages = []

if us10y is not None and latest_10y > 5:
    messages.append(
        "• Long-duration AI assets are under pressure from high interest rates."
    )

if hy_spread is not None and latest_hy > 5:
    messages.append(
        "• Credit markets are beginning to price higher default risk."
    )

if not nvda.empty and nvda_return < -15:
    messages.append(
        "• AI infrastructure equities are entering valuation compression."
    )

if not natgas.empty and natgas_change > 35:
    messages.append(
        "• Energy costs may begin compressing AI inference margins."
    )

if len(messages) == 0:
    st.success(
        "AI financial conditions currently stable."
    )
else:
    for m in messages:
        st.warning(m)

# ==========================================================
# FOOTER
# ==========================================================

st.markdown("---")
st.markdown(
    """
### Suggested Future Improvements

- Add SEC filing parser for AI CapEx extraction
- Add GPU spot pricing APIs
- Add Hugging Face open-source activity tracker
- Add data center REIT monitoring
- Add electricity market APIs
- Add ABS / CMBS delinquency feeds
- Add automated monthly reporting
- Add email alert engine
- Add AI bubble probability model
"""
)

# ==========================================================
# GITHUB DEPLOYMENT GUIDE
# ==========================================================

st.markdown("---")
st.markdown("## Deployment Guide")

st.code(
"""
pip install streamlit yfinance fredapi plotly pandas numpy requests

streamlit run app.py
"""
)

st.markdown(
    "Deploy free on Streamlit Cloud using GitHub integration."
)
