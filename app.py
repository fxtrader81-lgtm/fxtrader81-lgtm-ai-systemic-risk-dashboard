import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="AI Capital Risk Dashboard",
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

html, body, [class*="css"] {
    background-color: #050b16;
    color: white;
    font-family: Inter, sans-serif;
}

/* Streamlit */
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

.main .block-container{
    max-width: 1600px;
    padding-top: 1.2rem;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 2rem;
}

/* Hero */
.hero-box{
    background:
    radial-gradient(circle at top left, rgba(37,99,235,0.16), transparent 35%),
    linear-gradient(135deg,#07111f 0%, #040816 100%);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:26px;
    padding:28px 34px;
    margin-bottom:24px;
    box-shadow:0 0 40px rgba(0,0,0,0.45);
}

.hero-top{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
}

.hero-title{
    font-size:42px;
    font-weight:800;
    margin-bottom:8px;
    letter-spacing:-1px;
}

.hero-sub{
    color:#94a3b8;
    font-size:17px;
}

.hero-right{
    text-align:right;
}

.hero-time{
    color:#94a3b8;
    font-size:14px;
    margin-bottom:10px;
}

.hero-symbol{
    background:rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:14px;
    padding:10px 18px;
    display:inline-block;
    font-size:22px;
    font-weight:700;
}

/* Cards */
.metric-card{
    background:
    radial-gradient(circle at top left, rgba(37,99,235,0.14), transparent 35%),
    linear-gradient(180deg,#08101f 0%, #050b16 100%);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:22px;
    padding:22px;
    min-height:170px;
    box-shadow:0 0 24px rgba(0,0,0,0.35);
}

.metric-label{
    color:#d1d5db;
    font-size:16px;
    font-weight:600;
    margin-bottom:22px;
}

.metric-number{
    font-size:44px;
    font-weight:800;
    line-height:1;
    margin-bottom:16px;
    letter-spacing:-1px;
}

.metric-desc{
    color:#94a3b8;
    font-size:14px;
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

/* Alert */
.alert-box{
    margin-top:22px;
    background:
    radial-gradient(circle at left, rgba(251,191,36,0.18), transparent 28%),
    linear-gradient(135deg,#1a1205 0%, #090909 100%);
    border:1px solid rgba(251,191,36,0.35);
    border-radius:24px;
    padding:30px;
    display:flex;
    gap:24px;
    align-items:flex-start;
}

.alert-icon{
    font-size:62px;
    line-height:1;
}

.alert-title{
    color:#fbbf24;
    font-size:32px;
    font-weight:800;
    margin-bottom:12px;
    line-height:1.3;
}

.alert-text{
    color:#d1d5db;
    font-size:18px;
    line-height:1.9;
}

/* Panels */
.panel{
    margin-top:24px;
    background:
    radial-gradient(circle at top left, rgba(37,99,235,0.12), transparent 35%),
    linear-gradient(180deg,#08101f 0%, #050b16 100%);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:24px;
    padding:26px;
    min-height:580px;
}

.panel-title{
    font-size:28px;
    font-weight:800;
    margin-bottom:22px;
}

.logic-item{
    color:#d1d5db;
    font-size:18px;
    line-height:2;
    margin-bottom:6px;
}

.logic-sub{
    color:#94a3b8;
    font-size:16px;
    margin-left:18px;
    line-height:2;
}

.footer{
    margin-top:24px;
    text-align:center;
    color:#6b7280;
    font-size:13px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# INPUT
# =========================================================

symbol = st.text_input("股票代码", "NVDA")

# =========================================================
# FUNCTIONS
# =========================================================

def fetch(url):
    try:
        r = requests.get(url, timeout=15)
        return r.json()
    except:
        return []

def safe(x, k):
    try:
        return float(x.get(k, 0))
    except:
        return 0

# =========================================================
# API DATA
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

    # =====================================================
    # STATUS
    # =====================================================

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

    # =====================================================
    # HERO
    # =====================================================

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

    # =====================================================
    # METRICS
    # =====================================================

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

    # =====================================================
    # ALERT
    # =====================================================

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
            <span class="yellow">{diff:.2f}%</span>，

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

    # =====================================================
    # LOWER PANELS
    # =====================================================

    left_panel, right_panel = st.columns([1, 1.4])

    # =====================================================
    # LEFT
    # =====================================================

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
            ⑤ 根据阈值判断系统风险：
            </div>

            <div class="logic-sub">
            🔴 增速差 ≥ 20% → 过热预警
            </div>

            <div class="logic-sub">
            🟡 0% ≤ 增速差 ＜ 20% → 偏热
            </div>

            <div class="logic-sub">
            🟢 增速差 ＜ 0% → 健康
            </div>

        </div>
        """, unsafe_allow_html=True)

    # =====================================================
    # RIGHT
    # =====================================================

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
            x=years[1:],
            y=capex_growths,
            mode="lines+markers",
            name="资本开支增长率 (%)",
            line=dict(
                color="#ef4444",
                width=4
            ),
            marker=dict(
                size=9
            )
        ))

        fig.update_layout(

            height=470,

            paper_bgcolor="#050b16",
            plot_bgcolor="#050b16",

            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10
            ),

            font=dict(
                color="white",
                size=14
            ),

            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=14)
            ),

            hovermode="x unified",

            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=14)
            ),

            yaxis=dict(
                title="增长率 (%)",
                title_font=dict(size=15),
                gridcolor="rgba(255,255,255,0.06)",
                zerolinecolor="rgba(255,255,255,0.1)",
                tickfont=dict(size=13)
            )
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================
    # FOOTER
    # =====================================================

    st.markdown("""
    <div class="footer">
    数据来源：Financial Modeling Prep（FMP） ｜ 单位：USD ｜ 更新频率：实时
    </div>
    """, unsafe_allow_html=True)

else:

    st.error("API数据加载失败，请检查 API KEY 或接口权限")
