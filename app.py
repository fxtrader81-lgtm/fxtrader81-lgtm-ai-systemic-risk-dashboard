import streamlit as st
import requests

# =========================
# CONFIG
# =========================
st.set_page_config(layout="centered")
st.title("📊 AI Compute-Dollar Risk Terminal v12")

# ⚠️ API KEY（已写死）
API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

symbol = st.text_input("Symbol", "NVDA")


# =========================
# SAFE REQUEST
# =========================
def fetch(url):
    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except:
        return []


def safe(x, k):
    try:
        v = x.get(k, 0)
        return float(v) if v is not None else 0.0
    except:
        return 0.0


def safe_div(a, b):
    return a / b if b else 0.0


# =========================
# DATA
# =========================
income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=3&apikey={API_KEY}")
cash = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=3&apikey={API_KEY}")


# =========================
# VALIDATION
# =========================
if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2 and len(cash) >= 2:

    inc0, inc1 = income[0], income[1]
    cf0, cf1 = cash[0], cash[1]

    revenue = safe(inc0, "revenue")
    revenue_prev = safe(inc1, "revenue")

    capex = abs(safe(cf0, "capitalExpenditure"))
    capex_prev = abs(safe(cf1, "capitalExpenditure"))

    fcf = safe(cf0, "freeCashFlow")
    fcf_prev = safe(cf1, "freeCashFlow")

    # =========================
    # STRAW 1 - AI CAPITAL CYCLE
    # =========================
    rev_growth = safe_div(revenue - revenue_prev, revenue_prev)
    capex_growth = safe_div(capex - capex_prev, capex_prev)

    if capex_growth > rev_growth * 1.2:
        straw1 = "🟡 OVERHEAT"
        straw1_msg = "资本开支明显跑赢收入增长"
    elif capex_growth > rev_growth:
        straw1 = "🟠 WARNING"
        straw1_msg = "资本扩张领先收入"
    else:
        straw1 = "🟢 HEALTHY"
        straw1_msg = "收入支撑资本扩张"


    # =========================
    # STRAW 2 - PROFIT QUALITY
    # =========================
    margin = safe_div(safe(inc0, "operatingIncome"), revenue)

    if margin > 0.25:
        straw2 = "🟢 OK"
        straw2_msg = "盈利能力健康"
    else:
        straw2 = "🟡 WEAK"
        straw2_msg = "利润承压"


    # =========================
    # STRAW 3 - CAPEX BURDEN
    # =========================
    capex_ratio = safe_div(capex, revenue)

    if capex_ratio < 0.05:
        straw3 = "🟢 OK"
        straw3_msg = "资本开支正常"
    else:
        straw3 = "🟡 HIGH"
        straw3_msg = "资本开支偏重"


    # =========================
    # STRAW 4 - CASH FLOW
    # =========================
    fcf_trend = fcf - fcf_prev

    if fcf_trend > 0:
        straw4 = "🟢 STRONG"
        straw4_msg = "现金流改善"
    else:
        straw4 = "🟡 WEAK"
        straw4_msg = "现金流下降"


    # =========================
    # STRAW 5 - SYSTEM RISK
    # =========================
    system_score = rev_growth + (0.5 * capex_growth)

    if system_score > 0.8:
        straw5 = "🔴 RISK"
        straw5_msg = "高波动扩张阶段"
    elif system_score > 0.3:
        straw5 = "🟡 WATCH"
        straw5_msg = "结构性风险上升"
    else:
        straw5 = "🟢 STABLE"
        straw5_msg = "系统稳定"


    # =========================
    # UI
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
