import requests
import streamlit as st

# =====================
# CONFIG
# =====================
KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =====================
# DATA LAYER
# =====================
def fetch(endpoint):
    url = f"{BASE}/{endpoint}&apikey={KEY}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}
    except:
        return {}

# =====================
# STRAW 1 ENGINE
# =====================
def straw1(income, cash):
    revenue = income.get("revenue", 0)
    op_income = income.get("operatingIncome", 0)

    capex = abs(cash.get("capitalExpenditure", 0))
    ocf = cash.get("operatingCashFlow", 0)

    # 防除零
    capex_intensity = capex / ocf if ocf else 0
    op_margin = op_income / revenue if revenue else 0

    # risk scoring
    score = 0

    if capex_intensity > 0.35:
        score += 1
    if op_margin < 0.35:
        score += 1
    if revenue <= 0:
        score += 2

    if score == 0:
        status = "🟢 HEALTHY"
    elif score == 1:
        status = "🟡 WATCH"
    else:
        status = "🔴 OVERHEAT"

    return {
        "Revenue": revenue,
        "Operating Income": op_income,
        "CapEx": capex,
        "Operating Cash Flow": ocf,
        "CapEx Intensity": round(capex_intensity, 4),
        "Operating Margin": round(op_margin, 4),
        "Risk Score": score,
        "Status": status
    }

# =====================
# APP UI
# =====================
st.title("📊 AI Compute-Dollar Risk Terminal v1")

symbol = st.text_input("Symbol", "NVDA")

if st.button("Run Analysis"):

    income = fetch(f"income-statement?symbol={symbol}&limit=1")
    cash = fetch(f"cash-flow-statement?symbol={symbol}&limit=1")

    result = straw1(income, cash)

    st.subheader("🧨 Straw 1 Result")

    st.json(result)
