import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

API_KEY = "YOUR_API_KEY_HERE"
BASE = "https://financialmodelingprep.com/stable"

symbol = st.text_input("Symbol", "NVDA")


# =========================
# CACHE (防止限流)
# =========================
@st.cache_data(ttl=3600)
def fetch(url):
    try:
        r = requests.get(url, timeout=10)

        # HTTP error
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}"}

        data = r.json()

        # API error message
        if isinstance(data, dict) and "Error Message" in data:
            return {"error": data["Error Message"]}

        return data

    except Exception as e:
        return {"error": str(e)}


# =========================
# SAFE FIELD PARSER
# =========================
def get_value(x, keys):
    """Try multiple possible keys"""
    for k in keys:
        if isinstance(x, dict) and k in x and x[k] is not None:
            try:
                return float(x[k])
            except:
                pass
    return 0.0


# =========================
# FETCH DATA
# =========================
income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=8&apikey={API_KEY}")
cash = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=8&apikey={API_KEY}")


# =========================
# ERROR HANDLING
# =========================
if isinstance(income, dict) and "error" in income:
    st.error(f"Income API Error: {income['error']}")
    st.stop()

if isinstance(cash, dict) and "error" in cash:
    st.error(f"Cashflow API Error: {cash['error']}")
    st.stop()

if not isinstance(income, list) or not isinstance(cash, list):
    st.error("API返回结构异常（非list）")
    st.stop()

if len(income) < 2 or len(cash) < 2:
    st.error("数据不足（至少需要2期数据）")
    st.stop()


# =========================
# BUILD DATA
# =========================
rev, capex, dates = [], [], []

for i in range(min(len(income), len(cash))):
    inc = income[i]
    cf = cash[i]

    revenue = get_value(inc, ["revenue", "revenueUSD", "totalRevenue"])
    capex_v = abs(get_value(cf, ["capitalExpenditure", "capex"]))
    date = inc.get("date", str(i))

    rev.append(revenue)
    capex.append(capex_v)
    dates.append(date)


df = pd.DataFrame({
    "date": dates,
    "revenue": rev,
    "capex": capex
})

df = df.iloc[::-1]  # chronological


# =========================
# METRICS
# =========================
df["rev_growth"] = df["revenue"].pct_change()
df["capex_growth"] = df["capex"].pct_change()

latest_rev_growth = df["rev_growth"].iloc[-1] if len(df) > 1 else 0
latest_capex_growth = df["capex_growth"].iloc[-1] if len(df) > 1 else 0

risk_gap = latest_capex_growth - latest_rev_growth

overheat = latest_capex_growth > latest_rev_growth * 1.2


# =========================
# UI HEADER
# =========================
st.title(f"📊 AI Compute-Dollar Risk Terminal — {symbol}")


# =========================
# KPI CARDS
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("Revenue Growth", f"{latest_rev_growth*100:.2f}%")
col2.metric("CapEx Growth", f"{latest_capex_growth*100:.2f}%")
col3.metric("Risk Gap", f"{risk_gap*100:.2f}%")
col4.metric("Status", "OVERHEAT" if overheat else "NORMAL")


# =========================
# ALERT
# =========================
if overheat:
    st.error("⚠️ 资本开支增长显著高于收入增长 —— 可能进入过热阶段")
else:
    st.success("✅ 资本开支与收入增长结构健康")


# =========================
# CHART
# =========================
fig = go.Figure()

fig.add_trace(go.Scatter(
    y=df["revenue"],
    x=df["date"],
    name="Revenue"
))

fig.add_trace(go.Scatter(
    y=df["capex"],
    x=df["date"],
    name="CapEx"
))

fig.update_layout(
    height=500,
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font=dict(color="white"),
    margin=dict(l=10, r=10, t=30, b=10)
)

st.plotly_chart(fig, use_container_width=True)


# =========================
# TABLE
# =========================
st.subheader("Raw Data")
st.dataframe(df)
