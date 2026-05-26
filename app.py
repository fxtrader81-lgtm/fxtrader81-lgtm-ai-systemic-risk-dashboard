import streamlit as st
import requests
import matplotlib.pyplot as plt

st.title("📊 AI Compute-Dollar Risk Terminal v1")

# 👉 只改这里：填你的 key
KEY = st.text_input("Enter FMP Key", "")

symbol = st.text_input("Symbol", "NVDA")


BASE = "https://financialmodelingprep.com/api/v3"


def fetch_income(symbol):
    url = f"{BASE}/income-statement/{symbol}?limit=5&apikey={KEY}"
    return requests.get(url).json()


def fetch_cash(symbol):
    url = f"{BASE}/cash-flow-statement/{symbol}?limit=5&apikey={KEY}"
    return requests.get(url).json()


if st.button("Run Analysis"):

    if not KEY:
        st.error("请先输入API Key")
        st.stop()

    income = fetch_income(symbol)
    cash = fetch_cash(symbol)

    if not isinstance(income, list) or not isinstance(cash, list):
        st.error("API返回异常：Key或权限问题")
        st.json(income)
        st.stop()

    if len(income) < 2 or len(cash) < 2:
        st.error("数据不足")
        st.stop()

    years = []
    revenue = []
    capex = []

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
