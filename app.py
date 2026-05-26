import streamlit as st
import requests

# =========================
# CONFIG
# =========================
FMP_KEY = st.secrets.get("FMP_KEY", "")
FRED_KEY = st.secrets.get("FRED_KEY", "")

# =========================
# DATA LAYER (NO SILENT FAIL)
# =========================
def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        return r.json(), None
    except Exception as e:
        return None, str(e)


def get_fmp_cashflow(symbol):
    url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{symbol}?apikey={FMP_KEY}"
    data, err = fetch_json(url)
    if err or not data:
        return None, err
    try:
        return float(data[0]["capitalExpenditures"])
    except:
        return None, "parse_error"


def get_fmp_income(symbol):
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{symbol}?apikey={FMP_KEY}"
    data, err = fetch_json(url)
    if err or not data:
        return None, err
    try:
        return float(data[0]["revenue"])
    except:
        return None, "parse_error"


def get_fred(series):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={FRED_KEY}&file_type=json"
    data, err = fetch_json(url)
    if err or not data:
        return None, err
    try:
        return float(data["observations"][-1]["value"])
    except:
        return None, "parse_error"


# =========================
# SAFE CALC
# =========================
def pct_change(new, old):
    if new is None or old is None or old == 0:
        return None
    return (new - old) / abs(old) * 100


def risk_level(x, yellow, red):
    if x is None:
        return "⚪ 无数据"
    if x >= red:
        return "🔴 CRITICAL"
    if x >= yellow:
        return "🟠 WARNING"
    return "🟢 NORMAL"


# =========================
# STRAW 1 (CORE LOGIC)
# =========================
def straw1():
    msft_capex = get_fmp_cashflow("MSFT")
    amzn_capex = get_fmp_cashflow("AMZN")

    msft_rev = get_fmp_income("MSFT")
    amzn_rev = get_fmp_income("AMZN")

    capex_score = None
    revenue_score = None

    if msft_capex and amzn_capex:
        capex_score = msft_capex + amzn_capex

    if msft_rev and amzn_rev:
        revenue_score = msft_rev + amzn_rev

    gap = None
    if capex_score and revenue_score:
        gap = (capex_score / revenue_score) * 100

    return {
        "capex": capex_score,
        "revenue": revenue_score,
        "gap": gap
    }


# =========================
# UI
# =========================
st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v8)")

st.subheader("🧨 稻草1：AI资本循环")

s1 = straw1()

st.metric("CapEx (MSFT+AMZN)", "无法采集" if s1["capex"] is None else f"{s1['capex']:.0f}")
st.metric("Revenue (MSFT+AMZN)", "无法采集" if s1["revenue"] is None else f"{s1['revenue']:.0f}")

if s1["gap"] is None:
    st.warning("⚪ 稻草1：数据不足，无法计算结构失衡")
else:
    st.metric("CapEx/Revenue Pressure", f"{s1['gap']:.2f}%")

    if s1["gap"] > 30:
        st.error("🔴 AI资本循环过热")
    elif s1["gap"] > 20:
        st.warning("🟠 资本扩张偏快")
    else:
        st.success("🟢 正常结构")
        
