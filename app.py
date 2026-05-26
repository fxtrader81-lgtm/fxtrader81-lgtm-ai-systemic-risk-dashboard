import streamlit as st
import requests
import plotly.graph_objects as go

# ======================================================
# PAGE CONFIG
# ======================================================

st.set_page_config(
    page_title="AI Risk Terminal",
    layout="wide"
)

# ======================================================
# API CONFIG
# ======================================================

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# ======================================================
# GLOBAL STYLE
# ======================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    background-color: #050816;
    color: white;
    font-family: "Inter", sans-serif;
}

/* Main Layout */
.block-container {
    padding-top: 1.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1600px;
}

/* Header */
.main-title {
    font-size: 48px;
    font-weight: 800;
    color: white;
    margin-bottom: 8px;
    letter-spacing: -1px;
}

.sub-title {
    color: #94a3b8;
    font-size: 18px;
    margin-bottom: 35px;
}

/* Metric Cards */
.metric-card {

    background:
        linear-gradient(
            180deg,
            rgba(17,24,39,0.98) 0%,
            rgba(15,23,42,0.98) 100%
        );

    border: 1px solid rgba(255,255,255,0.06);

    border-radius: 24px;

    padding: 28px;

    min-height: 260px;

    box-shadow:
        0 0 40px rgba(0,0,0,0.35);

    transition: all 0.3s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
}

.metric-label {
    color: #94a3b8;
    font-size: 15px;
    margin-bottom: 22px;
}

.metric-number {
    font-size: 52px;
    font-weight: 800;
    margin-bottom: 20px;
    line-height: 1;
}

.metric-desc {
    color: #cbd5e1;
    font-size: 15px;
    line-height: 1.9;
}

/* Colors */
.green {
    color: #22c55e;
}

.red {
    color: #ef4444;
}

.yellow {
    color: #fbbf24;
}

/* Alert Box */
.alert-box {

    margin-top: 30px;

    background:
        linear-gradient(
            90deg,
            rgba(70,50,0,0.95),
            rgba(20,15,5,0.98)
        );

    border: 1px solid rgba(251,191,36,0.25);

    border-radius: 26px;

    padding: 36px;

    box-shadow:
        0 0 50px rgba(251,191,36,0.08);
}

.alert-title {
    color: #fbbf24;
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 18px;
}

.alert-text {
    color: white;
    font-size: 20px;
    line-height: 2;
}

/* Section Card */
.section-card {

    margin-top: 32px;

    background:
        linear-gradient(
            180deg,
            rgba(17,24,39,0.98) 0%,
            rgba(15,23,42,0.98) 100%
        );

    border: 1px solid rgba(255,255,255,0.06);

    border-radius: 24px;

    padding: 28px;

    min-height: 560px;

    box-shadow:
        0 0 40px rgba(0,0,0,0.35);
}

.section-title {
    font-size: 30px;
    font-weight: 700;
    margin-bottom: 28px;
}

.logic-item {
    font-size: 17px;
    line-height: 2;
    color: #e2e8f0;
    margin-bottom: 16px;
}

/* Footer */
.footer {
    margin-top: 24px;
    color: #64748b;
    font-size: 14px;
}

.stTextInput input {
    background-color: #111827 !important;
    color: white !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}

