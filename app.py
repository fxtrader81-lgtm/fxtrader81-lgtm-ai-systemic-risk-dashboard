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
    background: #050816;
    color: white;
    font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 主容器 */

.block-container {
    max-width: 1600px;
    padding-top: 1.2rem;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 2rem;
}

/* 隐藏streamlit默认 */

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

/* =========================
顶部区域
========================= */

.hero {
    background:
        radial-gradient(circle at top left, rgba(59,130,246,0.18), transparent 30%),
        linear-gradient(135deg,#071224 0%, #020617 100%);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 26px;
    padding: 26px 30px;
    margin-bottom: 24px;
    box-shadow:
        0 0 40px rgba(0,0,0,0.35),
        inset 0 0 30px rgba(255,255,255,0.02);
}

.main-title {
    font-size: 46px;
    font-weight: 800;
    color: white;
    letter-spacing: -1.8px;
    margin-bottom: 10px;
}

.sub-title {
    font-size: 17px;
    color: #94a3b8;
    font-weight: 500;
}

.update-time {
    text-align: right;
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 14px;
}

/* 输入框 */

.stTextInput label {
    color: #94a3b8 !important;
    font-size: 13px !important;
}

.stTextInput input {
    background: rgba(15,23,42,0.9);
    color: white;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.08);
    height: 50px;
    font-size: 18px;
    font-weight: 600;
}

/* =========================
指标卡
========================= */

