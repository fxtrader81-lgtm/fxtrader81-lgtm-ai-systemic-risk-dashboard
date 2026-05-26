import streamlit as st
import requests
import matplotlib.pyplot as plt

# ========== 配置 ==========
KEY = "你的FMP_API_KEY"   # ← 把这里换成你的key
symbol = st.text_input("Symbol", "NVDA")

# ========== 数据获取 ==========
def fetch_income(symbol):
    url = f"https://financialmodelingprep.com/stable/income-statement?symbol={symbol}&limit=5&apikey={KEY}"
    return requests.get(url).json()

def fetch_cash(symbol):
    url = f"https://financialmodelingprep.com/stable/cash-flow-statement?symbol={symbol}&limit=5&apikey={KEY}"
    return requests.get(url).json()

# ========== 主逻辑 ==========
if st.button("Run Analysis"):

    income = fetch_income(symbol)
    cash = fetch_cash(symbol)

    if not income or not cash:
        st.error("API没有返回数据，请检查KEY或权限")
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

    st.subheader("📊 Revenue vs CapEx Trend")

    fig, ax = plt.subplots()
    ax.plot(years, revenue, label="Revenue")
    ax.plot(years, capex, label="CapEx")

    ax.legend()
    st.pyplot(fig)

    # ========== 稻草1基础指标 ==========
    st.subheader("🧨 Straw 1 Snapshot")

    capex_growth = (capex[-1] - capex[-2]) / capex[-2]
    revenue_growth = (revenue[-1] - revenue[-2]) / revenue[-2]

    risk = "🟢 HEALTHY"

    if capex_growth > revenue_growth:
        risk = "🟡 OVERHEATING"
    if capex_growth > revenue_growth * 1.5:
        risk = "🔴 STRESS"

    st.json({
        "Revenue": revenue[-1],
        "CapEx": capex[-1],
        "Revenue Growth": round(revenue_growth, 4),
        "CapEx Growth": round(capex_growth, 4),
        "Status": risk
    })
