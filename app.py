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
# API 核心配置
# =========================================================

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =========================================================
# CSS 样式完全留存
# =========================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    background-color: #050816 !important;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.stApp { background-color: #050816 !important; }
section[data-testid="stMain"] > div { background-color: #050816 !important; }
.block-container {
    padding-top: 1.8rem;
    padding-left: 2.2rem;
    padding-right: 2.2rem;
    max-width: 1600px;
    background-color: #050816 !important;
}

/* 标题 */
.main-title {
    font-size: 32px; font-weight: 800; color: #ffffff;
    margin: 0 0 6px 0; letter-spacing: -0.5px;
    display: flex; align-items: center; gap: 10px;
}

/* 核心检测维度副标题 */
.sub-title { 
    font-size: 16px !important; 
    color: #cbd5e1 !important; 
    margin: 0; 
}

.timestamp-text { font-size: 13px; color: #475569; margin-bottom: 8px; display: block; }
.symbol-badge {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 3px 16px;
    font-size: 13px; font-weight: 600; color: #94a3b8; letter-spacing: 1px;
}

/* 输入框 */
.stTextInput input {
    background-color: #0f172a !important; color: white !important;
    border-radius: 10px !important; border: 1px solid rgba(255,255,255,0.1) !important;
    font-size: 14px !important;
}
.stTextInput label { color: #94a3b8 !important; font-size: 13px !important; }

/* Metric 卡片 */
.metric-card {
    background-color: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 20px 22px 18px;
    height: 168px;
}

.metric-label {
    color: #ffffff; font-size: 15px; font-weight: 600;
    margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.4px;
}
.metric-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 14px; }
.metric-number { font-size: 38px; font-weight: 800; line-height: 1; letter-spacing: -1.5px; }
.metric-arrow { font-size: 20px; font-weight: 700; }

/* 卡片下方描述文字 */
.metric-desc, .metric-desc p { 
    color: #cbd5e1 !important; 
    font-size: 15px !important; 
    line-height: 1.6; 
}

.green { color: #22c55e; } .red { color: #ef4444; } .yellow { color: #fbbf24; }

/* Alert 结论框 */
.alert-box {
    margin: 18px 0; background: #120e00;
    border: 1px solid rgba(251,191,36,0.18);
    border-radius: 14px; padding: 22px 26px;
    display: flex; gap: 18px; align-items: flex-start;
}
.alert-icon { font-size: 44px; flex-shrink: 0; line-height: 1; }

/* 结论框标题 */
.alert-title { 
    font-size: 23px !important; 
    font-weight: 700; 
    color: #fbbf24; 
    margin-bottom: 10px; 
}

/* 结论框正文描述 */
.alert-text, .alert-text p { 
    font-size: 17px !important; 
    color: #cbd5e1 !important; 
    line-height: 1.75; 
}

/* Panel */
.panel {
    background-color: #0b1120; border-radius: 14px;
    padding: 22px; border: 1px solid rgba(255,255,255,0.07);
}

/* 面板标题样式 */
.panel-title { 
    font-size: 20px !important; 
    font-weight: 700; 
    margin-bottom: 20px; 
    color: #e2e8f0; 
}

/* 检测逻辑文本样式 */
.logic-step { display: flex; gap: 12px; margin-bottom: 13px; align-items: flex-start; }
.step-num {
    width: 22px; height: 22px; min-width: 22px; border-radius: 50%;
    background: #1e3a5f; color: #60a5fa; font-size: 12px; font-weight: 700;
    display: flex; align-items: center; justify-content: center; margin-top: 2px;
}
.step-text, .logic-step p { 
    font-size: 16px !important; 
    color: #cbd5e1 !important; 
    line-height: 1.6; 
}

.threshold-block { margin-left: 34px; margin-top: 8px; }
.threshold-row {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 12px; border-radius: 7px; margin-bottom: 6px;
    background: rgba(255,255,255,0.02);
}
.t-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

/* 下层条件阈值说明文字 */
.t-label, .threshold-row p { 
    font-size: 15px !important; 
    color: #cbd5e1 !important; 
    flex: 1; 
}
.t-arrow { font-size: 13px; color: #475569; }
.t-status { font-size: 15px !important; font-weight: 600; }

.footer-text { margin-top: 14px; color: #1e293b; font-size: 11px; text-align: right; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
.modebar { display: none !important; }

</style>
""", unsafe_allow_html=True)

# =========================================================
# 工具函数
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
# 顶部控制流
# =========================================================

col_title, col_input = st.columns([5, 1])

with col_input:
    symbol = st.text_input("股票代码", "NVDA")

with col_title:
    st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start;">
  <div>
    <div class="main-title">🌾 稻草一：AI资本开支循环检测</div>
    <div class="sub-title">核心检测维度：资本开支扩张速度是否超过收入增长速度</div>
  </div>
  <div style="text-align:right; padding-top:4px;">
    <span class="timestamp-text">🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    <span class="symbol-badge">标的：{symbol}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 核心突围：通过混合拉取“年报接口”与“季报接口”突破 FMP 5条限制
# =========================================================

# 1. 抓取标准年报 (包含最新5个财年)
inc_annual = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=5&apikey={API_KEY}")
cash_annual = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=5&apikey={API_KEY}")

# 2. 抓取季报 (额外获得10-20个季度，用于向上融合成更早的完整财年)
inc_quarterly = fetch(f"{BASE}/income-statement?symbol={symbol}&period=quarter&limit=20&apikey={API_KEY}")
cash_quarterly = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&period=quarter&limit=20&apikey={API_KEY}")

# =========================================================
# 融合同步逻辑
# =========================================================

income_pool = {}
cash_pool = {}

# 塞入标准年报原始值
if isinstance(inc_annual, list):
    for item in inc_annual:
        if "calendarYear" in item:
            y = int(item["calendarYear"])
            income_pool[y] = safe(item, "revenue")

if isinstance(cash_annual, list):
    for item in cash_annual:
        if "calendarYear" in item:
            y = int(item["calendarYear"])
            cash_pool[y] = abs(safe(item, "capitalExpenditure"))

# 提取季度数据融合成更久远的财年（补足年报接口死活拿不到的 2019, 2020 原始值）
q_inc_map = {}
if isinstance(inc_quarterly, list):
    for item in inc_quarterly:
        try:
            y = int(item.get("calendarYear", item.get("date", "")[:4]))
            q_inc_map[y] = q_inc_map.get(y, 0) + safe(item, "revenue")
        except: pass

q_csh_map = {}
if isinstance(cash_quarterly, list):
    for item in cash_quarterly:
        try:
            y = int(item.get("calendarYear", item.get("date", "")[:4]))
            q_csh_map[y] = q_csh_map.get(y, 0) + abs(safe(item, "capitalExpenditure"))
        except: pass

# 如果年报缺失更早年份，用融合的季度总数补齐
for y in q_inc_map:
    if y not in income_pool:
        income_pool[y] = q_inc_map[y]
for y in q_csh_map:
    if y not in cash_pool:
        cash_pool[y] = q_csh_map[y]

# 组装最终时间轴
final_timeline = []
for y in sorted(income_pool.keys()):
    if y in cash_pool and income_pool[y] > 0 and cash_pool[y] > 0:
        final_timeline.append({
            "year": y,
            "revenue": income_pool[y],
            "capex": cash_pool[y]
        })

# =========================================================
# 视图与看板渲染
# =========================================================

if len(final_timeline) >= 2:

    # 计算最新财年的增长率与增速差
    rev_growth   = (final_timeline[-1]["revenue"] - final_timeline[-2]["revenue"]) / final_timeline[-2]["revenue"]
    capex_growth = (final_timeline[-1]["capex"] - final_timeline[-2]["capex"]) / final_timeline[-2]["capex"]
    diff         = capex_growth - rev_growth

    # 状态判断
    if diff >= 0.2:
        status, sc, si = "过热预警", "yellow", "⚠️"
        status_desc  = "当前AI资本扩张已进入<br>高波动风险阶段。"
        alert_title  = "结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段"
        alert_body   = (f'当前资本开支增速比收入增速高出 <span class="yellow"><b>{diff*100:.2f}%</b></span>，'
                        f'企业AI基础设施投入已超出现实需求支撑。<br>'
                        f'若趋势持续，将提升未来盈利与现金流承压风险，需重点跟踪需求兑现情况。')
    elif diff >= 0:
        status, sc, si = "偏热", "yellow", "⚠️"
        status_desc  = "资本扩张开始领先收入增长。<br>系统进入高估值区间。"
        alert_title  = "结论：资本开支增速超出收入增速，进入偏热区间"
        alert_body   = (f'当前资本开支增速比收入增速高出 <span class="yellow"><b>{diff*100:.2f}%</b></span>，'
                        f'资本扩张速度开始领先，需关注需求兑现节奏。')
    else:
        status, sc, si = "健康", "green", "✅"
        status_desc  = "收入增长仍高于资本扩张。<br>AI需求尚能支撑投资。"
        alert_title  = "结论：当前AI投资处于健康扩张阶段"
        alert_body   = (f'收入增速高于资本开支增速，差值为 <span class="green"><b>{abs(diff)*100:.2f}%</b></span>，'
                        f'AI基础设施投入与现实需求匹配良好。')

    # ===== 四张卡片 =====
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""<div class="metric-card">
  <div class="metric-label">收入增长率 (YoY)</div>
  <div class="metric-row"><span class="metric-number green">{rev_growth*100:.2f}%</span><span class="metric-arrow green">↗</span></div>
  <div class="metric-desc">AI需求仍维持高增长。<br>当前收入扩张速度保持强劲.</div>
</div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""<div class="metric-card">
  <div class="metric-label">资本开支增长率 (YoY)</div>
  <div class="metric-row"><span class="metric-number red">{capex_growth*100:.2f}%</span><span class="metric-arrow red">↗</span></div>
  <div class="metric-desc">企业正在加速AI基础设施投入。<br>CapEx扩张速度持续提升.</div>
</div>""", unsafe_allow_html=True)

    with c3:
        ds = "+" if diff >= 0 else ""
        st.markdown(f"""<div class="metric-card">
  <div class="metric-label">增速差 (CapEx - Revenue)</div>
  <div class="metric-row"><span class="metric-number yellow">{ds}{diff*100:.2f}%</span></div>
  <div class="metric-desc">资本扩张速度已开始超过<br>收入增长速度。</div>
</div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""<div class="metric-card">
  <div class="metric-label">状态判断</div>
  <div class="metric-row"><span class="metric-number {sc}">{status}</span><span class="metric-arrow {sc}">{si}</span></div>
  <div class="metric-desc">{status_desc}</div>
</div>""", unsafe_allow_html=True)

    # ===== Alert =====
    st.markdown(f"""<div class="alert-box">
  <div class="alert-icon">⚠️</div>
  <div class="alert-text"><div class="alert-title">{alert_title}</div><div>{alert_body}</div></div>
</div>""", unsafe_allow_html=True)

    # ===== 下方面板 =====
    lp, rp = st.columns([1, 1.5])

    with lp:
        st.markdown("""<div class="panel">
  <div class="panel-title">⚙️ 检测逻辑</div>
  <div class="logic-step"><div class="step-num">1</div><div class="step-text">获取最新两个财年数据：收入、资本开支</div></div>
  <div class="logic-step"><div class="step-num">2</div><div class="step-text">计算收入增长率 = (本期收入 - 上期收入) / 上期收入</div></div>
  <div class="logic-step"><div class="step-num">3</div><div class="step-text">计算资本开支增长率 = (本期资本开支 - 上期资本开支) / 上期资本开支</div></div>
  <div class="logic-step"><div class="step-num">4</div><div class="step-text">计算增速差 = 资本开支增长率 - 收入增长率</div></div>
  <div class="logic-step"><div class="step-num">5</div><div class="step-text">根据阈值判断状态：</div></div>
  <div class="threshold-block">
    <div class="threshold-row"><div class="t-dot" style="background:#ef4444;"></div><div class="t-label">增速差 ≥ 20%</div><div class="t-arrow">→</div><div class="t-status red">过热预警（红色）</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#fbbf24;"></div><div class="t-label">0% ≤ 增速差 &lt; 20%</div><div class="t-arrow">→</div><div class="t-status yellow">偏离预警（黄色）</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#22c55e;"></div><div class="t-label">增速差 &lt; 0%</div><div class="t-arrow">→</div><div class="t-status green">健康（绿色）</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    with rp:
        st.markdown('<div class="panel"><div class="panel-title">📈 趋势对比</div>', unsafe_allow_html=True)

        # 核心趋势线组装
        rg_list, cg_list, cy_list = [], [], []
        for i in range(1, len(final_timeline)):
            prev = final_timeline[i-1]
            curr = final_timeline[i]
            if prev["revenue"] > 0 and prev["capex"] > 0:
                # 限制图表起始轴为 2021 年，但因为有了多季度前置融合，2021年现在能顺利算出同比值！
                if curr["year"] >= 2021:
                    rg_list.append(((curr["revenue"] - prev["revenue"]) / prev["revenue"]) * 100)
                    cg_list.append(((curr["capex"] - prev["capex"]) / prev["capex"]) * 100)
                    cy_list.append(curr["year"])

        fig = go.Figure()
        
        if cy_list:
            fig.add_trace(go.Scatter(x=cy_list, y=rg_list, mode="lines+markers",
                name="收入增长率(%)", line=dict(color="#22c55e", width=2.5), marker=dict(size=7)))
            fig.add_trace(go.Scatter(x=cy_list, y=cg_list, mode="lines+markers",
                name="资本开支增长率(%)", line=dict(color="#ef4444", width=2.5), marker=dict(size=7)))

            annotations = [
                dict(x=cy_list[-1], y=rg_list[-1], text=f"<b>{rg_list[-1]:.2f}%</b>",
                     showarrow=False, xanchor="left", xshift=10, font=dict(color="#22c55e", size=13)),
                dict(x=cy_list[-1], y=cg_list[-1], text=f"<b>{cg_list[-1]:.2f}%</b>",
                     showarrow=False, xanchor="left", xshift=10, font=dict(color="#ef4444", size=13)),
            ]
        else:
            annotations = []

        # 画布自适应布局
        fig.update_layout(
            height=340,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#64748b", size=12),
            legend=dict(orientation="h", y=1.1, font=dict(size=12, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=10, r=60, t=10, b=10),
            annotations=annotations,
            xaxis=dict(
                type="linear",
                tickvals=cy_list,
                ticktext=[str(y) for y in cy_list],
                showgrid=False, 
                zeroline=False,
                tickfont=dict(color="#64748b", size=11)
            ),
            yaxis=dict(
                title="增长率 (%)",
                gridcolor="rgba(255,255,255,0.05)",
                zeroline=True, zerolinecolor="rgba(255,255,255,0.08)",
                tickfont=dict(color="#64748b"), title_font=dict(color="#64748b", size=11)
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f'<div class="footer-text">数据来源：Financial Modeling Prep (FMP) · 混合采集架构 · 当前标的：{symbol}</div>',
                unsafe_allow_html=True)

else:
    st.error(f"API数据加载失败，请检查股票代码是否正确。")