.metric-card {
    background:
        radial-gradient(circle at top left, rgba(59,130,246,0.12), transparent 30%),
        linear-gradient(145deg,#07152e,#020817);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 22px;
    padding: 24px;
    min-height: 190px;
    box-shadow:
        0 0 24px rgba(0,0,0,0.25),
        inset 0 0 30px rgba(255,255,255,0.02);
}

.metric-label {
    color: #cbd5e1;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 26px;
}

.metric-number {
    font-size: 54px;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 24px;
    letter-spacing: -2px;
}

.metric-desc {
    color: #94a3b8;
    font-size: 14px;
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
结论区域
========================= */

.alert-box {
    margin-top: 24px;
    margin-bottom: 26px;

    background:
        radial-gradient(circle at left, rgba(251,191,36,0.18), transparent 28%),
        linear-gradient(90deg,#2d2100,#0b0f18);

    border: 1px solid rgba(251,191,36,0.22);

    border-radius: 24px;

    padding: 28px;

    box-shadow:
        0 0 35px rgba(0,0,0,0.3),
        inset 0 0 20px rgba(255,255,255,0.02);
}

.alert-title {
    color: #fbbf24;
    font-size: 34px;
    font-weight: 800;
    line-height: 1.3;
    margin-bottom: 18px;
    letter-spacing: -1px;
}

.alert-text {
    color: #d1d5db;
    font-size: 19px;
    line-height: 1.9;
}

/* =========================
下方面板
========================= */

.panel {
    background:
        radial-gradient(circle at top left, rgba(59,130,246,0.10), transparent 30%),
        linear-gradient(145deg,#07152e,#020817);

    border-radius: 24px;
    border: 1px solid rgba(255,255,255,0.06);

    padding: 26px;

    min-height: 100%;

    box-shadow:
        0 0 28px rgba(0,0,0,0.25),
        inset 0 0 30px rgba(255,255,255,0.02);
}

.panel-title {
    color: white;
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 24px;
    letter-spacing: -0.8px;
}

/* 逻辑项 */

.logic-item {
    display: flex;
    align-items: flex-start;
    gap: 14px;

    margin-bottom: 18px;

    color: #d1d5db;
    font-size: 16px;
    line-height: 1.8;
}

.logic-num {
    min-width: 32px;
    height: 32px;

    border-radius: 999px;

    background: rgba(59,130,246,0.25);

    display: flex;
    align-items: center;
    justify-content: center;

    color: #60a5fa;
    font-size: 15px;
    font-weight: 700;
}

/* Footer */

.footer {
    margin-top: 22px;
    color: #64748b;
    font-size: 13px;
    text-align: center;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# 顶部区域
# =========================================================

left_top, right_top = st.columns([5,1])

with left_top:

    st.markdown("""
    <div class="hero">

        <div class="main-title">
        稻草一：AI资本开支循环检测
        </div>

        <div class="sub-title">
        核心检测维度：资本开支扩张速度是否超过收入增长速度
        </div>

    </div>
    """, unsafe_allow_html=True)

with right_top:

    symbol = st.text_input(
        "股票代码",
        "NVDA"
    )

# =========================================================
# API函数
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
# 获取数据
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

        years.append(
            income[i]["date"][:4]
        )

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

    # =====================================================
    # 状态
    # =====================================================

    if diff >= 0.2:

        status = "过热预警"
        status_color = "yellow"

        status_desc = """
AI资本扩张速度已经明显超过收入增长，
系统进入高波动风险阶段。
"""

    elif diff >= 0:

        status = "偏热"
        status_color = "yellow"

        status_desc = """
资本扩张开始领先收入增长，
估值与投资热度持续抬升。
"""

    else:

        status = "健康"
        status_color = "green"

        status_desc = """
收入增长仍高于资本扩张，
需求基本能够支撑投资。
"""

    # =====================================================
    # 顶部卡片
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
    # 中间结论
    # =====================================================

    st.markdown(f"""
    <div class="alert-box">

        <div class="alert-title">
        结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段
        </div>

        <div class="alert-text">

        当前资本开支增速比收入增速高出
        <span class="yellow"><b>{diff*100:.2f}%</b></span>，

        显示企业在AI基础设施上的投入扩张
        已经开始超出真实需求支撑。

        <br><br>

        若趋势持续，
        将提升未来盈利能力与现金流承压风险。

        </div>

    </div>
    """, unsafe_allow_html=True)

    # =====================================================
    # 下方区域
    # =====================================================

    left_panel, right_panel = st.columns([1, 1.5])

    # =====================================================
    # 左侧逻辑
    # =====================================================

    with left_panel:

        st.markdown("""
        <div class="panel">

            <div class="panel-title">
            ⚙️ 检测逻辑
            </div>

            <div class="logic-item">
                <div class="logic-num">1</div>
                <div>
                获取最近5年收入与资本开支数据
                </div>
            </div>

            <div class="logic-item">
                <div class="logic-num">2</div>
                <div>
                计算 Revenue YoY 增长率
                </div>
            </div>

            <div class="logic-item">
                <div class="logic-num">3</div>
                <div>
                计算 CapEx YoY 增长率
                </div>
            </div>

            <div class="logic-item">
                <div class="logic-num">4</div>
                <div>
                计算增速差：<br>
                CapEx Growth - Revenue Growth
                </div>
            </div>

            <div class="logic-item">
                <div class="logic-num">5</div>
                <div>
                增速差 ≥ 20% → 过热预警<br><br>
                0% ~ 20% → 偏热<br><br>
                小于 0% → 健康
                </div>
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =====================================================
    # 右侧图表
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

            mode="lines+markers+text",

            name="收入增长率 (%)",

            text=[
                f"{x:.1f}%"
                for x in rev_growths
            ],

            textposition="top right",

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

            mode="lines+markers+text",

            name="资本开支增长率 (%)",

            text=[
                f"{x:.1f}%"
                for x in capex_growths
            ],

            textposition="top right",

            line=dict(
                color="#ef4444",
                width=4
            ),

            marker=dict(
                size=9
            )
        ))

        fig.update_layout(

            height=480,

            paper_bgcolor="#07152e",
            plot_bgcolor="#07152e",

            hovermode="x unified",

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
                x=0,

                font=dict(
                    size=15,
                    color="white"
                )
            ),

            font=dict(
                color="white",
                size=15
            ),

            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=14)
            ),

            yaxis=dict(
                title="增长率 (%)",
                titlefont=dict(size=15),
                tickfont=dict(size=14),
                gridcolor="rgba(255,255,255,0.08)",
                zeroline=False
            )
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================
    # Footer
    # =====================================================

    st.markdown("""
    <div class="footer">
    数据来源：Financial Modeling Prep（FMP） ｜ 单位：USD ｜ 更新频率：实时
    </div>
    """, unsafe_allow_html=True)

else:

    st.error("API数据加载失败")
