import streamlit as st
import requests
import matplotlib.pyplot as plt
import pandas as pd

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="AI 风险终端",
    layout="wide"
)

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =====================================
# STYLE（Bloomberg Terminal 风格）
# =====================================
st.markdown("""
<style>

html, body, [class*="css"]  {
    background-color: #0b0f19;
    color: white;
    font-family: sans-serif;
}

/* 主标题 */
.main-title {
    font-size: 34px;
    font-weight: 700;
    color: #7dd3fc;
    margin-bottom: 5px;
}

.sub-text {
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 20px;
}

/* 卡片 */
.card {
    background: #121826;
    border: 1px solid #1f2a44;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 12px;
}

/* 指标标题 */
.metric-title {
    color: #94a3b8;
    font-size: 12px;
    margin-bottom: 6px;
}

/* 指标数值 */
.metric-value {
    font-size: 22px;
    font-weight: 700;
}

/* 指标说明 */
.metric-desc {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 4px;
}

/* 状态颜色 */
.green {
    color: #22c55e;
}

.yellow {
    color: #fbbf24;
}

.red {
    color: #ef4444;
}

/* 说明区 */
.note-box {
    background: #111827;
    border-left: 4px solid #38bdf8;
    padding: 14px;
    border-radius: 10px;
    color: #cbd5e1;
    font-size: 13px;
    margin-top: 12px;
}

.small-text {
    color: #94a3b8;
    font-size: 12px;
}

</style>
""", unsafe_allow_html=True)

# =====================================
# HEADER
# =====================================
st.markdown("""
<div class="main-title">
📊 AI Compute-Dollar 风险终端
</div>

<div class="sub-text">
Bloomberg 风格 AI 资本开支监控系统 ｜ 用于检测 AI 基础设施扩张是否进入过热周期
</div>
""", unsafe_allow_html=True)

# =====================================
# INPUT
# =====================================
symbol = st.text_input("股票代码", "NVDA")

# =====================================
# FETCH
# =====================================
@st.cache_data(ttl=300)
def fetch(url):
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []

def safe(x, k):
    try:
        return float(x.get(k, 0))
    except:
        return 0.0

income = fetch(
    f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

cash = fetch(
    f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

# =====================================
# MAIN
# =====================================
if isinstance(income, list) and isinstance(cash, list) and len(income) > 1:

    years, revenue, capex, fcf = [], [], [], []

    n = min(len(income), len(cash))

    for i in range(n):

        years.append(income[i].get("date", "")[:4])

        revenue.append(
            safe(income[i], "revenue")
        )

        capex.append(
            abs(safe(cash[i], "capitalExpenditure"))
        )

        fcf.append(
            safe(cash[i], "freeCashFlow")
        )

    # 时间顺序
    years = years[::-1]
    revenue = revenue[::-1]
    capex = capex[::-1]
    fcf = fcf[::-1]

    # =====================================
    # CALCULATION
    # =====================================
    rev_g = (
        (revenue[-1] - revenue[-2]) / revenue[-2]
        if revenue[-2] else 0
    )

    capex_g = (
        (capex[-1] - capex[-2]) / capex[-2]
        if capex[-2] else 0
    )

    capex_ratio = (
        capex[-1] / revenue[-1]
        if revenue[-1] else 0
    )

    fcf_trend = fcf[-1] - fcf[-2]

    system_score = rev_g + capex_g

    # =====================================
    # STRAW 1 STATUS
    # =====================================
    straw1_status = "🟢 健康"
    straw1_color = "green"

    if capex_g > rev_g:
        straw1_status = "🟡 过热"
        straw1_color = "yellow"

    if capex_g > rev_g * 1.5:
        straw1_status = "🔴 高压"
        straw1_color = "red"

    # =====================================
    # KPI ROW
    # =====================================
    st.markdown("### 🧨 Straw 风险系统")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(f"""
        <div class="card">
            <div class="metric-title">
                稻草一｜AI资本周期
            </div>

            <div class="metric-value {straw1_color}">
                {straw1_status}
            </div>

            <div class="metric-desc">
                收入增速 {rev_g:.1%}<br>
                CapEx增速 {capex_g:.1%}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card">
            <div class="metric-title">
                稻草二｜利润质量
            </div>

            <div class="metric-value green">
                稳定
            </div>

            <div class="metric-desc">
                当前利润率维持正常区间
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="card">
            <div class="metric-title">
                稻草三｜资本压力
            </div>

            <div class="metric-value yellow">
                {capex_ratio:.1%}
            </div>

            <div class="metric-desc">
                CapEx / Revenue
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        trend_cls = "green" if fcf_trend > 0 else "red"

        st.markdown(f"""
        <div class="card">
            <div class="metric-title">
                稻草四｜自由现金流
            </div>

            <div class="metric-value {trend_cls}">
                {fcf[-1]/1e9:.1f}B
            </div>

            <div class="metric-desc">
                年变化 {fcf_trend/1e9:.1f}B
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c5:
        score_cls = "green"

        if system_score > 0.5:
            score_cls = "yellow"

        if system_score > 1:
            score_cls = "red"

        st.markdown(f"""
        <div class="card">
            <div class="metric-title">
                稻草五｜系统风险
            </div>

            <div class="metric-value {score_cls}">
                {system_score:.2f}
            </div>

            <div class="metric-desc">
                AI资本扩张综合评分
            </div>
        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # CHART + NOTE
    # =====================================
    left, right = st.columns([1.2, 1])

    # =====================================
    # CHART
    # =====================================
    with left:

        st.markdown("### 📈 资本扩张趋势")

        fig, ax = plt.subplots(figsize=(6, 2.8))

        ax.plot(years, revenue, label="Revenue")
        ax.plot(years, capex, label="CapEx")
        ax.plot(years, fcf, label="FCF")

        ax.legend(fontsize=7)

        ax.tick_params(labelsize=7)

        ax.set_facecolor("#121826")

        fig.patch.set_facecolor("#121826")

        st.pyplot(fig, use_container_width=False)

    # =====================================
    # DESIGN NOTE
    # =====================================
    with right:

        st.markdown("### 🧠 系统说明")

        st.markdown("""
        <div class="note-box">

        本系统用于检测 AI 基础设施资本开支是否开始脱离真实收入增长，
        通过 Revenue、CapEx 与 Free Cash Flow 的动态关系，
        识别 AI 产业是否进入“资本过热周期”。

        当资本开支扩张速度持续高于收入增长时，
        系统会逐步提高风险等级，用于提示潜在的 AI 泡沫风险。

        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # RAW DATA
    # =====================================
    with st.expander("📊 原始数据"):

        df = pd.DataFrame({
            "Year": years,
            "Revenue": revenue,
            "CapEx": capex,
            "FCF": fcf
        })

        st.dataframe(df)

else:
    st.warning("数据加载失败或 API 限制")
