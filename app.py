import streamlit as st
import requests
import matplotlib.pyplot as plt

st.title("📊 AI Compute-Dollar Risk Terminal v1")

symbol = st.text_input("Symbol", "NVDA")
KEY = st.text_input("FMP Key", "")

BASE = "https://financialmodelingprep.com/api/v3"


def fetch(url):
    r = requests.get(url)
    try:
        return r.json()
    except:
        return {"error": "invalid response", "text": r.text}


if st.button("Run Analysis"):

    if not KEY:
        st.error("请输入API Key")
        st.stop()

    income_url = f"{BASE}/income-statement/{symbol}?limit=5&apikey={KEY}"
    cash_url = f"{BASE}/cash-flow-statement/{symbol}?limit=5&apikey={KEY}"

    income = fetch(income_url)
    cash = fetch(cash_url)

    # 🚨 强制显示API返回（关键）
    st.subheader("📡 Raw Income API Response")
    st.json(income)

    st.subheader("📡 Raw CashFlow API Response")
    st.json(cash)

    if not isinstance(income, list) or not isinstance(cash, list):
        st.error("API失败：请看上方返回内容（不是代码问题，是API权限/endpoint）")
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
