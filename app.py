import streamlit as st
import requests
import plotly.graph_objects as go

# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title="AI Risk Dashboard",
    layout="wide"
)

# =====================================================
# API
# =====================================================

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"

BASE_URL = "https://financialmodelingprep.com/stable"

# =====================================================
# STYLE
# =====================================================

st.markdown("""
<style>

html, body, [class*="css"]{
    background-color:#050816;
    color:white;
    font-family:Arial;
}

.block-container{
    max-width:1600px;
    padding-top:30px;
}

/* ========================= */

.main-title{
    font-size:42px;
    font-weight:800;
    margin-bottom:8px;
}

.sub-title{
    color:#94a3b8;
    font-size:15px;
    margin-bottom:35px;
}

/* ========================= */

.metric-card{

    background:linear-gradient(
        180deg,
        #111827 0%,
        #0f172a 100%
    );

    border-radius:22px;

    padding:26px;

    min-height:220px;

    border:1px solid rgba(255,255,255,0.06);

    box-shadow:0 0 30px rgba(0,0,0,0.35);
}

.metric-label{
    color:#94a3b8;
    font-size:13px;
    margin-bottom:18px;
}

.metric-number{
    font-size:44px;
    font-weight:800;
    margin-bottom:18px;
}

.metric-desc{
    color:#d1d5db;
    font-size:14px;
    line-height:1.8;
}

/* ========================= */

.green{
    color:#22c55e;
}

.red{
    color:#ef4444;
}

.yellow{
    color:#fbbf24;
}

/* ========================= */

.alert-box{

    margin-top:28px;
    margin-bottom:28px;

    background:linear-gradient(
        90deg,
        rgba(55,40,10,0.95),
        rgba(20,16,10,0.98)
    );

    border-radius:24px;

    padding:30px;

    border:1px solid rgba(251,191,36,0.2);
}

.alert-title{
    color:#fbbf24;
    font-size:30px;
    font-weight:800;
    margin-bottom:16px;
}

.alert-text{
    color:white;
    font-size:17px;
    line-height:2;
}

/* ========================= */

.panel{

    background:linear-gradient(
        180deg,
        #111827 0%,
        #0f172a 100%
    );

    border-radius:22px;

    padding:26px;

    border:1px solid rgba(255,255,255,0.06);

    min-height:580px;
}

.panel-title{
    font-size:24px;
    font-weight:700;
    margin-bottom:24px;
}

.logic-item{
    color:#e2e8f0;
    font-size:15px;
    line-height:2;
    margin-bottom:18px;
}

/* ========================= */

.footer{
    margin-top:20px;
    color:#64748b;
    font-size:13px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================

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

def safe(x, key):

    try:
        return float(x.get(key, 0))
    except:
        return 0

income = fetch(
    f"{BASE_URL}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

cash = fetch(
    f"{BASE_URL}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}"
)

# =====================================================
# MAIN
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
            income[i].get("date","")[:4]
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

    # =========================
    # METRICS
    # =========================

    rev_growth = (
        (revenue[-1] - revenue[-2])
        / revenue[-2]
    )

    capex_growth = (
        (capex[-1] - capex[-2])
        / capex[-2]
    )

    diff = capex_growth - rev_growth

    status = "健康"
    status_color = "green"
    status_desc = "收入增长仍能覆盖资本扩张。"

    if diff > 0:
        status = "偏热"
        status_color = "yellow"
        status_desc = "资本扩张开始领先收入增长。"

    if diff >= 0.2:
        status = "过热预警"
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
            {diff*100:.2f}%
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
        </span>

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

    left_panel, right_panel = st.columns([1,1.5])

    # =========================
    # LEFT
    # =========================

    with left_panel:

        st.markdown("""
        <div class="panel">

            <div class="panel-title">
            检测逻辑
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

    # =========================
    # RIGHT
    # =========================

    with right_panel:

        st.markdown("""
        <div class="panel">
        <div class="panel-title">
        趋势对比（最近5年）
        </div>
        """, unsafe_allow_html=True)

        rev_growths = []
        capex_growths_chart = []

        for i in range(1, len(revenue)):

            rg = (
                (revenue[i] - revenue[i-1])
                / revenue[i-1]
            ) * 100

            cg = (
                (capex[i] - capex[i-1])
                / capex[i-1]
            ) * 100

            rev_growths.append(rg)
            capex_growths_chart.append(cg)

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
            y=capex_growths_chart,
            mode="lines+markers",
            name="资本开支增长率",
            line=dict(
                color="#ef4444",
                width=5
            )
        ))

        fig.update_layout(

            height=500,

            paper_bgcolor="#111827",
            plot_bgcolor="#111827",

            font=dict(
                color="white"
            ),

            legend=dict(
                orientation="h"
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
            width="stretch"
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
