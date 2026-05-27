import streamlit as st
import requests
import plotly.graph_objects as go

# =========================================================
# 页面配置
# =========================================================

st.set_page_config(
    page_title="AI资本开支风险系统",
    layout="wide"
)

# =========================================================
# API
# =========================================================

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    background-color: #050816;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

.block-container {
    padding-top: 2rem;
    padding-left: 3rem;
    padding-right: 3rem;
}

/* =========================
标题
========================= */

.main-title {
    font-size: 56px;
    font-weight: 800;
    color: white;
    margin-bottom: 10px;
}

.sub-title {
    font-size: 24px;
    color: #94a3b8;
    margin-bottom: 40px;
}

/* =========================
Metric Card
========================= */

.metric-card {
    background: linear-gradient(145deg,#07122b,#020817);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 28px;
    height: 260px;
    box-shadow: 0 0 40px rgba(0,0,0,0.4);
}

.metric-label {
    color: #94a3b8;
    font-size: 18px;
    margin-bottom: 20px;
}

.metric-number {
    font-size: 52px;
    font-weight: 800;
    margin-bottom: 18px;
}

.metric-desc {
    color: #cbd5e1;
    font-size: 18px;
    line-height: 1.7;
}

.green {
    color: #22c55e;
}

.red {
    color: #ef4444;
}

.yellow {
    color: #fbbf24;
}

/* =========================
Alert
========================= */

.alert-box {
    margin-top: 30px;
    margin-bottom: 30px;
    background: linear-gradient(90deg,#3b2a00,#0f0f0f);
    border: 1px solid rgba(251,191,36,0.35);
    border-radius: 24px;
    padding: 35px;
}

.alert-title {
    font-size: 42px;
    font-weight: 800;
    color: #fbbf24;
    margin-bottom: 20px;
}

.alert-text {
    font-size: 24px;
    color: #e5e7eb;
    line-height: 1.9;
}

/* =========================
Panel
========================= */

.panel {
    background: linear-gradient(145deg,#07122b,#020817);
    border-radius: 24px;
    padding: 28px;
    border: 1px solid rgba(255,255,255,0.08);
    height: 100%;
}

.panel-title {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 25px;
    color: white;
}

.logic-item {
    font-size: 20px;
    color: #cbd5e1;
    margin-bottom: 18px;
    line-height: 1.8;
}

/* =========================
Footer
========================= */

.footer {
    margin-top: 25px;
    color: #64748b;
    font-size: 16px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# 标题
# =========================================================

col_title, col_input = st.columns([4,1])

with col_title:

    st.markdown("""
<div class="main-title">
稻草一：AI资本开支循环检测
</div>

<div class="sub-title">
核心检测维度：资本开支扩张速度是否超过收入增长速度
</div>
""", unsafe_allow_html=True)

with col_input:

    symbol = st.text_input("股票代码", "NVDA")

# =========================================================
# 请求函数
# =========================================================

def fetch(url):

    try:
        r = requests.get(url)

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
# 数据处理
# =========================================================

if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2:

    years = []
    revenue = []
    capex = []

    n = min(len(income), len(cash))

    for i in range(n):

        years.append(income[i]["date"][:4])

        revenue.append(
            safe(income[i], "revenue")
        )

        capex.append(
            abs(safe(cash[i], "capitalExpenditure"))
        )

    years.reverse()
    revenue.reverse()
    capex.reverse()

    rev_growth = (
        (revenue[-1] - revenue[-2])
        / revenue[-2]
    )

    capex_growth = (
        (capex[-1] - capex[-2])
        / capex[-2]
    )

    diff = capex_growth - rev_growth

    # =========================================================
    # 状态
    # =========================================================

    if diff >= 0.2:

        status = "过热预警"
        status_color = "yellow"

        status_desc = """
当前AI资本扩张已经进入<br>
高波动风险阶段。
"""

    elif diff >= 0:

        status = "偏热"
        status_color = "yellow"

        status_desc = """
资本扩张开始领先收入增长。<br>
系统开始进入高估值区间。
"""

    else:

        status = "健康"
        status_color = "green"

        status_desc = """
收入增长仍高于资本扩张。<br>
AI需求尚能支撑投资。
"""

    # =========================================================
    # 顶部4卡
    # =========================================================

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

    # =========================================================
    # 结论
    # =========================================================

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

    # =========================================================
    # 下方布局
    # =========================================================

    left, right = st.columns([1,1.5])

    # =========================================================
    # 左侧逻辑
    # =========================================================

    with left:

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

    # =========================================================
    # 图表
    # =========================================================

    with right:

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
                (revenue[i] - revenue[i-1])
                / revenue[i-1]
            ) * 100

            cg = (
                (capex[i] - capex[i-1])
                / capex[i-1]
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
            ),

            marker=dict(
                size=10
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
            ),

            marker=dict(
                size=10
            )
        ))

        fig.update_layout(

            height=500,

            paper_bgcolor="#07122b",
            plot_bgcolor="#07122b",

            font=dict(
                color="white",
                size=16
            ),

            legend=dict(
                orientation="h",
                y=1.1
            ),

            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20
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
            width='stretch'
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================
    # Footer
    # =========================================================

    st.markdown("""
<div class="footer">
数据来源：Financial Modeling Prep（FMP） ｜ 单位：USD ｜ 更新频率：实时
</div>
""", unsafe_allow_html=True)

else:

    st.error("API数据加载失败")
