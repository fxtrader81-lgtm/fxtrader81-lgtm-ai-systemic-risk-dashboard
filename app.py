import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="AI Risk Terminal",
    layout="wide"
)

# =========================================================
# API
# =========================================================

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>

html, body, [class*="css"]  {
    background-color: #050b16;
    color: white;
    font-family: Inter, sans-serif;
}

/* 整体 */
.main .block-container{
    padding-top: 1.2rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    max-width: 1600px;
}

/* 隐藏streamlit元素 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* 顶部 */
.hero-box{
    background:
        radial-gradient(circle at top left, rgba(29,78,216,0.22), transparent 35%),
        linear-gradient(135deg,#07111f 0%, #020617 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 28px 34px;
    margin-bottom: 22px;
    box-shadow: 0 0 40px rgba(0,0,0,0.55);
}

.hero-top{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
}

.hero-title{
    font-size:56px;
    font-weight:800;
    letter-spacing:-1px;
    margin-bottom:10px;
}

.hero-sub{
    font-size:18px;
    color:#94a3b8;
    margin-top:6px;
}

.hero-right{
    text-align:right;
}

.hero-time{
    color:#9ca3af;
    font-size:15px;
    margin-bottom:14px;
}

.hero-symbol{
    background: rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.08);
    padding:10px 20px;
    border-radius:14px;
    display:inline-block;
    font-size:28px;
    font-weight:700;
}

