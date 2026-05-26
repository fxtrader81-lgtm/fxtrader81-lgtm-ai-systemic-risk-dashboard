import streamlit as st
import requests
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 AI Compute-Dollar Risk Terminal v9")

# ======================
# CONFIG
# ======================
API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

symbol = st.text_input("Symbol", "NVDA")


# ======================
# SAFE FETCH
# ======================
def fetch(url):
    r = requests.get(url)
    try:
        return r.json()
    except:
        return []


# ======================
# DATA LAYER
# ======================
def get_data(symbol):
    income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}")
    cash = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}")
    return income, cash


# ======================
# SAFE GET
# ======================
def safe(x, key):
    try:
        return float(x[key])
    except:
        return 0.0


# ======================
# STRAW ENGINE
# ======================
def compute_straws(income, cash):

    years = []
    revenue = []
    op_income = []
    capex = []
    fcf = []

    n = min(len(income), len(cash))

    for i in range(n):
        years.append(income[i].get("date", "")[:4])
        revenue.append(safe(income[i], "revenue"))
        op_income.append(safe(income[i], "operatingIncome"))
        capex.append(abs(safe(cash[i], "capitalExpenditure")))
        fcf.append(safe(cash[i], "freeCashFlow"))

    years = years[::-1]
    revenue = revenue[::-1]
    op_income = op_income[::-1]
    capex = capex[::-1]
    fcf = fcf[::-1]

    # ======================
    # STRAW 1: AI CAPEX CYCLE
    # ======================
    rev_g = (revenue[-1] - revenue[-2]) / revenue[-2] if revenue[-2] else 0
    capex_g = (capex[-1] - capex[-2]) / capex[-2] if capex[-2] else 0

    straw1 = {
        "Revenue": revenue[-1],
        "CapEx": capex[-1],
        "Revenue Growth": rev_g,
        "CapEx Growth": capex_g,
        "Status": "🟢 HEALTHY"
    }

    if capex_g > rev_g:
        straw1["Status"] = "🟡 OVERHEAT"
    if capex_g > rev_g * 1.5:
        straw1["Status"] = "🔴 STRESS"

    # ======================
    # STRAW 2: MARGIN PRESSURE
    # ======================
    margin = op_income[-1] / revenue[-1] if revenue[-1] else 0

    straw2 = {
        "Operating Margin": margin,
        "Status": "🟢 OK" if margin > 0.2 else "🟡 WEAK"
    }

    # ======================
    # STRAW 3: CAPEX BURDEN
    # ======================
    capex_ratio = capex[-1] / revenue[-1] if revenue[-1] else 0

    straw3 = {
        "CapEx Ratio": capex_ratio,
        "Status": "🟢 OK" if capex_ratio < 0.1 else "🟡 HEAVY"
    }

    # ======================
    # STRAW 4: CASH FLOW QUALITY
    # ======================
    fcf_trend = fcf[-1] - fcf[-2]

    straw4 = {
        "FCF": fcf[-1],
        "FCF Trend": fcf_trend,
        "Status": "🟢 STRONG" if fcf_trend > 0 else "🟡 WEAK"
    }

    # ======================
    # STRAW 5: SYSTEM MOMENTUM
    # ======================
    system_score = (rev_g + capex_g + margin + capex_ratio)

    straw5 = {
        "System Score": system_score,
        "Status": "🟢 STABLE"
    }

    return years, revenue, capex, fcf, {
        "Straw 1": straw1,
        "Straw 2": straw2,
        "Straw 3": straw3,
        "Straw 4": straw4,
        "Straw 5": straw5
    }


# ======================
# UI
# ======================
if st.button("Analyze"):

    income, cash = get_data(symbol)

    if not isinstance(income, list) or not isinstance(cash, list):
        st.error("API failed")
        st.json({"income": income, "cash": cash})
        st.stop()

    years, revenue, capex, fcf, straws = compute_straws(income, cash)

    # ======================
    # CHART
    # ======================
    st.subheader("📈 Multi-Year Trend")

    fig, ax = plt.subplots()
    ax.plot(years, revenue, label="Revenue")
    ax.plot(years, capex, label="CapEx")
    ax.plot(years, fcf, label="FCF")
    ax.legend()

    st.pyplot(fig)

    # ======================
    # STRAWS
    # ======================
    st.subheader("🧨 Straw System")

    st.json(straws)
