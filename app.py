import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="AI Compute-Dollar v5", layout="wide")
st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v5)")

st.caption("FRED + FMP + Market hybrid system | No synthetic data")

# =========================
# KEYS (from Streamlit Secrets)
# =========================
FRED_KEY = st.secrets.get("fred_api_key", None)
FMP_KEY = st.secrets.get("fmp_api_key", None)

# =========================
# SAFE UTIL
# =========================
def safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except:
        return None


def fmt(x):
    try:
        if x is None or pd.isna(x):
            return "无法采集数据"
        return f"{float(x):.2f}"
    except:
        return "无法采集数据"


# =========================
# FRED LOADER
# =========================
def fred(series_id):
    if not FRED_KEY:
        return None

    try:
        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={FRED_KEY}&file_type=json"
        )
        r = requests.get(url, timeout=10)
        data = r.json()

        values = [
            float(o["value"])
            for o in data.get("observations", [])
            if o["value"] != "."
        ]

        return pd.Series(values) if values else None
    except:
        return None


# =========================
# FMP LOADER (核心升级)
# =========================
def fmp(metric_url):
    if not FMP_KEY:
        return None

    try:
        url = metric_url + FMP_KEY
        r = requests.get(url, timeout=10)
        data = r.json()

        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except:
        return None


# =========================
# MARKET DATA
# =========================
def yf_load(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df is None or df.empty:
            return None
        return df["Close"]
    except:
        return None


def ret30(s):
    try:
        if s is None or len(s) < 30:
            return None
        return (s.iloc[-1] / s.iloc[-30] - 1) * 100
    except:
        return None


# =========================
# MARKET
# =========================
nvda = yf_load("NVDA")
msft = yf_load("MSFT")
qqq = yf_load("QQQ")

# =========================
# FRED MACRO
# =========================
fedfunds = fred("FEDFUNDS")
teny = fred("DGS10")
baa = fred("BAA")
m2 = fred("M2SL")

# =========================
# FMP (AI核心公司财务)
# =========================
msft_income = fmp(f"https://financialmodelingprep.com/api/v3/income-statement/MSFT?limit=1&apikey=")
amzn_income = fmp(f"https://financialmodelingprep.com/api/v3/income-statement/AMZN?limit=1&apikey=")

msft_profile = fmp(f"https://financialmodelingprep.com/api/v3/key-metrics/MSFT?limit=1&apikey=")
amzn_profile = fmp(f"https://financialmodelingprep.com/api/v3/key-metrics/AMZN?limit=1&apikey=")

# =========================
# UI
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("NVDA (AI Infra)", fmt(ret30(nvda)))
    st.metric("MSFT (Market)", fmt(ret30(msft)))

with col2:
    st.metric("QQQ (Expectation)", fmt(ret30(qqq)))

with col3:
    st.metric("10Y Yield", fmt(teny.iloc[-1] if teny is not None else None))
    st.metric("Fed Funds", fmt(fedfunds.iloc[-1] if fedfunds is not None else None))

st.divider()

# =========================
# 🧨 STRAW 1 AI CAPITAL
# =========================
st.subheader("🧨 稻草一：AI资本循环（市场 + 收入预期）")

st.write("NVDA:", fmt(ret30(nvda)))
st.write("MSFT:", fmt(ret30(msft)))
st.write("QQQ:", fmt(ret30(qqq)))

st.write("""
逻辑：AI是否还能被“增长叙事”支撑。
""")

st.divider()

# =========================
# 🧨 STRAW 2 CAPEX vs CASHFLOW
# =========================
st.subheader("🧨 稻草二：AI真实盈利能力（FMP）")

msft_capex = msft_profile["capitalExpenditure"] if msft_profile else None
amzn_capex = amzn_profile["capitalExpenditure"] if amzn_profile else None

msft_fcf = msft_profile["freeCashFlow"] if msft_profile else None
amzn_fcf = amzn_profile["freeCashFlow"] if amzn_profile else None

st.write("MSFT CapEx:", fmt(msft_capex))
st.write("AMZN CapEx:", fmt(amzn_capex))

st.write("MSFT FCF:", fmt(msft_fcf))
st.write("AMZN FCF:", fmt(amzn_fcf))

st.write("""
逻辑：如果 CapEx >> FCF → AI进入烧钱扩张阶段（泡沫风险↑）
""")

st.divider()

# =========================
# 🧨 STRAW 3 LIQUIDITY
# =========================
st.subheader("🧨 稻草三：流动性与利率")

st.write("Fed Funds:", fmt(fedfunds.iloc[-1] if fedfunds is not None else None))
st.write("10Y:", fmt(teny.iloc[-1] if teny is not None else None))
st.write("M2:", fmt(m2.iloc[-1] if m2 is not None else None))

st.write("""
逻辑：流动性收缩 → AI高估值无法维持
""")

st.divider()

# =========================
# 🧠 RISK ENGINE
# =========================
st.subheader("🧠 AI Bubble Risk Index (0–100)")

risk = 0
count = 0

for x in [ret30(nvda), ret30(msft), ret30(qqq)]:
    if x is not None:
        risk += max(0, -x)
        count += 1

for x in [safe_float(fedfunds.iloc[-1] if fedfunds is not None else None)]:
    if x is not None:
        risk += x
        count += 1

risk_score = min(100, risk / max(count, 1) * 12)

status = (
    "🟢 STABLE" if risk_score < 30 else
    "🟠 WARNING" if risk_score < 60 else
    "🔴 CRITICAL"
)

st.metric("Risk Score", round(risk_score, 2))
st.write("Status:", status)

st.caption("v5: FRED + FMP + Market fully integrated | macro + earnings + sentiment")
