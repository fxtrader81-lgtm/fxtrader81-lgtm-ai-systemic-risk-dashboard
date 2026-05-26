import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("📊 AI Compute-Dollar Risk Terminal v13 (Visual Edition)")

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

symbol = st.text_input("Symbol", "NVDA")


# =========================
# FETCH
# =========================
def fetch(url):
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []


income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=8&apikey={API_KEY}")
cash = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=8&apikey={API_KEY}")


# =========================
# VALIDATE
# =========================
if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2 and len(cash) >= 2:

    # =========================
    # BUILD DATAFRAME
    # =========================
    rev_list = []
    capex_list = []
    fcf_list = []
    dates = []

    for i in range(min(len(income), len(cash))):
        inc = income[i]
        cf = cash[i]

        rev = inc.get("revenue", 0)
        capex = abs(cf.get("capitalExpenditure", 0))
        fcf = cf.get("freeCashFlow", 0)
        date = inc.get("date", str(i))

        rev_list.append(rev)
        capex_list.append(capex)
        fcf_list.append(fcf)
        dates.append(date)

    df = pd.DataFrame({
        "date": dates,
        "revenue": rev_list,
        "capex": capex_list,
        "fcf": fcf_list
    })

    df = df[::-1]  # chronological order

    # =========================
    # DERIVED METRICS
    # =========================
    df["rev_growth"] = df["revenue"].pct_change()
    df["capex_growth"] = df["capex"].pct_change()
    df["capex_ratio"] = df["capex"] / df["revenue"]

    df["risk_score"] = df["capex_growth"] - df["rev_growth"]

    # =========================
    # LAYOUT
    # =========================
    col1, col2 = st.columns(2)

    # =========================
    # CHART 1 - Revenue vs CapEx
    # =========================
    with col1:
        st.subheader("📈 Revenue vs CapEx")

        fig, ax = plt.subplots()
        ax.plot(df["date"], df["revenue"], label="Revenue")
        ax.plot(df["date"], df["capex"], label="CapEx")
        ax.legend()
        ax.set_xticklabels(df["date"], rotation=45)
        st.pyplot(fig)

    # =========================
    # CHART 2 - Growth Rate
    # =========================
    with col2:
        st.subheader("📊 Growth Rate")

        fig2, ax2 = plt.subplots()
        ax2.plot(df["date"], df["rev_growth"], label="Revenue Growth")
        ax2.plot(df["date"], df["capex_growth"], label="CapEx Growth")
        ax2.legend()
        ax2.set_xticklabels(df["date"], rotation=45)
        st.pyplot(fig2)

    # =========================
    # CHART 3 - Risk Curve
    # =========================
    st.subheader("🧨 Risk Curve (CapEx - Revenue Growth)")

    fig3, ax3 = plt.subplots()
    ax3.plot(df["date"], df["risk_score"], color="red")
    ax3.axhline(0, linestyle="--")
    ax3.set_xticklabels(df["date"], rotation=45)
    st.pyplot(fig3)

    # =========================
    # TABLE
    # =========================
    st.subheader("📊 Raw Data Table")
    st.dataframe(df)

else:
    st.error("数据不足或API失败")
