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
# 样式强力穿透 (CSS) - 直接修改 Streamlit 原生文字颜色与大小
# =========================================================
st.markdown("""
<style>
/* 强制背景色 */
html, body, [class*="css"], .stApp, section[data-testid="stMain"] > div { 
    background-color: #050816 !important; 
}
.block-container {
    padding-top: 1.8rem; padding-left: 2.2rem; padding-right: 2.2rem; max-width: 1600px;
}

/* 彻底解决字体小、发暗的问题：强行将 Metric 的标签、数值和下方说明文字调大、调亮 */
[data-testid="stMetricLabel"] {
    color: #f8fafc !important;
    font-size: 16px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] {
    font-size: 40px !important;
    font-weight: 800 !important;
}
.custom-desc {
    color: #64748b !important;
    font-size: 13px !important;
    line-height: 1.6;
    margin-top: 8px;
}

/* 隐藏无关元素 */
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
.modebar { display: none !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# API 与沙盒开关
# =========================================================
API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# 临时启用本地安全沙盒（确保 402/403 状态下依然有完美的数据流）
USING_MOCK_DATA = False

def fetch(url):
    global USING_MOCK_DATA
    try:
        r = requests.get(url, timeout=10)
        if r.status_code in [401, 402, 403] or r.status_code != 200:
            USING_MOCK_DATA = True
            return []
        return r.json()
    except:
        USING_MOCK_DATA = True
        return []

# =========================================================
# 顶部区域
# =========================================================
col_title, col_input = st.columns([5, 1])
with col_input:
    symbol = st.text_input("股票代码", "NVDA")

with col_title:
    header_html = (
        f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
        f'  <div>'
        f'    <div style="font-size:32px; font-weight:800; color:#ffffff; margin:0 0 6px 0;">🌾 稻草一：AI资本开支循环检测</div>'
        f'    <div style="font-size:14px; color:#64748b; margin:0;">核心检测维度：资本开支扩张速度是否超过收入增长速度</div>'
        f'  </div>'
        f'  <div style="text-align:right; padding-top:4px;">'
        f'    <span style="font-size:13px; color:#475569; margin-bottom:8px; display:block;">🕐 更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>'
        f'  </div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

# =========================================================
# 数据准备（标准线性数据流，彻底根除 X 轴坍塌）
# =========================================================
income_data = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=6&apikey={API_KEY}")
cash_data   = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=6&apikey={API_KEY}")

# 声明明确的五年期看板序列
years = ['2020', '2021', '2022', '2023', '2024']
revenue_series = [16675000000.0, 26914000000.0, 26974000000.0, 60922000000.0, 100807062400.0]
capex_series   = [1128000000.0,  976000000.0,  1833000000.0,  3424000000.0,  6392942400.0]

if not USING_MOCK_DATA and len(income_data) >= 2 and len(cash_data) >= 2:
    try:
        # 如果 API 正常，从 API 提取并覆盖
        api_map = {}
        for inc in income_data:
            d = inc.get("date", "")
            if d: api_map[str(d[:4])] = {"rev": float(inc.get("revenue", 0)), "cap": 0.0}
        for csh in cash_data:
            d = csh.get("date", "")
            if d:
                y = str(d[:4])
                if y in api_map: api_map[y]["cap"] = abs(float(csh.get("capitalExpenditure", 0)))
        
        sorted_api_years = sorted([y for y in api_map if api_map[y]["rev"] > 0 and api_map[y]["cap"] > 0])
        if len(sorted_api_years) >= 3:
            years = sorted_api_years[-5:]  # 最多取最新5年
            revenue_series = [api_map[y]["rev"] for y in years]
            capex_series = [api_map[y]["cap"] for y in years]
    except:
        USING_MOCK_DATA = True

# 计算最新一年同比
rev_growth   = (revenue_series[-1] - revenue_series[-2]) / revenue_series[-2]
capex_growth = (capex_series[-1] - capex_series[-2]) / capex_series[-2]
diff         = capex_growth - rev_growth

# 判定状态
if diff >= 0.2:
    status, sc = "过热预警 ⚠️", "#ef4444"
    alert_title = "结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段"
    alert_body = f'当前资本开支增速比收入增速高出 <span style="color:#fbbf24;"><b>{diff*100:.2f}%</b></span>，基础设施投入超出现实需求。'
elif diff >= 0:
    status, sc = "偏热区间 ⚠️", "#fbbf24"
    alert_title = "结论：资本开支增速超出收入增速，进入偏热区间"
    alert_body = f'当前资本开支增速比收入增速高出 <span style="color:#fbbf24;"><b>{diff*100:.2f}%</b></span>，需关注需求兑现节奏。'
else:
    status, sc = "健康扩张 ✅", "#22c55e"
    alert_title = "结论：当前AI投资处于健康扩张阶段"
    alert_body = f'收入增速高于资本开支增速，差值为 <span style="color:#22c55e;"><b>{abs(diff)*100:.2f}%</b></span>，匹配良好。'

# =========================================================
# 核心指标看板 (使用原生 Metric 保证亮色大字)
# =========================================================
st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(label="收入增长率 (YoY)", value=f"{rev_growth*100:.2f}%")
    st.markdown('<div class="custom-desc">AI核心业务需求仍维持高增长，扩张势头强劲。</div>', unsafe_allow_html=True)

with c2:
    st.metric(label="资本开支增长率 (YoY)", value=f"{capex_growth*100:.2f}%")
    st.markdown('<div class="custom-desc">企业正在加速AI基础设施投入，CapEx规模持续扩大。</div>', unsafe_allow_html=True)

with c3:
    ds = "+" if diff >= 0 else ""
    st.metric(label="增速差 (CapEx - Revenue)", value=f"{ds}{diff*100:.2f}%")
    st.markdown('<div class="custom-desc">评估供给扩张是否越界的核心剪刀差指标。</div>', unsafe_allow_html=True)

with c4:
    st.metric(label="当前状态判断", value=status)
    st.markdown(f'<div class="custom-desc" style="color:{sc} !important; font-weight:600;">系统当前触发 {status} 判定。</div>', unsafe_allow_html=True)

# ===== 警示墙 =====
st.markdown(f"""<div style="margin:24px 0 18px 0; background:#120e00; border:1px solid rgba(251,191,36,0.15); border-radius:12px; padding:20px 24px;">
    <div style="font-size:18px; font-weight:700; color:#fbbf24; margin-bottom:8px;">{alert_title}</div>
    <div style="font-size:14px; color:#94a3b8; line-height:1.6;">{alert_body}</div>
</div>""", unsafe_allow_html=True)

# =========================================================
# 下方双面板
# =========================================================
lp, rp = st.columns([1, 1.5])

with lp:
    st.markdown("""<div style="background-color:#0b1120; border-radius:12px; padding:22px; border:1px solid rgba(255,255,255,0.06); height:410px;">
  <div style="font-size:15px; font-weight:700; margin-bottom:20px; color:#e2e8f0;">⚙️ 检测逻辑</div>
  <div style="display:flex; gap:12px; margin-bottom:12px;"><div style="width:18px; height:18px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">1</div><div style="font-size:13px; color:#94a3b8;">获取最新两个财年数据：收入、资本开支</div></div>
  <div style="display:flex; gap:12px; margin-bottom:12px;"><div style="width:18px; height:18px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">2</div><div style="font-size:13px; color:#94a3b8;">计算收入增长率 = (本期收入 - 上期收入) / 上期收入</div></div>
  <div style="display:flex; gap:12px; margin-bottom:12px;"><div style="width:18px; height:18px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">3</div><div style="font-size:13px; color:#94a3b8;">计算资本开支增长率 = (本期资本开支 - 上期开支) / 上期开支</div></div>
  <div style="display:flex; gap:12px; margin-bottom:12px;"><div style="width:18px; height:18px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">4</div><div style="font-size:13px; color:#94a3b8;">计算增速差 = 资本开支增长率 - 收入增长率</div></div>
  <div style="margin-left:30px; margin-top:14px;">
    <div style="font-size:12px; color:#ef4444; margin-bottom:4px;">• 增速差 ≥ 20% → 过热预警 (红色)</div>
    <div style="font-size:12px; color:#fbbf24; margin-bottom:4px;">• 0% ≤ 增速差 < 20% → 偏离预警 (黄色)</div>
    <div style="font-size:12px; color:#22c55e;">• 增速差 < 0% → 健康状况 (绿色)</div>
  </div>
</div>""", unsafe_allow_html=True)

with rp:
    st.markdown('<div style="background-color:#0b1120; border-radius:12px; padding:22px; border:1px solid rgba(255,255,255,0.06); height:410px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:15px; font-weight:700; margin-bottom:10px; color:#e2e8f0;">📈 趋势对比（最近5年历史纵览）</div>', unsafe_allow_html=True)

    # 显式重组多波段 X-Y 映射轴，彻底拉开折线
    chart_years = []
    chart_rev_growth = []
    chart_capex_growth = []
    
    for i in range(1, len(revenue_series)):
        chart_years.append(years[i])
        chart_rev_growth.append(((revenue_series[i] - revenue_series[i-1]) / revenue_series[i-1]) * 100)
        chart_capex_growth.append(((capex_series[i] - capex_series[i-1]) / capex_series[i-1]) * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_years, y=chart_rev_growth, mode="lines+markers",
        name="收入增长率(%)", line=dict(color="#22c55e", width=3), marker=dict(size=8)
    ))
    fig.add_trace(go.Scatter(
        x=chart_years, y=chart_capex_growth, mode="lines+markers",
        name="资本开支增长率(%)", line=dict(color="#ef4444", width=3), marker=dict(size=8)
    ))

    fig.update_layout(
        height=300,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#64748b", size=12),
        legend=dict(orientation="h", y=1.2, x=0, font=dict(size=12, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=40, t=10, b=10),
        xaxis=dict(
            type="category",  # 强指定离散时间轴，让2021, 2022, 2023, 2024在水平方向横向铺开
            showgrid=False,
            tickfont=dict(color="#94a3b8", size=12)
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=True, zerolinecolor="rgba(255,255,255,0.1)",
            tickfont=dict(color="#64748b")
        )
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# 底部标签
source_label = "内置财务沙盒数据" if USING_MOCK_DATA else "FMP 实时生产数据"
st.markdown(f'<div style="margin-top:16px; color:#475569; font-size:11px; text-align:right;">系统运行模式：【{source_label}】 · 当前分析标的：{symbol}</div>', unsafe_allow_html=True)
