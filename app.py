import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="AI资本开支风险系统", layout="wide")

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"

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
.main-title {
    font-size: 32px; font-weight: 800; color: #ffffff;
    margin: 0 0 6px 0; letter-spacing: -0.5px;
    display: flex; align-items: center; gap: 10px; line-height: 1.2;
}
.sub-title { font-size: 13px; color: #475569; margin: 0; }
.timestamp-text { font-size: 13px; color: #475569; margin-bottom: 8px; display: block; }
.symbol-badge {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 3px 16px;
    font-size: 13px; font-weight: 600; color: #94a3b8; letter-spacing: 1px;
}
.stTextInput input {
    background-color: #0f172a !important; color: white !important;
    border-radius: 10px !important; border: 1px solid rgba(255,255,255,0.1) !important;
    font-size: 14px !important;
}
.stTextInput label { color: #94a3b8 !important; font-size: 13px !important; }
.metric-card {
    background-color: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 20px 22px 18px;
    height: 168px; position: relative; overflow: hidden;
}
.metric-label {
    color: #64748b; font-size: 12px; font-weight: 500;
    margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.4px;
}
.metric-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 14px; }
.metric-number { font-size: 38px; font-weight: 800; line-height: 1; letter-spacing: -1.5px; }
.metric-arrow { font-size: 20px; font-weight: 700; line-height: 1; }
.metric-desc { color: #64748b; font-size: 12px; line-height: 1.65; }
.green { color: #22c55e; } .red { color: #ef4444; } .yellow { color: #fbbf24; }
.alert-box {
    margin: 18px 0; background: #120e00;
    border: 1px solid rgba(251,191,36,0.18);
    border-radius: 14px; padding: 22px 26px;
    display: flex; gap: 18px; align-items: flex-start;
}
.alert-icon { font-size: 44px; flex-shrink: 0; line-height: 1; }
.alert-title { font-size: 20px; font-weight: 700; color: #fbbf24; margin-bottom: 10px; line-height: 1.3; }
.alert-text { font-size: 14px; color: #94a3b8; line-height: 1.75; }
.panel {
    background-color: #0b1120; border-radius: 14px;
    padding: 22px; border: 1px solid rgba(255,255,255,0.07);
}
.panel-title { font-size: 15px; font-weight: 700; margin-bottom: 20px; color: #e2e8f0; }
.logic-step { display: flex; gap: 12px; margin-bottom: 13px; align-items: flex-start; }
.step-num {
    width: 20px; height: 20px; min-width: 20px; border-radius: 50%;
    background: #1e3a5f; color: #60a5fa; font-size: 11px; font-weight: 700;
    display: flex; align-items: center; justify-content: center; margin-top: 2px;
}
.step-text { font-size: 13px; color: #94a3b8; line-height: 1.6; }
.threshold-block { margin-left: 32px; margin-top: 8px; }
.threshold-row {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 10px; border-radius: 7px; margin-bottom: 5px;
    background: rgba(255,255,255,0.02);
}
.t-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.t-label { font-size: 12px; color: #475569; flex: 1; }
.t-arrow { font-size: 11px; color: #475569; }
.t-status { font-size: 12px; font-weight: 600; }
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
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        data = r.json()
        # FMP 有时返回 {"error": "..."} 或 {"message": "..."}
        if isinstance(data, dict):
            msg = data.get("error") or data.get("message") or str(data)
            return None, msg
        return data, None
    except Exception as e:
        return None, str(e)

def safe(x, k):
    try:
        return float(x.get(k) or 0)
    except:
        return 0.0

def dedup_annual(records):
    """
    FMP stable 接口返回的是最新数据，可能混入季度记录。
    用 fiscalDateEnding 或 date 字段的年份去重，每年只保留最新一条（通常是年报）。
    同时过滤掉 period != 'FY' 的季报条目（如果有该字段）。
    """
    seen = {}
    for rec in records:
        # 优先用 calendarYear，其次取 date 前4位
        year = str(rec.get("calendarYear", "") or rec.get("date", "")[:4])
        if not year.isdigit():
            continue
        period = rec.get("period", "FY")
        # 跳过明确标注为季报的条目
        if period and period.upper() not in ("FY", "TTM", ""):
            continue
        if year not in seen:
            seen[year] = rec
    # 按年份升序返回
    return [seen[y] for y in sorted(seen.keys())]

# =========================================================
# 顶部布局
# =========================================================

col_title, col_input = st.columns([5, 1])
with col_input:
    symbol = st.text_input("股票代码", "NVDA").upper().strip()

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
# 拉取数据 — 同时尝试 stable 和 v3 两套接口
# =========================================================

# 优先用 stable（原代码接口），如失败回退 v3
URLS = {
    "income_stable": f"https://financialmodelingprep.com/stable/income-statement?symbol={symbol}&limit=7&apikey={API_KEY}",
    "cash_stable":   f"https://financialmodelingprep.com/stable/cash-flow-statement?symbol={symbol}&limit=7&apikey={API_KEY}",
    "income_v3":     f"https://financialmodelingprep.com/api/v3/income-statement/{symbol}?limit=7&apikey={API_KEY}",
    "cash_v3":       f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{symbol}?limit=7&apikey={API_KEY}",
}

income_raw, err_i = fetch(URLS["income_stable"])
cash_raw,   err_c = fetch(URLS["cash_stable"])

# 如果 stable 失败，回退 v3
if income_raw is None:
    income_raw, err_i = fetch(URLS["income_v3"])
if cash_raw is None:
    cash_raw, err_c = fetch(URLS["cash_v3"])

# =========================================================
# 数据清洗：去重保留年度数据
# =========================================================

income = dedup_annual(income_raw) if income_raw else []
cash   = dedup_annual(cash_raw)   if cash_raw   else []

# =========================================================
# 调试面板（开发期可开启，上线时注释掉）
# =========================================================
# with st.expander("🔧 调试信息"):
#     st.write("income条数:", len(income), "| cash条数:", len(cash))
#     if income: st.write("income年份:", [r.get("calendarYear") or r.get("date","")[:4] for r in income])
#     if cash:   st.write("cash年份:",   [r.get("calendarYear") or r.get("date","")[:4] for r in cash])
#     st.write("income_err:", err_i, "| cash_err:", err_c)

# =========================================================
# 数据处理
# =========================================================

if len(income) >= 2 and len(cash) >= 2:

    # 对齐年份（取交集）
    income_dict = {str(r.get("calendarYear") or r.get("date","")[:4]): r for r in income}
    cash_dict   = {str(r.get("calendarYear") or r.get("date","")[:4]): r for r in cash}
    common_years = sorted(set(income_dict.keys()) & set(cash_dict.keys()))

    years, revenue, capex = [], [], []
    for y in common_years:
        rev = safe(income_dict[y], "revenue")
        cap = abs(safe(cash_dict[y],   "capitalExpenditure"))
        if rev > 0:   # 过滤掉无效行
            years.append(y)
            revenue.append(rev)
            capex.append(cap)

    if len(revenue) < 2:
        st.error(f"有效年度数据不足（仅 {len(revenue)} 年），无法计算增长率。请确认 {symbol} 是否已上市超过2年。")
        st.stop()

    rev_growth   = (revenue[-1] - revenue[-2]) / revenue[-2]
    capex_growth = (capex[-1]   - capex[-2])   / capex[-2]
    diff         = capex_growth - rev_growth

    # ===== 状态判断 =====
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
  <div class="metric-desc">AI需求仍维持高增长。<br>当前收入扩张速度保持强劲。</div>
</div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""<div class="metric-card">
  <div class="metric-label">资本开支增长率 (YoY)</div>
  <div class="metric-row"><span class="metric-number red">{capex_growth*100:.2f}%</span><span class="metric-arrow red">↗</span></div>
  <div class="metric-desc">企业正在加速AI基础设施投入。<br>CapEx扩张速度持续提升。</div>
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
  <div><div class="alert-title">{alert_title}</div><div class="alert-text">{alert_body}</div></div>
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
        st.markdown('<div class="panel"><div class="panel-title">📈 趋势对比（最近5年）</div>', unsafe_allow_html=True)

        rg_list, cg_list, cy_list = [], [], []
        for i in range(1, len(revenue)):
            if revenue[i-1] > 0 and capex[i-1] > 0:
                rg_list.append(((revenue[i] - revenue[i-1]) / revenue[i-1]) * 100)
                cg_list.append(((capex[i]   - capex[i-1])   / capex[i-1])   * 100)
                cy_list.append(years[i])

        annotations = []
        if rg_list:
            annotations.append(dict(x=cy_list[-1], y=rg_list[-1],
                text=f"<b>{rg_list[-1]:.2f}%</b>", showarrow=False,
                xanchor="left", xshift=10, font=dict(color="#22c55e", size=13)))
        if cg_list:
            annotations.append(dict(x=cy_list[-1], y=cg_list[-1],
                text=f"<b>{cg_list[-1]:.2f}%</b>", showarrow=False,
                xanchor="left", xshift=10, font=dict(color="#ef4444", size=13)))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cy_list, y=rg_list, mode="lines+markers",
            name="收入增长率(%)", line=dict(color="#22c55e", width=2.5), marker=dict(size=7)))
        fig.add_trace(go.Scatter(x=cy_list, y=cg_list, mode="lines+markers",
            name="资本开支增长率(%)", line=dict(color="#ef4444", width=2.5), marker=dict(size=7)))
        fig.update_layout(
            height=340,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#64748b", size=12),
            legend=dict(orientation="h", y=1.1, font=dict(size=12, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=10, r=60, t=10, b=10),
            annotations=annotations,
            xaxis=dict(type="category", showgrid=False, zeroline=False, tickfont=dict(color="#64748b", size=11)),
            yaxis=dict(title="增长率 (%)", gridcolor="rgba(255,255,255,0.05)",
                zeroline=True, zerolinecolor="rgba(255,255,255,0.08)",
                tickfont=dict(color="#64748b"), title_font=dict(color="#64748b", size=11))
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f'<div class="footer-text">数据来源：Financial Modeling Prep (FMP) · 年度财报 · 实时采集 · {symbol}</div>', unsafe_allow_html=True)

else:
    # ===== 详细错误诊断 =====
    st.error(f"⚠️ 无法获取 **{symbol}** 的年度财报数据")
    with st.expander("🔧 点击查看诊断信息"):
        st.write(f"- income 原始条数: `{len(income_raw) if income_raw else 0}`")
        st.write(f"- cash 原始条数:   `{len(cash_raw) if cash_raw else 0}`")
        st.write(f"- 清洗后 income 年度条数: `{len(income)}`")
        st.write(f"- 清洗后 cash 年度条数:   `{len(cash)}`")
        st.write(f"- income 错误: `{err_i}`")
        st.write(f"- cash 错误:   `{err_c}`")
        if income_raw:
            st.write("income 原始前3条：", income_raw[:3])
        if cash_raw:
            st.write("cash 原始前3条：", cash_raw[:3])
    st.info("💡 如果诊断信息显示有原始数据，说明是年份去重逻辑的问题，可把诊断信息截图发我。")
