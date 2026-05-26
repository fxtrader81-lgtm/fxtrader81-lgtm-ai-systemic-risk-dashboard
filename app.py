import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

symbol = st.text_input("Symbol", "NVDA")

# =========================
# DATA FETCH
# =========================
def fetch(url):
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []

income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=8&apikey={API_KEY}")
cash = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=8&apikey={API_KEY}")

# =========================
# SAFE
# =========================
def safe(x, k):
    try:
        return float(x.get(k, 0))
    except:
        return 0.0


# =========================
# CSS (关键：看板风格)
# =========================
st.markdown("""
<style>

body {
    background-color: #0b1220;
}

.main {
    background-color: #0b1220;
}

.block-container {
    padding-top: 2rem;
}

.card {
    background: #111827;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #243244;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.metric-title {
    font-size: 13px;
    color: #9ca3af;
}

.metric-value {
    font-size: 26px;
    font-weight: 700;
}

.red { color: #ef4444; }
.green { color: #22c55e; }
.yellow { color: #fbbf24; }

.big-alert {
    padding: 18px;
    border-radius: 12px;
    background: linear-gradient(90deg, #1f2937, #111827);
    border: 1px solid #374151;
    margin-top: 10px;
}

.alert-title {
    font-size: 20px;
    font-weight: 700;
}

.small {
    font-size: 12px;
    color: #9ca3af;
}

</style>
""", unsafe_allow_html=True)


# =========================
# VALIDATION
# =========================
if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2:

    inc0, inc1 = income[0], income[1]
    cf0, cf1 = cash[0], cash[1]

    revenue = safe(inc0, "revenue")
    revenue_prev = safe(inc1, "revenue")

    capex = abs(safe(cf0, "capitalExpenditure"))
    capex_prev = abs(safe(cf1, "capitalExpenditure"))

    # =========================
    # METRICS
    # =========================
    rev_growth = (revenue - revenue_prev) / revenue_prev if revenue_prev else 0
    capex_growth = (capex - capex_prev) / capex_prev if capex_prev else 0

    threshold = rev_growth * 1.2
    overheat = capex_growth > threshold

    # =========================
    # HEADER
    # =========================
    st.title(f"📊 AI Compute-Dollar Risk Terminal — {symbol}")

    # =========================
    # KPI ROW (像你图里的卡片)
    # =========================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="metric-title">收入增长率 (YoY)</div>
            <div class="metric-value green">{rev_growth*100:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="card">
            <div class="metric-title">资本开支增长率</div>
            <div class="metric-value red">{capex_growth*100:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        diff = (capex_growth - rev_growth) * 100
        st.markdown(f"""
        <div class="card">
            <div class="metric-title">增速差 (CapEx - Revenue)</div>
            <div class="metric-value yellow">{diff:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        status = "过热预警" if overheat else "正常"
        color = "red" if overheat else "green"

        st.markdown(f"""
        <div class="card">
            <div class="metric-title">状态判断</div>
            <div class="metric-value {color}">{status}</div>
        </div>
        """, unsafe_allow_html=True)

    # =========================
    # BIG ALERT（中间大横幅）
    # =========================
    if overheat:
        alert_text = "⚠️ AI资本开支扩张速度明显高于收入增长，进入过热阶段"
        alert_color = "red"
    else:
        alert_text = "✅ 当前资本扩张仍由收入增长支撑，结构健康"
        alert_color = "green"

    st.markdown(f"""
    <div class="big-alert">
        <div class="alert-title {alert_color}">结论：{status}</div>
        <div style="margin-top:8px;">{alert_text}</div>
        <div class="small">规则：CapEx增长 > 收入增长 × 1.2 → 过热信号</div>
    </div>
    """, unsafe_allow_html=True)

    # =========================
    # LAYOUT: LEFT TEXT + RIGHT CHART
    # =========================
    left, right = st.columns([1, 1])

    with left:
        st.subheader("🧠 检测逻辑")

        st.markdown(f"""
        <div class="card">
        1️⃣ 获取收入 & 资本开支数据<br>
        2️⃣ 计算 YoY 增速<br>
        3️⃣ 计算增速差：CapEx - Revenue<br>
        4️⃣ 判断是否超过阈值（×1.2）<br><br>

        <b>当前计算：</b><br>
        收入增长：{rev_growth*100:.2f}%<br>
        CapEx增长：{capex_growth*100:.2f}%<br>
        阈值：{threshold*100:.2f}%
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.subheader("📈 趋势对比")

        # build mini trend from list
        rev_series = [safe(x, "revenue") for x in income[:6]][::-1]
        capex_series = [abs(safe(x, "capitalExpenditure")) for x in cash[:6]][::-1]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            y=rev_series,
            name="Revenue",
            line=dict(color="green")
        ))

        fig.add_trace(go.Scatter(
            y=capex_series,
            name="CapEx",
            line=dict(color="red")
        ))

        fig.update_layout(
            paper_bgcolor="#0b1220",
            plot_bgcolor="#0b1220",
            font=dict(color="white"),
            height=420,
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

else:
    st.error("API数据不足或请求失败")
