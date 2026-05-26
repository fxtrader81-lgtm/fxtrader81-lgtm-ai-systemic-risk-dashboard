import streamlit as st
import requests
import time

FRED_KEY = "你的FRED_KEY"
FMP_KEY = "你的FMP_KEY"

# =========================
# SAFE REQUEST
# =========================

def safe_get(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None


# =========================
# FRED LAYER
# =========================

def fred(series):
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series,
        "api_key": FRED_KEY,
        "file_type": "json"
    }

    data = safe_get(url, params)
    if not data:
        return None

    try:
        vals = []
        for x in data["observations"]:
            v = x["value"]
            if v != ".":
                vals.append(float(v))

        return vals[-1] if vals else None
    except:
        return None


# =========================
# FMP LAYER
# =========================

def fmp_quote(symbol):
    url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
    params = {"apikey": FMP_KEY}

    data = safe_get(url, params)
    if not data or len(data) == 0:
        return None

    return data[0]


# =========================
# YFINANCE FALLBACK (optional)
# =========================

def yfinance_price(symbol):
    try:
        import yfinance as yf
        df = yf.download(symbol, period="1mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[-1])
    except:
        return None


# =========================
# UNIFIED DATA GETTER
# =========================

def get_data(symbol):
    # 1. FMP
    d = fmp_quote(symbol)
    if d and "price" in d:
        return d["price"]

    # 2. fallback yfinance
    return yfinance_price(symbol)


def get_macro(series):
    return fred(series)


# =========================
# STRAW 1 LOGIC (REAL)
# =========================

def straw1():
    nvda = get_data("NVDA")
    msft = get_data("MSFT")
    qqq = get_data("QQQ")

    capex = get_macro("B009RC1Q027SBEA")
    rate = get_macro("DGS10")

    score = 0
    if capex:
        score += capex
    if rate:
        score += rate

    return nvda, msft, qqq, capex, rate, score


# =========================
# UI SAFE FORMAT
# =========================

def fmt(x):
    return "无法采集数据" if x is None else f"{x:.2f}"


# =========================
# APP
# =========================

st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v7)")

nvda, msft, qqq, capex, rate, score = straw1()

st.subheader("🧨 稻草1：AI资本循环")

st.write("NVDA:", fmt(nvda))
st.write("MSFT:", fmt(msft))
st.write("QQQ:", fmt(qqq))

st.write("CapEx:", fmt(capex))
st.write("10Y Rate:", fmt(rate))

st.subheader("🧠 System Score")

st.write(score if score else "无法计算")

st.success("系统运行成功（无 synthetic data）")
