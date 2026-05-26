import streamlit as st
import requests

st.set_page_config(layout="centered")

st.title("📊 AI Compute-Dollar Risk Terminal v12")

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


income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=3&apikey={API_KEY}")
cash = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=3&apikey={API_KEY}")


if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2:

    inc0, inc1 = income[0], income[1]
    cf0, cf1 = cash[0], cash[1]

    revenue = safe(inc0, "revenue")
    revenue_prev = safe(inc1, "revenue")

    capex = abs(safe(cf0, "capitalExpenditure"))
    capex_prev = abs(safe(cf1, "capitalExpenditure"))

    fcf = safe(cf0, "freeCashFlow")
    fcf_prev = safe(cf1, "freeCashFlow")

    # =========================
    # STRAW 1 — 核心判断
    # =========================
    rev_growth = (revenue - revenue_prev) / revenue_prev if revenue_prev else 0
    capex_growth = (capex - capex_prev) / capex_prev if capex_prev else 0

    if capex_growth > rev_growth * 1.2:
        straw1 = "🟡 OVERHEAT（资本开支跑赢收入）"
        straw1_msg = "AI资本扩张 > 真实需求增长，进入过热阶段"
    elif capex_growth > rev_growth:
        straw1 = "🟠 WARNING（轻度偏离）"
        straw1_msg = "资本扩张开始领先收入，但尚未失衡"
    else:
        straw1 = "🟢 HEALTHY（良性扩张）"
        straw1_msg = "收入增长仍能支撑资本开支"

    # =========================
    # STRAW 2 — 利润质量
    # =========================
    margin = safe(inc0, "operatingIncome") / revenue if revenue else 0

    straw2 = "🟢 OK" if margin > 0.25 else "🟡 WEAK"
    straw2_msg = "盈利能力稳定" if margin > 0.25 else "利润率压力出现"

    # =========================
    # STRAW 3 — CapEx 压力
    # =========================
    capex_ratio = capex / revenue if revenue else 0

    straw3 = "🟢 OK" if capex_ratio < 0.05 else "🟡 HIGH"
    straw3_msg = "资本开支可控" if capex_ratio < 0.05 else "资本开支偏重"

    # =========================
    # STRAW 4 — 现金流
    # =========================
    fcf_trend = fcf - fcf_prev

    straw4 = "🟢 STRONG" if fcf_trend > 0 else "🟡 WEAK"
    straw4_msg = "现金流改善" if fcf_trend > 0 else "现金流走弱"

    # =========================
    # STRAW 5 — 系统风险
    # =========================
    system_score = rev_growth + (0.5 * capex_growth)

    if system_score > 0.8:
        straw5 = "🔴 RISK"
        straw5_msg = "系统进入高波动扩张阶段"
    elif system_score > 0.3:
        straw5 = "🟡 WATCH"
        straw5_msg = "结构性风险上升"
    else:
        straw5 = "🟢 STABLE"
        straw5_msg = "系统稳定"

    # =========================
    # UI（只显示结论）
    # =========================

    st.subheader("🧨 Straw 1 - AI Capital Cycle")
    st.metric(straw1, straw1_msg)

    st.subheader("🧨 Straw 2 - Profit Quality")
    st.metric(straw2, straw2_msg)

    st.subheader("🧨 Straw 3 - CapEx Pressure")
    st.metric(straw3, straw3_msg)

    st.subheader("🧨 Straw 4 - Cash Flow")
    st.metric(straw4, straw4_msg)

    st.subheader("🧨 Straw 5 - System Risk")
    st.metric(straw5, straw5_msg)

else:
    st.error("API数据不足或请求失败")