/* 指标卡 */
.metric-card{
    background:
        radial-gradient(circle at top left, rgba(30,64,175,0.16), transparent 30%),
        linear-gradient(180deg,#07101f 0%, #050b16 100%);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:22px;
    padding:24px;
    min-height:190px;
    box-shadow:0 0 22px rgba(0,0,0,0.35);
}

.metric-label{
    color:#cbd5e1;
    font-size:18px;
    font-weight:600;
    margin-bottom:28px;
}

.metric-number{
    font-size:54px;
    font-weight:800;
    line-height:1;
    margin-bottom:18px;
    letter-spacing:-1px;
}

.metric-desc{
    color:#94a3b8;
    font-size:15px;
    line-height:1.7;
}

.green{
    color:#22c55e;
}

.red{
    color:#ef4444;
}

.yellow{
    color:#fbbf24;
}

/* alert */
.alert-box{
    margin-top:22px;
    background:
        radial-gradient(circle at left, rgba(251,191,36,0.18), transparent 25%),
        linear-gradient(135deg,#161005 0%, #090909 100%);
    border:1px solid rgba(251,191,36,0.35);
    border-radius:24px;
    padding:34px;
    display:flex;
    gap:28px;
    align-items:flex-start;
}

.alert-icon{
    font-size:72px;
    line-height:1;
}

.alert-title{
    color:#fbbf24;
    font-size:42px;
    font-weight:800;
    margin-bottom:14px;
    line-height:1.2;
}

.alert-text{
    color:#d1d5db;
    font-size:22px;
    line-height:1.9;
}

/* panel */
.panel{
    margin-top:24px;
    background:
        radial-gradient(circle at top left, rgba(29,78,216,0.16), transparent 30%),
        linear-gradient(180deg,#07101f 0%, #050b16 100%);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:24px;
    padding:28px;
    min-height:620px;
}

.panel-title{
    font-size:34px;
    font-weight:800;
    margin-bottom:24px;
}

/* logic */
.logic-item{
    color:#d1d5db;
    font-size:22px;
    line-height:2;
    margin-bottom:10px;
}

.logic-sub{
    color:#94a3b8;
    margin-left:22px;
    font-size:19px;
}

/* footer */
.footer{
    margin-top:24px;
    color:#6b7280;
    font-size:14px;
    text-align:center;
    padding-bottom:12px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# INPUT
# =========================================================

symbol = st.text_input(
    "股票代码",
    "NVDA"
)

# =========================================================
# FETCH
# =========================================================

def fetch(url):
    try:
        r = requests.get(url, timeout=20)
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
# DATA
# =========================================================

if (
    isinstance(income, list)
    and isinstance(cash, list)
    and len(income) >= 5
    and len(cash) >= 5
):

    years = []
    revenue = []
    capex = []

    for i in range(5):

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

    rev_growth = rev_growths[-1]
    capex_growth = capex_growths[-1]

    diff = capex_growth - rev_growth

    # =========================================================
    # STATUS
    # =========================================================

    if diff >= 20:
        status = "过热预警"
        status_color = "yellow"
        status_desc = "当前AI资本扩张已经进入高波动风险阶段。"

    elif diff >= 0:
        status = "偏热"
        status_color = "yellow"
        status_desc = "资本扩张开始领先收入增长。"

    else:
        status = "健康"
        status_color = "green"
        status_desc = "收入增长仍高于资本扩张速度。"

    # =========================================================
    # HERO
    # =========================================================

    st.markdown(f"""
    <div class="hero-box">

        <div class="hero-top">

            <div>

                <div class="hero-title">
                🌾 稻草一：AI资本开支循环检测
                </div>

                <div class="hero-sub">
                核心检测维度：资本开支扩张速度是否超过收入增长速度
                </div>

            </div>

            <div class="hero-right">

                <div class="hero-time">
                更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                </div>

                <div class="hero-symbol">
                {symbol.upper()}
                </div>

            </div>

        </div>

    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # METRICS
    # =========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-label">
            收入增长率 (YoY)
            </div>

            <div class="metric-number green">
            {rev_growth:.2f}%
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
            {capex_growth:.2f}%
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
            +{diff:.2f}%
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
    # ALERT
    # =========================================================

    st.markdown(f"""
    <div class="alert-box">

        <div class="alert-icon">
        ⚠️
        </div>

        <div>

            <div class="alert-title">
            结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段
            </div>

            <div class="alert-text">

            当前资本开支增速比收入增速高出
            <span class="yellow">
            {diff:.2f}%
            </span>，

            显示企业在AI基础设施上的投入扩张已经超出
            现实需求支撑。

            <br><br>

            若该趋势持续，
            将提升未来盈利与现金流承压风险，
            需要重点跟踪需求兑现情况。

            </div>

        </div>

    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # LOWER
    # =========================================================

    left_panel, right_panel = st.columns([1, 1.35])

    # =========================================================
    # LEFT
    # =========================================================

    with left_panel:

        st.markdown("""
        <div class="panel">

            <div class="panel-title">
            ⚙️ 检测逻辑
            </div>

            <div class="logic-item">
            ① 获取最近5年财年数据：收入、资本开支
            </div>

            <div class="logic-item">
            ② 计算收入增长率 = (本期收入 - 上期收入) / 上期收入
            </div>

            <div class="logic-item">
            ③ 计算资本开支增长率 = (本期资本开支 - 上期资本开支) / 上期资本开支
            </div>

            <div class="logic-item">
            ④ 计算增速差 = 资本开支增长率 - 收入增长率
            </div>

            <div class="logic-item">
            ⑤ 根据阈值判断状态：
            </div>

            <div class="logic-sub">
            🔴 增速差 ≥ 20% → 过热预警
            </div>

            <div class="logic-sub">
            🟡 0% ≤ 增速差 &lt; 20% → 偏热
            </div>

            <div class="logic-sub">
            🟢 增速差 &lt; 0% → 健康
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =========================================================
    # RIGHT
    # =========================================================

    with right_panel:

        st.markdown("""
        <div class="panel">
        <div class="panel-title">
        📈 趋势对比（最近5年）
        </div>
        """, unsafe_allow_html=True)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=years[1:],
            y=rev_growths,
            mode="lines+markers+text",
            name="收入增长率(%)",
            text=[f"{x:.1f}%" for x in rev_growths],
            textposition="top center",
            line=dict(
                color="#22c55e",
                width=5
            ),
            marker=dict(
                size=12
            ),
            textfont=dict(
                size=16,
                color="#22c55e"
            )
        ))

        fig.add_trace(go.Scatter(
            x=years[1:],
            y=capex_growths,
            mode="lines+markers+text",
            name="资本开支增长率(%)",
            text=[f"{x:.1f}%" for x in capex_growths],
            textposition="top center",
            line=dict(
                color="#ef4444",
                width=5
            ),
            marker=dict(
                size=12
            ),
            textfont=dict(
                size=16,
                color="#ef4444"
            )
        ))

        fig.update_layout(

            height=520,

            paper_bgcolor="#050b16",
            plot_bgcolor="#050b16",

            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20
            ),

            font=dict(
                color="white",
                size=16
            ),

            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=16)
            ),

            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=16)
            ),

            yaxis=dict(
                title="增长率 (%)",
                title_font=dict(size=18),
                gridcolor="rgba(255,255,255,0.08)",
                zerolinecolor="rgba(255,255,255,0.15)",
                tickfont=dict(size=15)
            ),

            hovermode="x unified"
        )

        st.plotly_chart(
            fig,
            width='stretch'
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================
    # FOOTER
    # =========================================================

    st.markdown("""
    <div class="footer">
    数据来源：Financial Modeling Prep（FMP） ｜ 单位：USD ｜ 更新频率：实时
    </div>
    """, unsafe_allow_html=True)

else:

    st.error("API数据加载失败")
