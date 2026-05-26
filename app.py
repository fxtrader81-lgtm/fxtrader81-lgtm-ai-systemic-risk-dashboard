import streamlit as st
import requests
import matplotlib.pyplot as plt

st.title("📊 AI Compute-Dollar Risk Terminal v1")

# ✅ 直接写死你的 key（不再输入）
KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"

symbol = st.text_input("Symbol", "NVDA")

BASE = "https://financialmodelingprep.com/api/v3"


def fetch(url):
    r = requests.get(url)
    try:
        return r.json()
    except:
        return {"error": "invalid response", "text": r.text}


if st.button("Run Analysis"):

    income_url = f"{BASE}/income-statement/{symbol}?limit=5&apikey={KEY}"
    cash_url = f"{BASE}/cash-flow-statement/{symbol}?limit=5&apikey={KEY}"

    income = fetch(income_url)
    cash = fetch(cash_url)

    # 🚨 如果API失败，直接暴露
    if not isinstance(income, list):
        st.error("Income API失败")
        st.json(income)
        st.stop()

    if not isinstance(cash, list):
        st.error("Cashflow API失败")
        st.json(cash)
        st.stop()

    years, revenue, capex = [], [], []

    for i in range(len(income)):
        years.append(income[i]["date"][:4])
        revenue.append(income[i]["revenue"])
        capex.append(abs(cash[i]["capitalExpenditure"]))

    years = years[::-1]
    revenue = revenue[::-1]
    capex = capex[::-1]

    st.subheader("📈 Trend")

    fig, ax = plt.subplots()
    ax.plot(years, revenue, label="Revenue")
    ax.plot(years, capex, label="CapEx")
    ax.legend()

    st.pyplot(fig)

    st.subheader("🧨 Straw 1")

    rev_g = (revenue[-1] - revenue[-2]) / revenue[-2]
    capex_g = (capex[-1] - capex[-2]) / capex[-2]

    status = "🟢 HEALTHY"
    if capex_g > rev_g:
        status = "🟡 OVERHEAT"
    if capex_g > rev_g * 1.5:
        status = "🔴 STRESS"

    st.json({
        "Revenue": revenue[-1],
        "CapEx": capex[-1],
        "Revenue Growth": rev_g,
        "CapEx Growth": capex_g,
        "Status": status
    })
