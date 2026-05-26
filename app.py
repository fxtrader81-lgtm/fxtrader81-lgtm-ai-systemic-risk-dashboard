import streamlit as st
import requests
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("📊 AI Compute-Dollar Risk Dashboard v11")

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

symbol = st.text_input("Symbol", "NVDA")


def fetch(url):
    try:
        return requests.get(url).json()
    except:
        return []


def safe(x, k):
    try:
        return float(x.get(k, 0))
    except:
        return 0.0


income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}")
cash = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}")

if isinstance(income, list) and isinstance(cash, list) and len(income) > 1:

    years, revenue, capex, fcf = [], [], [], []

    n = min(len(income), len(cash))

    for i in range(n):
        years.append(income[i].get("date", "")[:4])
        revenue.append(safe(income[i], "revenue"))
        capex.append(abs(safe(cash[i], "capitalExpenditure")))
        fcf.append(safe(cash[i], "freeCashFlow"))

    years = years[::-1]
    revenue = revenue[::-1]
    capex = capex[::-1]
    fcf = fcf[::-1]

    # ======================
    # CHART (缩小版)
    # ======================
    st.subheader("📈 Trend")

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(years, revenue, label="Revenue")
    ax.plot(years, capex, label="CapEx")
    ax.plot(years, fcf, label="FCF")
    ax.legend(fontsize=8)
    ax.tick_params(labelsize=8)

    st.pyplot(fig, use_container_width=False)

    # ======================
    # STRAW ENGINE
    # ======================
    rev_g = (revenue[-1] - revenue[-2]) / revenue[-2] if revenue[-2] else 0
    capex_g = (capex[-1] - capex[-2]) / capex[-2] if capex[-2] else 0

    straw1_status = "🟢 HEALTHY"
    if capex_g > rev_g:
        straw1_status = "🟡 OVERHEAT"
    if capex_g > rev_g * 1.5:
        straw1_status = "🔴 STRESS"

    margin = 0.6
    capex_ratio = capex[-1] / revenue[-1] if revenue[-1] else 0
    fcf_trend = fcf[-1] - fcf[-2]
    system_score = rev_g + capex_g

    # ======================
    # DASHBOARD UI
    # ======================
    st.subheader("🧨 Straw System Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Straw 1 - AI CapEx Cycle", straw1_status, f"RevG {rev_g:.2%} | CapExG {capex_g:.2%}")

    with col2:
        st.metric("Straw 2 - Margin", f"{margin:.2f}", "OK")

    with col3:
        st.metric("Straw 3 - CapEx Ratio", f"{capex_ratio:.2%}", "OK")

    col4, col5 = st.columns(2)

    with col4:
        st.metric("Straw 4 - FCF", f"{fcf[-1]:,.0f}", f"{fcf_trend:,.0f}")

    with col5:
        st.metric("Straw 5 - System Score", f"{system_score:.2f}", "STABLE")

else:
    st.warning("Loading data or API error")
