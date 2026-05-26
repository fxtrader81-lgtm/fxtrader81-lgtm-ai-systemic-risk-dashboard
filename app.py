import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="AI Risk Terminal",
    layout="wide"
)

# =========================================================
# CONFIG
# =========================================================
API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =========================================================
# CSS（真正 Bloomberg / Terminal 风格）
# =========================================================
st.markdown("""
<style>

/* =========================
GLOBAL
========================= */

html, body, [class*="css"] {
    background-color: #050b16;
    color: white;
    font-family: "Inter", sans-serif;
}

/* 去除默认padding */
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* =========================
TOP HEADER
========================= */

.topbar {
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:20px;
}

.main-title {
    font-size:44px;
    font-weight:800;
    color:white;
    letter-spacing:-1px;
}

.sub-title {
    color:#94a3b8;
    font-size:15px;
    margin-top:4px;
}

.symbol-box {
    background:#111827;
    border:1px solid #1e293b;
    border-radius:12px;
    padding:10px 18px;
    font-size:22px;
    font-weight:700;
    color:#38bdf8;
}

/* =========================
CARD
========================= */

.metric-card {
    background: linear-gradient(
        180deg,
        rgba(17,24,39,0.98),
        rgba(10,15,25,0.98)
    );

    border:1px solid #1f2937;

    border-radius:18px;

    padding:24px;

    height:190px;

    box-shadow:
    0 0 0 1px rgba(255,255,255,0.02),
    0 10px 30px rgba(0,0,0,0.35);
}

/* 卡片标题 */
.metric-label {
    color:#94a3b8;
    font-size:14px;
    margin-bottom:20px;
}

/* 卡片主数值 */
.metric-number {
    font-size:42px;
    font-weight:800;
    margin-bottom:12px;
}

/* 卡片说明 */
.metric-desc {
    color:#cbd5e1;
    font-size:14px;
    line-height:1.7;
}

/* =========================
COLORS
========================= */

.green {
    color:#22c55e;
}

.yellow {
    color:#fbbf24;
}

.red {
    color:#ef4444;
}

.blue {
    color:#38bdf8;
}

/* =========================
BIG ALERT
========================= */

.alert-box {

    background: linear-gradient(
        90deg,
        rgba(60,40,0,0.95),
        rgba(20,15,5,0.98)
    );

    border:1px solid #7c5a10;

    border-radius:20px;

    padding:30px;

    margin-top:22px;
    margin-bottom:24px;
}

.alert-title {
    font-size:40px;
    font-weight:800;
    color:#fbbf24;
    margin-bottom:10px;
}

.alert-text {
    font-size:18px;
    color:#f8fafc;
    line-height:1.8;
}

/* =========================
SECTION
========================= */

.section-card {

    background: linear-gradient(
        180deg,
        rgba(17,24,39,0.98),
        rgba(10,15,25,0.98)
    );

    border:1px solid #1f2937;

    border-radius:18px;

    padding:24px;

    min-height:520px;
}

.section-title {
    font-size:26px;
    font-weight:700;
    margin-bottom:20px;
}

/* =========================
LOGIC ITEM
========================= */

.logic-item {
    margin-bottom:18px;
    font-size:16px;
    color:#e2e8f0;
    line-height:1.7;
}

/* =========================
FOOTER
========================= */

.footer {
    margin-top:18px;
    color:#64748b;
    font-size:13px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================
left, right = st.columns([5,1])

with left:

    st.markdown("""
    <div class="main-title">
    稻草一：AI资本开支循环检测
    </div>

    <div class="sub-title">
    核心检测维度：资本开支扩张速度是否超过收入增长速度
    </div>
    """, unsafe_allow_html=True)

with right:

    st.markdown("""
    <div class="symbol-box">
    NVDA
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# INPUT
# =========================================================
symbol = st.text_input("股票代码", "NVDA")

# =========================================================
# FETCH
# =========================================================
@st.cache_data(ttl=300)
def fetch(url):

    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return []

        return r.json()

    except:
        return []

# =========================================================
# SAFE
# =========================================================
def safe(x, k):

    try:
        return float(x.get(k, 0))
    except:
        return 0.0

# =========================================================
# API
# =========================================================
income = fetch(
    f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

cash = fetch(
    f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

# =========================================================
# MAIN
# =========================================================
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

    years = years[::-1]
    revenue = revenue[::-1]
    capex = capex[::-1]
    fcf = fcf[::-1]

    # =========================================================
    # CALCULATION
    # =========================================================
    rev_g = (
        (revenue[-1] - revenue[-2]) / revenue[-2]
        if revenue[-2] else 0
    )

    capex_g = (
        (capex[-1] - capex[-2]) / capex[-2]
        if capex[-2] else 0
    )

    diff = capex_g - rev_g

    # =========================================================
    # STATUS
    # =========================================================
    status = "健康"
    status_color = "green"

    if diff > 0:
        status = "偏热"
        status_color = "yellow"

    if diff > 0.2:
        status = "过热预警"
        status_color = "yellow"

    # =========================================================
    # KPI ROW
    # =========================================================
    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-label">
            收入增长率 (YoY)
            </div>

            <div class="metric-number green">
            {rev_g*100:.2f}%
            </div>

            <div class="metric-desc">
            AI需求仍维持高增长，
            当前收入扩张速度保持强劲。
            </div>

        </div>
        """, unsafe_allow_html=True)

    with c2:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-label">
            资本开支增长率 (YoY)
            </div>

            <div class="metric-number red">
            {capex_g*100:.2f}%
            </div>

            <div class="metric-desc">
            企业正在加速AI基础设施投入，
            CapEx扩张速度持续提升。
            </div>

        </div>
        """, unsafe_allow_html=True)

    with c3:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-label">
            增速差 (CapEx - Revenue)
            </div>

            <div class="metric-number yellow">
            +{diff*100:.2f}%
            </div>

            <div class="metric-desc">
            资本扩张速度已经开始超过
            收入增长速度。
            </div>

        </div>
        """, unsafe_allow_html=True)

    with c4:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-label">
            状态判断
            </div>

            <div class="metric-number yellow">
            {status}
            </div>

            <div class="metric-desc">
            当前AI资本扩张已经进入
            高波动风险阶段。
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =========================================================
    # ALERT
    # =========================================================
    st.markdown(f"""
    <div class="alert-box">

        <div class="alert-title">
        结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段
        </div>

        <div class="alert-text">

        当前资本开支增速比收入增速高出
        <span class="yellow">{diff*100:.2f}%</span>，

        显示企业在AI基础设施上的投入扩张已经超出
        现实需求支撑。

        若该趋势持续，
        将提升未来盈利与现金流承压风险。

        </div>

    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # LOWER SECTION
    # =========================================================
    left2, right2 = st.columns([1,1.2])

    # =========================================================
    # LOGIC
    # =========================================================
    with left2:

        st.markdown("""
        <div class="section-card">

            <div class="section-title">
            ⚙️ 检测逻辑
            </div>

            <div class="logic-item">
            ① 获取最近5年收入与资本开支数据
            </div>

            <div class="logic-item">
            ② 计算 Revenue YoY 增长率
            </div>

            <div class="logic-item">
            ③ 计算 CapEx YoY 增长率
            </div>

            <div class="logic-item">
            ④ 计算增速差：
            CapEx Growth - Revenue Growth
            </div>

            <div class="logic-item">
            ⑤ 根据阈值判断系统风险：
            <br><br>

            增速差 ≥ 20%
            → 过热预警
            <br><br>

            0% ~ 20%
            → 偏热
            <br><br>

            小于 0%
            → 健康
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =========================================================
    # CHART
    # =========================================================
    with right2:

        st.markdown("""
        <div class="section-card">
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="section-title">
        📈 趋势对比（最近5年）
        </div>
        """, unsafe_allow_html=True)

        rev_growths = []
        capex_growths = []

        for i in range(1, len(revenue)):

            rg = (
                (revenue[i] - revenue[i-1]) / revenue[i-1]
                if revenue[i-1] else 0
            )

            cg = (
                (capex[i] - capex[i-1]) / capex[i-1]
                if capex[i-1] else 0
            )

            rev_growths.append(rg * 100)
            capex_growths.append(cg * 100)

        chart_years = years[1:]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=chart_years,
            y=rev_growths,
            mode="lines+markers",
            name="收入增长率",
            line=dict(color="#22c55e", width=4)
        ))

        fig.add_trace(go.Scatter(
            x=chart_years,
            y=capex_growths,
            mode="lines+markers",
            name="资本开支增长率",
            line=dict(color="#ef4444", width=4)
        ))

        fig.update_layout(

            height=420,

            paper_bgcolor="#111827",
            plot_bgcolor="#111827",

            font=dict(
                color="white",
                size=14
            ),

            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20
            ),

            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            ),

            xaxis=dict(
                showgrid=False
            ),

            yaxis=dict(
                gridcolor="rgba(255,255,255,0.08)"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.markdown("""
        </div>
        """, unsafe_allow_html=True)

    # =========================================================
    # FOOTER
    # =========================================================
    st.markdown("""
    <div class="footer">
    数据来源：Financial Modeling Prep（FMP）
    ｜ 单位：USD
    ｜ 更新频率：实时
    </div>
    """, unsafe_allow_html=True)

else:

    st.error("API数据加载失败")
