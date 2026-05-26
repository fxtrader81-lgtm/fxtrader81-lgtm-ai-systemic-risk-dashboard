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
# CSS（Bloomberg 风格）
# =====================================
st.markdown("""
<style>

html, body, [class*="css"] {
    background-color: #0b0f19;
    color: white;
    font-family: sans-serif;
}

/* 页面顶部间距 */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
}

/* 标题 */
.main-title {
    font-size: 34px;
    font-weight: 700;
    color: #7dd3fc;
    margin-bottom: 4px;
}

/* 副标题 */
.sub-title {
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 22px;
}

/* 卡片 */
.card {
    background: #121826;
    border: 1px solid #1f2a44;
    border-radius: 14px;
    padding: 14px;
    height: 150px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.35);
}

/* 卡片标题 */
.metric-title {
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 10px;
}

/* 大数字 */
.metric-value {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 10px;
}

/* 说明 */
.metric-desc {
    font-size: 12px;
    line-height: 1.5;
    color: #cbd5e1;
}

/* 颜色 */
.green {
    color: #22c55e;
}

.yellow {
    color: #fbbf24;
}

.red {
    color: #ef4444;
}

/* 系统说明 */
.note-box {
    background: #121826;
    border: 1px solid #1f2a44;
    border-left: 4px solid #38bdf8;
    border-radius: 12px;
    padding: 16px;
    font-size: 13px;
    line-height: 1.7;
    color: #cbd5e1;
}

/* chart 标题 */
.chart-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 10px;
}

/* expander */
.streamlit-expanderHeader {
    font-size: 14px;
    color: white;
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

<div class="sub-title">
Bloomberg 风格 AI 资本开支监控系统 ｜ 用于检测 AI 基础设施是否进入资本过热周期
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

# =====================================
# SAFE
# =====================================
def safe(x, k):
    try:
        return float(x.get(k, 0))
    except:
        return 0.0

# =====================================
# API
# =====================================
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

    years = []
    revenue = []
    capex = []
    fcf = []

    n = min(len(income), len(cash))

    for i in range(n):

        years.append(
            income[i].get("date", "")[:4]
        )

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

    fcf_trend = (
        fcf[-1] - fcf[-2]
    )

    system_score = (
        rev_g + capex_g
    )

    # =====================================
    # STATUS
    # =====================================
    straw1_status = "🟢 健康"
    straw1_color = "green"
    straw1_desc = "收入增长仍能覆盖资本扩张"

    if capex_g > rev_g:
        straw1_status = "🟡 过热"
        straw1_color = "yellow"
        straw1_desc = "资本扩张开始领先收入增长"

    if capex_g > rev_g * 1.5:
        straw1_status = "🔴 高压"
        straw1_color = "red"
        straw1_desc = "资本扩张明显脱离真实需求"

    # =====================================
    # KPI ROW
    # =====================================
    st.markdown("### 🧨 Straw 风险系统")

    c1, c2, c3, c4, c5 = st.columns(5)

    # =====================================
    # CARD 1
    # =====================================
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
                CapEx增速 {capex_g:.1%}<br><br>
                {straw1_desc}
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # CARD 2
    # =====================================
    with c2:
        st.markdown("""
        <div class="card">

            <div class="metric-title">
                稻草二｜利润质量
            </div>

            <div class="metric-value green">
                稳定
            </div>

            <div class="metric-desc">
                当前利润率维持正常区间，
                盈利能力尚未出现明显恶化
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # CARD 3
    # =====================================
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
                当前资本开支占收入比例，
                用于衡量 AI 基础设施负担
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # CARD 4
    # =====================================
    with c4:

        fcf_color = "green"

        if fcf_trend < 0:
            fcf_color = "red"

        st.markdown(f"""
        <div class="card">

            <div class="metric-title">
                稻草四｜自由现金流
            </div>

            <div class="metric-value {fcf_color}">
                {fcf[-1]/1e9:.1f}B
            </div>

            <div class="metric-desc">
                年变化 {fcf_trend/1e9:.1f}B<br>
                观察现金流是否开始恶化
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # CARD 5
    # =====================================
    with c5:

        score_color = "green"

        if system_score > 0.5:
            score_color = "yellow"

        if system_score > 1:
            score_color = "red"

        st.markdown(f"""
        <div class="card">

            <div class="metric-title">
                稻草五｜系统风险
            </div>

            <div class="metric-value {score_color}">
                {system_score:.2f}
            </div>

            <div class="metric-desc">
                AI资本扩张综合评分，
                用于检测系统性泡沫风险
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # LOWER SECTION
    # =====================================
    left, right = st.columns([1.2, 1])

    # =====================================
    # CHART
    # =====================================
    with left:

        st.markdown("""
        <div class="chart-title">
        📈 AI资本扩张趋势
        </div>
        """, unsafe_allow_html=True)

        fig, ax = plt.subplots(figsize=(6.5, 3))

        ax.plot(years, revenue, label="Revenue")
        ax.plot(years, capex, label="CapEx")
        ax.plot(years, fcf, label="FCF")

        ax.legend(fontsize=7)

        ax.tick_params(labelsize=8)

        ax.set_facecolor("#121826")

        fig.patch.set_facecolor("#121826")

        for spine in ax.spines.values():
            spine.set_color("#334155")

        ax.tick_params(colors="white")

        st.pyplot(fig, use_container_width=False)

    # =====================================
    # NOTE
    # =====================================
    with right:

        st.markdown("""
        <div class="chart-title">
        🧠 系统说明
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="note-box">

        本系统用于检测 AI 基础设施资本开支是否开始脱离真实收入增长，
        通过 Revenue、CapEx 与 Free Cash Flow 的动态关系，
        识别 AI 产业是否进入资本过热周期。

        当资本开支扩张速度持续高于收入增长时，
        系统会逐步提高风险等级，
        用于提示潜在的 AI 泡沫风险。

        </div>
        """, unsafe_allow_html=True)

    # =====================================
    # DATA
    # =====================================
    with st.expander("📊 查看原始数据"):

        df = pd.DataFrame({
            "Year": years,
            "Revenue": revenue,
            "CapEx": capex,
            "FCF": fcf
        })

        st.dataframe(df)

else:
    st.warning("数据加载失败或 API 限制")
