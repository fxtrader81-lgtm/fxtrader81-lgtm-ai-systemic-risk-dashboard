import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"

# ⚠️ 关键修复：不要用 /stable
BASE = "https://financialmodelingprep.com/api/v3"

symbol = st.text_input("Symbol", "NVDA")


# =========================
# FETCH (带错误显示)
# =========================
@st.cache_data(ttl=3600)
def fetch(url):
    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "url": url}

        data = r.json()

        if isinstance(data, dict) and "Error Message" in data:
            return {"error": data["Error Message"], "url": url}

        return data

    except Exception as e:
        return {"error": str(e), "url": url}


# =========================
# SAFE GET
# =========================
def get(x, keys):
    for k in keys:
        try:
            if k in x and x[k] is not None:
                return float(x[k])
        except:
            pass
    return 0.0


# =========================
# API CALLS（修复路径）
# =========================
income_url = f"{BASE}/income-statement/{symbol}?limit=8&apikey={API_KEY}"
cash_url = f"{BASE}/cash-flow-statement/{symbol}?limit=8&apikey={API_KEY}"

income = fetch(income_url)
cash = fetch(cash_url)


# =========================
# DEBUG（关键：避免黑盒）
# =========================
with st.expander("🔍 Debug Info"):
    st.write("Income URL:", income_url)
    st.write("Cash URL:", cash_url)
    st.write("Income RAW:", income[:1] if isinstance(income, list) else income)
    st.write("Cash RAW:", cash[:1] if isinstance(cash, list) else cash)


# =========================
# ERROR HANDLING
# =========================
if isinstance(income, dict) and "error" in income:
    st.error(f"Income API Error: {income['error']}")
    st.stop()

if isinstance(cash, dict) and "error" in cash:
    st.error(f"Cash API Error: {cash['error']}")
    st.stop()

if not isinstance(income, list) or not isinstance(cash, list):
    st.error("API返回格式异常（不是list）")
    st.stop()

if len(income) < 2 or len(cash) < 2:
    st.error("数据不足（至少需要2期财报）")
    st.stop()


# =========================
# BUILD DATAFRAME
# =========================
dates, revenue, capex = [], [], []

for i in range(min(len(income), len(cash))):
    inc = income[i]
    cf = cash[i]

    dates.append(inc.get("date", str(i)))

    revenue.append(
        get(inc, ["revenue", "revenueUSD", "totalRevenue"])
    )

    capex.append(
        abs(get(cf, ["capitalExpenditure", "capex"]))
    )

df = pd.DataFrame({
    "date": dates,
    "revenue": revenue,
    "capex": capex
}).iloc[::-1]


# =========================
# METRICS
# =========================
df["rev_growth"] = df["revenue"].pct_change()
df["capex_growth"] = df["capex"].pct_change()

rev_g = df["rev_growth"].iloc[-1]
capex_g = df["capex_growth"].iloc[-1]

risk_gap = capex_g - rev_g

overheat = capex_g > rev_g * 1.2


# =========================
# UI
# =========================
st.title(f"📊 AI Compute-Dollar Risk Terminal — {symbol}")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Revenue Growth", f"{rev_g*100:.2f}%")
col2.metric("CapEx Growth", f"{capex_g*100:.2f}%")
col3.metric("Risk Gap", f"{risk_gap*100:.2f}%")
col4.metric("Status", "OVERHEAT" if overheat else "NORMAL")


# =========================
# ALERT
# =========================
if overheat:
    st.error("⚠️ CapEx增长显著高于Revenue增长（潜在AI过热）")
else:
    st.success("✅ 结构健康：收入仍支撑资本开支")


# =========================
# CHART
# =========================
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["date"],
    y=df["revenue"],
    name="Revenue"
))

fig.add_trace(go.Scatter(
    x=df["date"],
    y=df["capex"],
    name="CapEx"
))

fig.update_layout(
    height=500,
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font=dict(color="white")
)

st.plotly_chart(fig, use_container_width=True)


# =========================
# TABLE
# =========================
st.subheader("Raw Data")
st.dataframe(df)
