import streamlit as st
import requests
import matplotlib.pyplot as plt

# ========== CONFIG ==========
KEY = "你的FMP_API_KEY"   # ← 只改这一行
BASE = "https://financialmodelingprep.com/stable"

st.title("📊 AI Compute-Dollar Risk Terminal v1")

symbol = st.text_input("Symbol", "NVDA")


# ========== DATA ==========
def fetch_income(symbol):
    url = f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={KEY}"
    return requests.get(url).json()

def fetch_cash(symbol):
    url = f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={KEY}"
    return requests.get(url).json()


# ========== RUN ==========
if st.button("Run Analysis"):

    income = fetch_income(symbol)
    cash = fetch_cash(symbol)

    if not isinstance(income, list) or not isinstance(cash, list):
        st.error("API返回错误，请检查Key或权限")
        st.stop()

    if len(income) < 2 or len(cash) < 2:
        st.error("数据不足（至少需要2年数据）")
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

    # ========== CHART ==========
    st.subheader("📈 Revenue vs CapEx Trend")

    fig, ax = plt.subplots()
    ax.plot(years, revenue, label="Revenue")
    ax.plot(years, capex, label="CapEx")
    ax.legend()

    st.pyplot(fig)

    # ========== STRAW 1 ==========
    st.subheader("🧨 Straw 1 Signal")

    revenue_growth = (revenue[-1] - revenue[-2]) / revenue[-2]
    capex_growth = (capex[-1] - capex[-2]) / capex[-2]

    score = 0
    status = "🟢 HEALTHY"

    if capex_growth > revenue_growth:
        score += 1
    if capex_growth > revenue_growth * 1.5:
        score += 1

    if score == 1:
        status = "🟡 WATCH"
    if score >= 2:
        status = "🔴 OVERHEAT"

    st.json({
        "symbol": symbol,
        "Revenue": revenue[-1],
        "CapEx": capex[-1],
        "Revenue Growth": round(revenue_growth, 4),
        "CapEx Growth": round(capex_growth, 4),
        "Risk Score": score,
        "Status": status
    })
