import streamlit as st
import requests
import plotly.graph_objects as go

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AI Risk Terminal",
    layout="wide"
)

# =====================================================
# API
# =====================================================

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =====================================================
# STYLE
# =====================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    background-color: #050816;
    color: white;
    font-family: Inter, sans-serif;
}

.main {
    background-color: #050816;
}

.block-container {
    padding-top: 2rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1600px;
}

header {
    visibility: hidden;
}

/* ========================================= */

.title-main {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 6px;
}

.title-sub {
    color: #94a3b8;
    font-size: 16px;
    margin-bottom: 30px;
}

/* ========================================= */

.metric-card {

    background: linear-gradient(
        180deg,
        #111827 0%,
        #0f172a 100%
    );

    border: 1px solid rgba(255,255,255,0.06);

    border-radius: 22px;

    padding: 28px;

    min-height: 230px;

    box-shadow:
        0 0 40px rgba(0,0,0,0.35);
}

.metric-label {
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 18px;
}

.metric-number {
    font-size: 46px;
    font-weight: 800;
    margin-bottom: 20px;
}

.metric-desc {
    color: #d1d5db;
    font-size: 14px;
    line-height: 1.8;
}

/* ========================================= */

.green {
    color: #22c55e;
}

.red {
    color: #ef4444;
}

.yellow {
    color: #fbbf24;
}

/* ========================================= */

.alert-box {

    margin-top: 30px;
    margin-bottom: 30px;

    background: linear-gradient(
        90deg,
        rgba(55,40,10,0.95),
        rgba(20,16,10,0.98)
    );

    border-radius: 24px;

    padding: 32px;

    border: 1px solid rgba(251,191,36,0.2);
}

.alert-title {
    color: #fbbf24;
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 18px;
}

.alert-text {
    color: white;
    font-size: 18px;
    line-height: 2;
}

/* ========================================= */

.panel {

    background: linear-gradient(
        180deg,
        #111827 0%,
        #0f172a 100%
    );

    border-radius: 24px;

    padding: 28px;

    border: 1px solid rgba(255,255,255,0.06);

    min-height: 620px;
}

.panel-title {
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 26px;
}

.logic-item {
    color: #e2e8f0;
    font-size: 15px;
    line-height: 2;
    margin-bottom: 18px;
}

/* ========================================= */

.footer {
    margin-top: 25px;
    color: #64748b;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================

left, right = st.columns([5, 1])

with left:

    st.markdown("""
    <div class="title-main">
    稻草一：AI资本开支循环检测
    </div>

    <div class="title-sub">
    核心检测维度：资本开支扩张速度是否超过收入增长速度
    </div>
    """, unsafe_allow_html=True)

with right:

    symbol = st.text_input("股票代码", "NVDA")

# =====================================================
# FETCH
# =====================================================

@st.cache_data(ttl=300)
def fetch(url):

    try:

        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return []

        return r.json()

    except:
        return []

def safe(x, k):

    try:
        return float(x.get(k, 0))
    except:
        return 0

income = fetch(
    f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

cash = fetch(
    f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

# =====================================================
# DATA CHECK
# =====================================================

if (
    isinstance(income, list)
    and isinstance(cash, list)
    and len(income) > 1
):

    years = []
    revenue = []
    capex = []

    n = min(len(income), len(cash))

    for i in range(n):

        years.append(
            income[i].get("date", "")[:4]
        )

        revenue.append(
            safe(income[i], "revenue")
        )

        capex.append(
            abs(
                safe(cash[i], "capitalExpenditure")
            )
        )

    years = years[::-1]
    revenue = revenue[::-1]
    capex = capex[::-1]

    # =====================================================
    # METRICS
    # =====================================================

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
    status_desc = "收入增长仍能覆盖资本扩张。"

    if diff > 0:
        status = "🟡 偏热"
        status_color = "yellow"
        status_desc = "资本扩张开始领先收入增长。"

    if diff >= 0.2:
        status = "🔴 过热预警"
        status_color = "red"
        status_desc = "AI资本扩张已经进入高波动风险阶段。"

    # =====================================================
    # TOP CARDS
    # =====================================================

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
            AI需求仍维持高增长。<br>
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
            企业正在加速AI基础设施投入。<br>
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
            {status_desc}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # =====================================================
    # ALERT
    # =====================================================

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

    # =====================================================
    # LOWER AREA
    # =====================================================

    left_panel, right_panel = st.columns([1, 1.5])

    # =====================================================
    # LEFT PANEL
    # =====================================================

    with left_panel:

        st.markdown("""
        <div class="panel">

            <div class="panel-title">
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
            ④ 计算增速差：<br>
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

    # =====================================================
    # RIGHT PANEL
    # =====================================================

    with right_panel:

        st.markdown("""
        <div class="panel">
        <div class="panel-title">
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

        fig.add_trace(go.Scatter(
            x=chart_years,
            y=rev_growths,
            mode="lines+markers",
            name="收入增长率",
            line=dict(
                color="#22c55e",
                width=5
            )
        ))

        fig.add_trace(go.Scatter(
            x=chart_years,
            y=capex_growths,
            mode="lines+markers",
            name="资本开支增长率",
            line=dict(
                color="#ef4444",
                width=5
            )
        ))

        fig.update_layout(

            height=520,

            paper_bgcolor="#111827",
            plot_bgcolor="#111827",

            font=dict(
                color="white",
                size=14
            ),

            legend=dict(
                orientation="h",
                y=1.02
            ),

            xaxis=dict(
                showgrid=False
            ),

            yaxis=dict(
                title="增长率 (%)",
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

    # =====================================================
    # FOOTER
    # =====================================================

    st.markdown("""
    <div class="footer">
    数据来源：Financial Modeling Prep（FMP） ｜ 单位：USD ｜ 更新频率：实时
    </div>
    """, unsafe_allow_html=True)

else:

    st.error("API数据加载失败")
