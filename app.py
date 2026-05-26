import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="AI Risk Terminal", layout="wide")

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =========================
# STYLE
# =========================
st.markdown("""
<style>

body {
    background-color: #0b0f19;
    color: white;
}

.block {
    background: #121a2a;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
    border: 1px solid #1f2a44;
}

.title {
    font-size: 20px;
    font-weight: 600;
    color: #7dd3fc;
}

.metric {
    font-size: 16px;
    margin-top: 6px;
}

.good { color: #22c55e; }
.warn { color: #fbbf24; }
.bad { color: #ef4444; }

.small {
    font-size: 13px;
    color: #94a3b8;
}

</style>
""", unsafe_allow_html=True)

# =========================
# INPUT
# =========================
symbol = st.text_input("Symbol", "NVDA")

# =========================
# FETCH
# =========================
@st.cache_data(ttl=300)
def fetch(url):

    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return {
                "error": f"HTTP {r.status_code}"
            }

        return r.json()

    except Exception as e:
        return {
            "error": str(e)
        }

# =========================
# SAFE
# =========================
def safe(x, k):

    try:
        return float(x.get(k, 0))
    except:
        return 0.0

# =========================
# API
# =========================
income_url = f"{BASE}/income-statement?symbol={symbol}&limit=6&apikey={API_KEY}"

cash_url = f"{BASE}/cash-flow-statement?symbol={symbol}&limit=6&apikey={API_KEY}"

income = fetch(income_url)
cash = fetch(cash_url)

# =========================
# DEBUG
# =========================
with st.expander("🔍 Debug"):

    st.write("Income URL:", income_url)
    st.write("Cash URL:", cash_url)

    st.write("Income Type:", type(income))
    st.write("Cash Type:", type(cash))

# =========================
# ERROR
# =========================
if isinstance(income, dict) and "error" in income:
    st.error(f"Income API Error: {income['error']}")
    st.stop()

if isinstance(cash, dict) and "error" in cash:
    st.error(f"Cash API Error: {cash['error']}")
    st.stop()

if not isinstance(income, list) or not isinstance(cash, list):
    st.error("API返回结构异常")
    st.stop()

if len(income) < 2 or len(cash) < 2:
    st.error("数据不足")
    st.stop()

# =========================
# BUILD DATA
# =========================
dates = []
revenues = []
capexs = []

for i in range(min(len(income), len(cash))):

    inc = income[i]
    cf = cash[i]

    dates.append(inc.get("date", str(i)))

    revenues.append(
        safe(inc, "revenue")
    )

    capexs.append(
        abs(safe(cf, "capitalExpenditure"))
    )

df = pd.DataFrame({
    "date": dates,
    "revenue": revenues,
    "capex": capexs
})

df = df.iloc[::-1]

# =========================
# METRICS
# =========================
df["rev_growth"] = df["revenue"].pct_change()

df["capex_growth"] = df["capex"].pct_change()

rev_growth = df["rev_growth"].iloc[-1]
capex_growth = df["capex_growth"].iloc[-1]

# =========================
# STRAW 1
# =========================
if capex_growth > rev_growth * 1.2:

    status = "🟡 过热风险"
    cls = "warn"

    desc = "资本开支扩张速度明显高于收入增长"

elif capex_growth > rev_growth:

    status = "🟠 偏热"
    cls = "warn"

    desc = "资本扩张开始领先收入增长"

else:

    status = "🟢 健康"
    cls = "good"

    desc = "收入增长仍能覆盖资本开支"

# =========================
# CARD
# =========================
st.markdown(f"""
<div class="block">

<div class="title">
🧨 稻草一：AI资本开支循环检测
</div>

<div class="metric">
当前状态：
<b class="{cls}">{status}</b>
</div>

<div class="metric">
核心判断：
{desc}
</div>

<div class="small">
逻辑：
CapEx增速 > 收入增速 × 1.2
→ 判定为资本过热
</div>

<div class="small">
收入增速：
{rev_growth:.2%}
｜
CapEx增速：
{capex_growth:.2%}
</div>

</div>
""", unsafe_allow_html=True)

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
    paper_bgcolor="#0b0f19",
    plot_bgcolor="#0b0f19",
    font=dict(color="white"),
    height=500
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# DATA
# =========================
with st.expander("📊 Raw Data"):
    st.dataframe(df)
