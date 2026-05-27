import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

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

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    background-color: #050816;
    color: white;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.block-container {
    padding-top: 1.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1600px;
}

/* =========================
顶部 Header
========================= */

.header-bar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 22px;
}

.header-left {}

.header-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
}

.main-title {
    font-size: 30px;
    font-weight: 800;
    color: white;
    margin-bottom: 4px;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.title-icon {
    font-size: 28px;
}

.sub-title {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 0;
}

.timestamp {
    font-size: 13px;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 6px;
}

.symbol-badge {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 4px 14px;
    font-size: 14px;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: 1px;
}

/* =========================
输入框
========================= */

.stTextInput input {
    background-color: #111827;
    color: white;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.1);
    font-size: 14px;
}

/* =========================
Metric Card
========================= */

.metric-card {
    background: linear-gradient(145deg, #0a1628, #060d1f);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 22px 24px;
    height: 172px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 16px 16px 0 0;
}

.metric-card.card-green::before { background: linear-gradient(90deg, #22c55e, transparent); }
.metric-card.card-red::before   { background: linear-gradient(90deg, #ef4444, transparent); }
.metric-card.card-yellow::before{ background: linear-gradient(90deg, #fbbf24, transparent); }
.metric-card.card-status-green::before { background: linear-gradient(90deg, #22c55e, transparent); }
.metric-card.card-status-yellow::before{ background: linear-gradient(90deg, #fbbf24, transparent); }

.metric-label {
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metric-value-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
}

.metric-number {
    font-size: 36px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1px;
}

.metric-arrow {
    font-size: 22px;
    line-height: 1;
    margin-top: 4px;
}

.metric-desc {
    color: #94a3b8;
    font-size: 12px;
    line-height: 1.6;
}

.green  { color: #22c55e; }
.red    { color: #ef4444; }
.yellow { color: #fbbf24; }

/* =========================
Alert
========================= */

.alert-box {
    margin-top: 18px;
    margin-bottom: 18px;
    background: linear-gradient(135deg, #1a1200 0%, #0f0c00 50%, #0a0a0a 100%);
    border: 1px solid rgba(251,191,36,0.2);
    border-radius: 16px;
    padding: 24px 28px;
    display: flex;
    gap: 20px;
    align-items: flex-start;
}

.alert-icon {
    font-size: 42px;
    flex-shrink: 0;
    line-height: 1;
    margin-top: 2px;
}

.alert-content {}

.alert-title {
    font-size: 20px;
    font-weight: 700;
    color: #fbbf24;
    margin-bottom: 10px;
    line-height: 1.3;
}

.alert-text {
    font-size: 14px;
    color: #cbd5e1;
    line-height: 1.75;
}

/* =========================
Panel
========================= */

.panel {
    background: linear-gradient(145deg, #0a1628, #060d1f);
    border-radius: 16px;
    padding: 22px;
    border: 1px solid rgba(255,255,255,0.07);
    height: 100%;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}

.panel-title {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 20px;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* 检测逻辑步骤 */
.logic-step {
    display: flex;
    gap: 12px;
    margin-bottom: 14px;
    align-items: flex-start;
}

.step-badge {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
}

.step-badge-blue   { background: #1e40af; color: #93c5fd; }
.step-badge-green  { background: #14532d; color: #86efac; }
.step-badge-yellow { background: #713f12; color: #fde68a; }

.step-text {
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.6;
}

/* 阈值说明 */
.threshold-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-radius: 8px;
    margin-bottom: 6px;
    background: rgba(255,255,255,0.03);
}

.threshold-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

.threshold-label {
    font-size: 12px;
    color: #64748b;
    flex: 1;
}

.threshold-arrow {
    font-size: 12px;
    color: #475569;
}

.threshold-status {
    font-size: 12px;
    font-weight: 600;
}

/* =========================
Footer
========================= */

.footer {
    margin-top: 16px;
    color: #334155;
    font-size: 11px;
    text-align: right;
}

/* =========================
隐藏streamlit默认元素
========================= */

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

</style>
""", unsafe_allow_html=True)

# =========================================================
# 标题 + 输入
# =========================================================

col_title, col_input = st.columns([5, 1])

with col_title:
    now_str = datetime.now().strftime("🕐 更新时间：%Y-%m-%d %H:%M:%S")
    st.markdown(f"""
<div class="header-bar">
  <div class="header-left">
    <div class="main-title">
      <span class="title-icon">🌾</span>稻草一：AI资本开支循环检测
    </div>
    <div class="sub-title">核心检测维度：资本开支扩张速度是否超过收入增长速度</div>
  </div>
</div>
""", unsafe_allow_html=True)

with col_input:
    symbol = st.text_input("股票代码", "NVDA")
    st.markdown(f"""
<div style="text-align:right; margin-top:4px;">
  <span style="color:#64748b; font-size:12px;">🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
</div>
<div style="text-align:right; margin-top:6px;">
  <span class="symbol-badge">标的：{symbol}</span>
</div>
""", unsafe_allow_html=True)

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
# 拉取数据
# =========================================================

income = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}")
cash   = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}")

# =========================================================
# 数据处理
# =========================================================

if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2:

    years, revenue, capex = [], [], []
    n = min(len(income), len(cash))

    for i in range(n):
        years.append(income[i]["date"][:4])
        revenue.append(safe(income[i], "revenue"))
        capex.append(abs(safe(cash[i], "capitalExpenditure")))

    years.reverse(); revenue.reverse(); capex.reverse()

    rev_growth   = (revenue[-1] - revenue[-2]) / revenue[-2]
    capex_growth = (capex[-1]   - capex[-2])   / capex[-2]
    diff         = capex_growth - rev_growth

    # 状态判断
    if diff >= 0.2:
        status, status_color = "过热预警", "yellow"
        status_card_class = "card-status-yellow"
        status_desc = "当前AI资本扩张已进入<br>高波动风险阶段。"
        status_icon = "⚠️"
        alert_title = "结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段"
        alert_body  = f'当前资本开支增速比收入增速高出 <span class="yellow"><b>{diff*100:.2f}%</b></span>，显示企业在AI基础设施上的投入扩张已超出现实需求支撑。<br>若该趋势持续，将提升未来盈利与现金流承压风险，需重点跟踪需求兑现情况。'
    elif diff >= 0:
        status, status_color = "偏热", "yellow"
        status_card_class = "card-status-yellow"
        status_desc = "资本扩张开始领先收入增长。<br>系统进入高估值区间。"
        status_icon = "⚠️"
        alert_title = "结论：资本开支增速开始超出收入增速，进入偏热区间"
        alert_body  = f'当前资本开支增速比收入增速高出 <span class="yellow"><b>{diff*100:.2f}%</b></span>，资本扩张速度开始领先收入增长，需关注需求兑现节奏。'
    else:
        status, status_color = "健康", "green"
        status_card_class = "card-status-green"
        status_desc = "收入增长仍高于资本扩张。<br>AI需求尚能支撑投资。"
        status_icon = "✅"
        alert_title = "结论：当前AI投资处于健康扩张阶段"
        alert_body  = f'收入增速高于资本开支增速，差值为 <span class="green"><b>{abs(diff)*100:.2f}%</b></span>，AI基础设施投入与现实需求匹配良好。'

    # =========================================================
    # 顶部四张卡片
    # =========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
<div class="metric-card card-green">
  <div class="metric-label">收入增长率 (YoY)</div>
  <div class="metric-value-row">
    <div class="metric-number green">{rev_growth*100:.2f}%</div>
    <div class="metric-arrow green">↗</div>
  </div>
  <div class="metric-desc">AI需求仍维持高增长。<br>当前收入扩张速度保持强劲。</div>
</div>
""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
<div class="metric-card card-red">
  <div class="metric-label">资本开支增长率 (YoY)</div>
  <div class="metric-value-row">
    <div class="metric-number red">{capex_growth*100:.2f}%</div>
    <div class="metric-arrow red">↗</div>
  </div>
  <div class="metric-desc">企业正在加速AI基础设施投入。<br>CapEx扩张速度持续提升。</div>
</div>
""", unsafe_allow_html=True)

    with c3:
        diff_sign = "+" if diff >= 0 else ""
        st.markdown(f"""
<div class="metric-card card-yellow">
  <div class="metric-label">增速差 (CapEx - Revenue)</div>
  <div class="metric-value-row">
    <div class="metric-number yellow">{diff_sign}{diff*100:.2f}%</div>
  </div>
  <div class="metric-desc">资本扩张速度已开始超过<br>收入增长速度。</div>
</div>
""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
<div class="metric-card {status_card_class}">
  <div class="metric-label">状态判断</div>
  <div class="metric-value-row">
    <div class="metric-number {status_color}">{status}</div>
    <div class="metric-arrow {status_color}">{status_icon}</div>
  </div>
  <div class="metric-desc">{status_desc}</div>
</div>
""", unsafe_allow_html=True)

    # =========================================================
    # Alert
    # =========================================================

    st.markdown(f"""
<div class="alert-box">
  <div class="alert-icon">⚠️</div>
  <div class="alert-content">
    <div class="alert-title">{alert_title}</div>
    <div class="alert-text">{alert_body}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # =========================================================
    # 下方：左侧逻辑 + 右侧图表
    # =========================================================

    left_panel, right_panel = st.columns([1, 1.5])

    with left_panel:
        st.markdown(f"""
<div class="panel">
  <div class="panel-title">⚙️ 检测逻辑</div>

  <div class="logic-step">
    <div class="step-badge step-badge-blue">1</div>
    <div class="step-text">获取最新两个财年数据：收入、资本开支</div>
  </div>

  <div class="logic-step">
    <div class="step-badge step-badge-blue">2</div>
    <div class="step-text">计算收入增长率 = (本期收入 - 上期收入) / 上期收入</div>
  </div>

  <div class="logic-step">
    <div class="step-badge step-badge-blue">3</div>
    <div class="step-text">计算资本开支增长率 = (本期资本开支 - 上期资本开支) / 上期资本开支</div>
  </div>

  <div class="logic-step">
    <div class="step-badge step-badge-blue">4</div>
    <div class="step-text">计算增速差 = 资本开支增长率 - 收入增长率</div>
  </div>

  <div class="logic-step">
    <div class="step-badge step-badge-blue">5</div>
    <div class="step-text">根据阈值判断状态：</div>
  </div>

  <div style="margin-left: 34px; margin-top: 4px;">
    <div class="threshold-row">
      <div class="threshold-dot" style="background:#ef4444;"></div>
      <div class="threshold-label">增速差 ≥ 20%</div>
      <div class="threshold-arrow">→</div>
      <div class="threshold-status red">过热预警（红色）</div>
    </div>
    <div class="threshold-row">
      <div class="threshold-dot" style="background:#fbbf24;"></div>
      <div class="threshold-label">0% ≤ 增速差 &lt; 20%</div>
      <div class="threshold-arrow">→</div>
      <div class="threshold-status yellow">偏离预警（黄色）</div>
    </div>
    <div class="threshold-row">
      <div class="threshold-dot" style="background:#22c55e;"></div>
      <div class="threshold-label">增速差 &lt; 0%</div>
      <div class="threshold-arrow">→</div>
      <div class="threshold-status green">健康（绿色）</div>
    </div>
  </div>

</div>
""", unsafe_allow_html=True)

    with right_panel:
        st.markdown("""
<div class="panel">
<div class="panel-title">📈 趋势对比（最近5年）</div>
""", unsafe_allow_html=True)

        rev_growths, capex_growths = [], []
        for i in range(1, len(revenue)):
            rev_growths.append(((revenue[i] - revenue[i-1]) / revenue[i-1]) * 100)
            capex_growths.append(((capex[i] - capex[i-1]) / capex[i-1]) * 100)

        chart_years = years[1:]

        # 末尾数值标签
        annotations = [
            dict(
                x=chart_years[-1], y=rev_growths[-1],
                text=f"<b>{rev_growths[-1]:.2f}%</b>",
                showarrow=False, xanchor="left", xshift=8,
                font=dict(color="#22c55e", size=13)
            ),
            dict(
                x=chart_years[-1], y=capex_growths[-1],
                text=f"<b>{capex_growths[-1]:.2f}%</b>",
                showarrow=False, xanchor="left", xshift=8,
                font=dict(color="#ef4444", size=13)
            ),
        ]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=chart_years, y=rev_growths,
            mode="lines+markers", name="收入增长率(%)",
            line=dict(color="#22c55e", width=2.5),
            marker=dict(size=7, color="#22c55e")
        ))

        fig.add_trace(go.Scatter(
            x=chart_years, y=capex_growths,
            mode="lines+markers", name="资本开支增长率(%)",
            line=dict(color="#ef4444", width=2.5),
            marker=dict(size=7, color="#ef4444")
        ))

        fig.update_layout(
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", size=12),
            legend=dict(
                orientation="h", y=1.1,
                font=dict(size=12, color="#cbd5e1"),
                bgcolor="rgba(0,0,0,0)"
            ),
            margin=dict(l=10, r=50, t=10, b=10),
            annotations=annotations,
            xaxis=dict(
                showgrid=False, zeroline=False,
                tickfont=dict(color="#64748b"),
                linecolor="rgba(255,255,255,0.05)"
            ),
            yaxis=dict(
                title="增长率 (%)",
                gridcolor="rgba(255,255,255,0.05)",
                zeroline=True,
                zerolinecolor="rgba(255,255,255,0.1)",
                tickfont=dict(color="#64748b"),
                title_font=dict(color="#64748b")
            )
        )

        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================
    # Footer
    # =========================================================

    st.markdown("""
<div class="footer">
数据来源：Financial Modeling Prep（FMP）｜单位：USD｜更新频率：实时
</div>
""", unsafe_allow_html=True)

else:
    st.error("API数据加载失败，请检查股票代码是否正确。")
