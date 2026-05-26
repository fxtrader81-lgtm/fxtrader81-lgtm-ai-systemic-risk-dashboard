import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================
FRED_API_KEY = st.secrets.get("fred_api_key", None)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


# =========================
# SAFE FETCH (FRED ONLY, NO FAKE DATA)
# =========================
def fetch_fred(series_id):
    if FRED_API_KEY is None:
        return None

    try:
        end = datetime.today()
        start = end - timedelta(days=365)

        url = (
            f"{FRED_BASE}?series_id={series_id}"
            f"&api_key={FRED_API_KEY}"
            f"&file_type=json"
            f"&observation_start={start.strftime('%Y-%m-%d')}"
        )

        r = requests.get(url, timeout=10)
        data = r.json().get("observations", [])

        values = []
        for x in data:
            v = x["value"]
            if v != ".":
                values.append(float(v))

        if len(values) < 2:
            return None

        return pd.Series(values)

    except:
        return None


# =========================
# SAFE METRIC FORMATTER
# =========================
def fmt(x):
    if x is None:
        return "无法采集数据"
    if isinstance(x, pd.Series):
        x = x.iloc[-1]
    return f"{float(x):.2f}"


# =========================
# RISK ENGINE (FIXED)
# =========================
def risk_level(x, yellow, red):
    if x is None:
        return "⚪ 无数据"
    try:
        v = float(x)
    except:
        return "⚪ 无数据"

    if v >= red:
        return "🔴 CRITICAL"
    elif v >= yellow:
        return "🟠 WARNING"
    return "🟢 STABLE"


# =========================
# HEADER
# =========================
st.title("📊 AI Compute-Dollar Systemic Risk Terminal (v1 REAL DATA)")

st.caption("No synthetic data. Only FRED macro signals. Missing data shown explicitly.")


# =========================
# LOAD DATA (REAL MACRO PROXIES)
# =========================

# --- 稻草1：AI资本循环 ---
capex = fetch_fred("A011RE1Q156NBEA")  # US private fixed investment proxy

# --- 稻草2：开源冲击 ---
credit_spread = fetch_fred("BAMLH0A0HYM2")  # HY credit spread

# --- 稻草3：数据中心风险 ---
investment = fetch_fred("TTLCONS")  # construction spending

# --- 稻草4：能源压力 ---
oil = fetch_fred("DCOILWTICO")
teny = fetch_fred("DGS10")

# --- 稻草5：流动性 ---
m2 = fetch_fred("M2SL")
fed_balance = fetch_fred("WALCL")


# =========================
# COMPUTE SIGNALS (SAFE)
# =========================
def pct(series):
    if series is None:
        return None
    if len(series) < 30:
        return None
    return (series.iloc[-1] / series.iloc[-30] - 1) * 100


capex_r = pct(capex)
credit_r = pct(credit_spread)
inv_r = pct(investment)
oil_r = pct(oil)
m2_r = pct(m2)


# =========================
# UI
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("CapEx Proxy", fmt(capex_r))
    st.caption(risk_level(capex_r, 3, 8))

with col2:
    st.metric("Credit Stress", fmt(credit_r))
    st.caption(risk_level(credit_r, 2, 5))

with col3:
    st.metric("Liquidity (M2)", fmt(m2_r))
    st.caption(risk_level(m2_r, 1, 4))


st.divider()

st.subheader("🧨 Five Straw System Map")

st.write("### 稻草1：AI资本循环压力")
st.write("判断：资本开支增长是否领先真实经济回报")
st.write("状态：", risk_level(capex_r, 3, 8))

st.write("### 稻草2：开源冲击（信用压力 proxy）")
st.write("判断：信用利差是否扩大（市场开始拒绝风险资产）")
st.write("状态：", risk_level(credit_r, 2, 5))

st.write("### 稻草3：数据中心投资周期")
st.write("判断：基础设施是否进入过热或衰退")
st.write("状态：", risk_level(inv_r, 2, 6))

st.write("### 稻草4：能源压力")
st.write("判断：油价 + 利率是否形成成本冲击")
st.write("状态：", risk_level(oil_r, 5, 15))

st.write("### 稻草5：美元流动性")
st.write("判断：M2增长是否收缩（流动性抽离）")
st.write("状态：", risk_level(m2_r, 2, 6))


st.divider()

# =========================
# SYSTEM SCORE (SIMPLE BUT STABLE)
# =========================
score = 0
count = 0

for x, w in [
    (capex_r, 1.5),
    (credit_r, 2),
    (inv_r, 1),
    (oil_r, 1),
    (m2_r, 2),
]:
    if x is not None:
        score += max(0, x) * w
        count += 1

if count > 0:
    score = score / count

status = "🟢 STABLE"
if score > 8:
    status = "🟠 WARNING"
if score > 15:
    status = "🔴 CRITICAL"

st.subheader("🧠 System Risk Engine")
st.metric("Risk Score", f"{score:.2f}")
st.markdown(f"### {status}")
