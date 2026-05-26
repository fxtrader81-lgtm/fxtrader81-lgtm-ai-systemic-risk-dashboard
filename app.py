import streamlit as st
import requests

st.set_page_config(page_title="AI Risk Terminal", layout="wide")

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =========================
# 🎨 UI STYLE（金融终端风）
# =========================
st.markdown("""
<style>
body {
    background-color: #0b0f19;
    color: #ffffff;
}

.block {
    background: #121a2a;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
    border: 1px solid #1f2a44;
}

.title {
    font-size: 20px;
    font-weight: 600;
    color: #7dd3fc;
}

.metric {
    font-size: 16px;
    margin-top: 6px;
    color: #e5e7eb;
}

.good { color: #22c55e; }
.warn { color: #fbbf24; }
.bad  { color: #ef4444; }

.small {
    font-size: 13px;
    color: #94a3b8;
}
</style>
""", unsafe_allow_html=True)


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


income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=2&apikey={API_KEY}")
cash = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=2&apikey={API_KEY}")


if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2:

    inc0, inc1 = income[0], income[1]
    cf0, cf1 = cash[0], cash[1]

    revenue = safe(inc0, "revenue")
    revenue_prev = safe(inc1, "revenue")

    capex = abs(safe(cf0, "capitalExpenditure"))
    capex_prev = abs(safe(cf1, "capitalExpenditure"))

    # =========================
    # 🧨 Straw 1 核心逻辑
    # =========================
    rev_growth = (revenue - revenue_prev) / revenue_prev if revenue_prev else 0
    capex_growth = (capex - capex_prev) / capex_prev if capex_prev else 0

    # 判断逻辑（核心）
    # CapEx 增速 > 收入增速 => 资本过热
    if capex_growth > rev_growth * 1.2:
        status = "🟡 过热风险"
        cls = "warn"
        desc = "资本开支扩张速度明显高于收入增长，进入过热阶段"
    elif capex_growth > rev_growth:
        status = "🟠 偏热"
        cls = "warn"
        desc = "资本扩张开始领先收入增长，但尚未失衡"
    else:
        status = "🟢 健康"
        cls = "good"
        desc = "收入增长仍能覆盖资本开支扩张"

    # =========================
    # 🧨 UI 卡片
    # =========================
    st.markdown(f"""
    <div class="block">
        <div class="title">🧨 稻草一：AI资本开支循环检测</div>

        <div class="metric">
            当前状态：<b class="{cls}">{status}</b>
        </div>

        <div class="metric">
            核心判断：{desc}
        </div>

        <div class="small">
            逻辑：当资本开支增速 > 收入增速 × 1.2 时，判定为资本过热信号
        </div>

        <div class="small">
            收入增速：{rev_growth:.2%} ｜ CapEx增速：{capex_growth:.2%}
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    st.error("数据加载失败")
