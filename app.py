import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# 页面配置
# =========================================================

st.set_page_config(
    page_title="AI资本开支风险终端",
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
    background: #050b14;
    color: white;
    font-family: -apple-system,BlinkMacSystemFont,sans-serif;
}

/* 主容器 */
.main .block-container{
    padding-top: 24px;
    padding-left: 28px;
    padding-right: 28px;
    max-width: 1600px;
}

/* 顶部 */
.topbar{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    margin-bottom:20px;
}

.main-title{
    font-size:52px;
    font-weight:800;
    color:white;
    line-height:1.1;
    margin-bottom:10px;
}

.sub-title{
    color:#94a3b8;
    font-size:18px;
    font-weight:500;
}

/* 股票代码 */
.ticker-box{
    background:#0f172a;
    border:1px solid rgba(255,255,255,0.08);
    padding:14px 18px;
    border-radius:16px;
    width:160px;
}

.ticker-label{
    color:#64748b;
    font-size:12px;
    margin-bottom:6px;
}

.ticker-value{
    color:white;
    font-size:34px;
    font-weight:700;
}

/* 指标卡 */
.metric-card{
    background: radial-gradient(circle at top left,#0d1b3d,#050b14);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:22px;
    padding:24px;
    height:230px;
    box-shadow: 0 0 30px rgba(0,0,0,0.35);
}

.metric-label{
    color:#cbd5e1;
    font-size:17px;
    font-weight:600;
    margin-bottom:26px;
}

.metric-number{
    font-size:54px;
    font-weight:800;
    line-height:1;
    margin-bottom:18px;
}

.metric-desc{
    color:#94a3b8;
    font-size:15px;
    line-height:1.8;
}

/* 颜色 */
.green{
    color:#22c55e;
}

.red{
    color:#ff5b4d;
}

.yellow{
    color:#fbbf24;
}

/* 结论 */
.alert-box{
    margin-top:24px;
    margin-bottom:24px;
    background: linear-gradient(90deg,rgba(251,191,36,0.12),rgba(0,0,0,0.2));
    border:1px solid rgba(251,191,36,0.28);
    border-radius:22px;
    padding:28px;
}

.alert-title{
    font-size:40px;
    font-weight:800;
    color:#fbbf24;
    margin-bottom:18px;
    line-height:1.3;
}

.alert-text{
    color:#d1d5db;
    font-size:20px;
    line-height:2;
}

/* 下方模块 */
.panel{
    background: radial-gradient(circle at top left,#0d1b3d,#050b14);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:22px;
    padding:26px;
    height:100%;
}

.panel-title{
    font-size:30px;
    font-weight:700;
    margin-bottom:22px;
}

/* 逻辑 */
.logic-item{
    color:#d1d5db;
    font-size:18px;
    line-height:2;
    margin-bottom:10px;
}

/* footer */
.footer{
    margin-top:18px;
    color:#64748b;
    font-size:14px;
}

/* Streamlit输入框 */
.stTextInput > div > div > input{
    background:#111827;
    color:white;
    border-radius:14px;
    border:1px solid rgba(255,255,255,0.08);
    font-size:18px;
}

/* 图表压缩 */
.js-plotly-plot{
    margin-top:-10px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# 顶部
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

    symbol = st.text_input("股票代码", "NVDA")

# =========================================================
# API
# =========================================================

def fetch(url):
    try:
        r = requests.get(url, timeout=15)

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

# =========================================================
# 数据
# =========================================================

if (
    isinstance(income, list)
    and isinstance(cash, list)
    and len(income) >= 2
):

    years = []
    revenue = []
    capex = []

    for i in range(min(len(income), len(cash))):

        years.append(income[i]["date"][:4])

        revenue.append(
            safe(income[i], "revenue")
        )

        capex.append(
            abs(safe(cash[i], "capitalExpenditure"))
        )

    years = years[::-1]
    revenue = revenue[::-1]
    capex = capex[::-1]

    # =========================================================
    # 当前增长率
    # =========================================================

    revenue_growth = (
        (revenue[-1] - revenue[-2])
        / revenue[-2]
    )

    capex_growth = (
        (capex[-1] - capex[-2])
        / capex[-2]
    )

    diff = capex_growth - revenue_growth

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
        资本扩张开始领先收入增长，<br>
        进入偏热阶段。
        """

    else:

        status = "健康"
        status_color = "green"

        status_desc = """
        当前收入增长仍覆盖资本扩张，<br>
        系统处于健康状态。
        """

    # =========================================================
    # 卡片
    # =========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-label">
            收入增长率 (YoY)
            </div>

            <div class="metric-number green">
            {revenue_growth*100:.2f}%
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
        结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段
        </div>

        <div class="alert-text">

        当前资本开支增速比收入增速高出
        <span class="yellow">
        {diff*100:.2f}%
        </span>，

        显示企业在AI基础设施上的投入扩张已经超出
        现实需求支撑。

        <br><br>

        若该趋势持续，
        将提升未来盈利与现金流承压风险，
        需要重点跟踪需求兑现情况。

        </div>

    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # 下方布局
    # =========================================================

    left_panel, right_panel = st.columns([1, 1.35])

    # =========================================================
    # 左侧逻辑
    # =========================================================

    with left_panel:

        st.markdown(f"""
        <div class="panel">

            <div class="panel-title">
            ⚙️ 检测逻辑
            </div>

            <div class="logic-item">
            ① 获取最近5年收入与资本开支数据
            </div>

            <div class="logic-item">
            ② 计算收入增长率 = (本期收入 - 上期收入) / 上期收入
            </div>

            <div class="logic-item">
            ③ 计算资本开支增长率 = (本期CapEx - 上期CapEx) / 上期CapEx
            </div>

            <div class="logic-item">
            ④ 计算增速差 = 资本开支增速 - 收入增速
            </div>

            <div class="logic-item">
            ⑤ 根据阈值判断系统状态：
            <br><br>

            • 增速差 ≥ 20% → 过热预警
            <br>

            • 0% ≤ 增速差 ＜ 20% → 偏热
            <br>

            • 增速差 ＜ 0% → 健康
            </div>

            <div class="logic-item">
            当前系统用于检测AI基础设施投资是否开始
            脱离真实需求增长。
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =========================================================
    # 图表
    # =========================================================

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
            name="收入增长率 (%)",
            line=dict(
                color="#22c55e",
                width=4
            ),
            marker=dict(
                size=9
            )
        ))

        fig.add_trace(go.Scatter(
            x=chart_years,
            y=capex_growths,
            mode="lines+markers",
            name="资本开支增长率 (%)",
            line=dict(
                color="#ff5b4d",
                width=4
            ),
            marker=dict(
                size=9
            )
        ))

        fig.update_layout(

            height=460,

            paper_bgcolor="#050b14",
            plot_bgcolor="#050b14",

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

            hovermode="x unified",

            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="left",
                x=0,
                font=dict(size=14)
            ),

            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=16)
            ),

            yaxis=dict(
                title="增长率 (%)",
                title_font=dict(size=14),
                tickfont=dict(size=14),
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

    st.error("API数据加载失败，请检查API KEY或接口权限")
