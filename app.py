import streamlit as st
import requests
import plotly.graph_objects as go

# ======================================================
# PAGE
# ======================================================

st.set_page_config(
    page_title="AI Risk Terminal",
    layout="wide"
)

# ======================================================
# API
# ======================================================

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# ======================================================
# STYLE
# ======================================================

st.markdown("""
<style>

html, body, [class*="css"]  {
    background-color: #050816;
    color: white;
}

.block-container {
    padding-top: 1rem;
}

div[data-testid="metric-container"] {

    background: linear-gradient(
        180deg,
        #111827 0%,
        #0f172a 100%
    );

    border: 1px solid #1f2937;

    padding: 20px;

    border-radius: 18px;

    box-shadow:
        0 0 25px rgba(0,0,0,0.35);
}

.label {
    color: #94a3b8;
    font-size: 14px;
}

.big-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 10px;
}

.sub-title {
    color: #94a3b8;
    margin-bottom: 30px;
}

.alert-box {

    margin-top: 25px;

    background: linear-gradient(
        90deg,
        rgba(70,50,0,0.95),
        rgba(20,15,5,0.98)
    );

    border: 1px solid #7c5a10;

    border-radius: 20px;

    padding: 30px;
}

.alert-title {
    color: #fbbf24;
    font-size: 32px;
    font-weight: 800;
}

.alert-text {
    color: white;
    font-size: 18px;
    line-height: 1.8;
    margin-top: 14px;
}

.footer {
    color: #64748b;
    margin-top: 20px;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)

# ======================================================
# HEADER
# ======================================================

left, right = st.columns([5,1])

with left:

    st.markdown("""
    <div class="big-title">
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
# DATA
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

    if diff > 0:
        status = "🟡 偏热"

    if diff > 0.2:
        status = "🟡 过热预警"

    # ======================================================
    # KPI
    # ======================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "收入增长率 (YoY)",
            f"{rev_growth*100:.2f}%",
            "AI需求仍维持高增长"
        )

    with c2:
        st.metric(
            "资本开支增长率 (YoY)",
            f"{capex_growth*100:.2f}%",
            "AI基础设施投入持续提升"
        )

    with c3:
        st.metric(
            "增速差 (CapEx - Revenue)",
            f"{diff*100:.2f}%",
            "资本扩张已开始超过收入增长"
        )

    with c4:
        st.metric(
            "状态判断",
            status,
            "AI资本扩张进入高波动阶段"
        )

    # ======================================================
    # ALERT
    # ======================================================

    st.markdown(f"""
    <div class="alert-box">

        <div class="alert-title">
        结论：AI资本开支扩张速度明显高于收入增长
        </div>

        <div class="alert-text">

        当前资本开支增速比收入增速高出
        {diff*100:.2f}% 。

        企业AI基础设施投入已经开始超出
        现实需求支撑。

        若趋势持续，
        将提升未来盈利与现金流压力。

        </div>

    </div>
    """, unsafe_allow_html=True)

    # ======================================================
    # CHART
    # ======================================================

    st.markdown("## 📈 趋势对比（最近5年）")

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

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years[1:],
        y=rev_growths,
        mode="lines+markers",
        name="收入增长率",
        line=dict(
            color="#22c55e",
            width=4
        )
    ))

    fig.add_trace(go.Scatter(
        x=years[1:],
        y=capex_growths,
        mode="lines+markers",
        name="资本开支增长率",
        line=dict(
            color="#ef4444",
            width=4
        )
    ))

    fig.update_layout(

        paper_bgcolor="#111827",
        plot_bgcolor="#111827",

        height=500,

        font=dict(
            color="white"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.markdown("""
    <div class="footer">
    数据来源：Financial Modeling Prep（FMP）
    ｜ 单位：USD
    ｜ 更新频率：实时
    </div>
    """, unsafe_allow_html=True)

else:

    st.error("API数据加载失败")