</style>
""", unsafe_allow_html=True)

# ======================================================
# HEADER
# ======================================================

left, right = st.columns([5, 1])

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

    symbol = st.text_input(
        "股票代码",
        "NVDA"
    )

# ======================================================
# FETCH
# ======================================================

@st.cache_data(ttl=300)
def fetch(url):

    try:

        r = requests.get(
            url,
            timeout=10
        )

        if r.status_code != 200:
            return []

        return r.json()

    except:
        return []

# ======================================================
# SAFE
# ======================================================

def safe(x, key):

    try:
        return float(x.get(key, 0))
    except:
        return 0

# ======================================================
# API DATA
# ======================================================

income = fetch(
    f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

cash = fetch(
    f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

# ======================================================
# MAIN
# ======================================================

if isinstance(income, list) and len(income) > 1:

    years = []
    revenue = []
    capex = []

    for i in range(min(len(income), len(cash))):

        years.append(
            income[i]["date"][:4]
        )

        revenue.append(
            safe(income[i], "revenue")
        )

        capex.append(
            abs(safe(cash[i], "capitalExpenditure"))
        )

    years = years[::-1]
    revenue = revenue[::-1]
    capex = capex[::-1]

    # ======================================================
    # CORE METRICS
    # ======================================================

    rev_growth = (
        (revenue[-1] - revenue[-2])
        / revenue[-2]
    )

    capex_growth = (
        (capex[-1] - capex[-2])
        / capex[-2]
    )

    diff = capex_growth - rev_growth

    status = "🟢 健康"
    status_color = "green"

    if diff > 0:
        status = "🟡 偏热"
        status_color = "yellow"

    if diff > 0.2:
        status = "🟡 过热预警"
        status_color = "yellow"

    # ======================================================
    # KPI CARDS
    # ======================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-label">
            收入增长率 (YoY)
            </div>

            <div class="metric-number green">
            {rev_growth*100:.2f}%
            </div>

            <div class="metric-desc">
            AI需求仍维持高增长，<br>
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
            {capex_growth*100:.2f}%
            </div>

            <div class="metric-desc">
            企业正在加速AI基础设施投入，<br>
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
            资本扩张速度已经开始超过<br>
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

            <div class="metric-number {status_color}">
            {status}
            </div>

            <div class="metric-desc">
            当前AI资本扩张已经进入<br>
            高波动风险阶段。
            </div>

        </div>
        """, unsafe_allow_html=True)

    # ======================================================
    # ALERT BOX
    # ======================================================

    st.markdown(f"""
    <div class="alert-box">

        <div class="alert-title">
        结论：AI资本开支扩张速度明显高于收入增长
        </div>

        <div class="alert-text">

        当前资本开支增速比收入增速高出
        <span class="yellow">
        {diff*100:.2f}%
        </span>，

        企业AI基础设施投入已经开始超出
        现实需求支撑。

        <br><br>

        若趋势持续，
        将提升未来盈利与现金流压力。

        </div>

    </div>
    """, unsafe_allow_html=True)

    # ======================================================
    # LOWER PANELS
    # ======================================================

    left_panel, right_panel = st.columns([1, 1])

    # ======================================================
    # LOGIC PANEL
    # ======================================================

    with left_panel:

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
            <br>
            CapEx Growth - Revenue Growth
            </div>

            <div class="logic-item">
            ⑤ 风险阈值：
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

    # ======================================================
    # CHART PANEL
    # ======================================================

    with right_panel:

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
                (revenue[i] - revenue[i - 1])
                / revenue[i - 1]
            ) * 100

            cg = (
                (capex[i] - capex[i - 1])
                / capex[i - 1]
            ) * 100

            rev_growths.append(rg)
            capex_growths.append(cg)

        chart_years = years[1:]

        fig = go.Figure()

        # Revenue Line
        fig.add_trace(go.Scatter(

            x=chart_years,
            y=rev_growths,

            mode="lines+markers+text",

            name="收入增长率",

            text=[
                f"{x:.1f}%"
                for x in rev_growths
            ],

            textposition="top center",

            line=dict(
                color="#22c55e",
                width=5
            ),

            marker=dict(
                size=10
            )
        ))

        # CapEx Line
        fig.add_trace(go.Scatter(

            x=chart_years,
            y=capex_growths,

            mode="lines+markers+text",

            name="资本开支增长率",

            text=[
                f"{x:.1f}%"
                for x in capex_growths
            ],

            textposition="bottom center",

            line=dict(
                color="#ef4444",
                width=5
            ),

            marker=dict(
                size=10
            )
        ))

        fig.update_layout(

            height=500,

            paper_bgcolor="#111827",
            plot_bgcolor="#111827",

            hovermode="x unified",

            font=dict(
                color="white",
                size=15
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

                xanchor="right",
                x=1,

                font=dict(
                    size=14
                )
            ),

            xaxis=dict(

                showgrid=False,

                tickfont=dict(
                    size=14
                )
            ),

            yaxis=dict(

                title="增长率 (%)",

                gridcolor="rgba(255,255,255,0.08)",

                zerolinecolor="rgba(255,255,255,0.2)"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.markdown("""
        </div>
        """, unsafe_allow_html=True)

    # ======================================================
    # FOOTER
    # ======================================================

    st.markdown("""
    <div class="footer">
    数据来源：Financial Modeling Prep（FMP）
    ｜ 单位：USD
    ｜ 更新频率：实时
    </div>
    """, unsafe_allow_html=True)

else:

    st.error("API数据加载失败")
