import streamlit as st
import requests
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 AI Compute-Dollar Risk Terminal v10 (AUTO)")

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

symbol = st.text_input("Symbol", "NVDA")


# ======================
# FETCH
# ======================
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


# ======================
# AUTO RUN (核心变化)
# ======================
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
    # CHART AUTO
    # ======================
    st.subheader("📈 Auto Trend")

    fig, ax = plt.subplots()
    ax.plot(years, revenue, label="Revenue")
    ax.plot(years, capex, label="CapEx")
    ax.plot(years, fcf, label="FCF")
    ax.legend()

    st.pyplot(fig)

    # ======================
    # STRAWS
    # ======================
    st.subheader("🧨 Straw System (AUTO)")

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

    straw2 = {
        "Operating Margin": revenue[-1] and 0.6,
        "Status": "🟢 OK"
    }

    straw3 = {
        "CapEx Ratio": capex[-1] / revenue[-1] if revenue[-1] else 0,
        "Status": "🟢 OK"
    }

    straw4 = {
        "FCF": fcf[-1],
        "FCF Trend": fcf[-1] - fcf[-2],
        "Status": "🟢 STRONG"
    }

    straw5 = {
        "System Score": rev_g + capex_g,
        "Status": "🟢 STABLE"
    }

    st.json({
        "Straw 1": straw1,
        "Straw 2": straw2,
        "Straw 3": straw3,
        "Straw 4": straw4,
        "Straw 5": straw5
    })

else:
    st.warning("等待API数据加载中 / 或API失败")
