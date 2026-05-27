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
# API — 保持原始接口
# =========================================================
API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE = "https://financialmodelingprep.com/stable"

# =========================================================
# 全局底色强制注入
# =========================================================
st.markdown("""
<style>
html, body, [class*="css"], .stApp, section[data-testid="stMain"] > div { 
    background-color: #050816 !important; 
}
.block-container {
    padding-top: 1.8rem; padding-left: 2.2rem; padding-right: 2.2rem; max-width: 1600px;
}
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
        if r.status_code != 200: return []
        return r.json()
    except:
        return []

def safe(x, k):
    try: return float(x.get(k, 0))
    except: return 0

# =========================================================
# 顶部：标题 + 输入框
# =========================================================
col_title, col_input = st.columns([5, 1])

with col_input:
    symbol = st.text_input("股票代码", "NVDA")

with col_title:
    header_html = (
        f'<div style="display:flex; justify-content:space-between; align-items:flex-start; background-color:#050816;">'
        f'  <div>'
        f'    <div style="font-size:32px; font-weight:800; color:#ffffff; margin:0 0 6px 0; letter-spacing:-0.5px;">🌾 稻草一：AI资本开支循环检测</div>'
        f'    <div style="font-size:14px; color:#64748b; margin:0;">核心检测维度：资本开支扩张速度是否超过收入增长速度</div>'
        f'  </div>'
        f'  <div style="text-align:right; padding-top:4px;">'
        f'    <span style="font-size:13px; color:#475569; margin-bottom:8px; display:block;">🕐 更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>'
        f'    <span style="display:inline-block; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:3px 16px; font-size:13px; font-weight:600; color:#94a3b8;">标的：{symbol}</span>'
        f'  </div>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

# =========================================================
# 数据拉取与精确对齐
# =========================================================
income_data = fetch(f"{BASE}/income-statement?symbol={symbol}&limit=6&apikey={API_KEY}")
cash_data   = fetch(f"{BASE}/cash-flow-statement?symbol={symbol}&limit=6&apikey={API_KEY}")

if isinstance(income_data, list) and isinstance(cash_data, list) and len(income_data) >= 2:
    
    # 建立财年映射，防止两边接口返回的数据年份错位
    data_map = {}
    
    for inc in income_data:
        date_str = inc.get("date", "")
        if date_str:
            year = date_str[:4]
            data_map[year] = {"revenue": safe(inc, "revenue"), "capex": 0.0}
            
    for csh in cash_data:
        date_str = csh.get("date", "")
        if date_str:
            year = date_str[:4]
            if year in data_map:
                data_map[year]["capex"] = abs(safe(csh, "capitalExpenditure"))

    # 按照年份从远到近严格升序排序 (例如: 2021, 2022, 2023, 2024, 2025)
    sorted_years = sorted(list(data_map.keys()))
    
    revenue = [data_map[y]["revenue"] for y in sorted_years]
    capex = [data_map[y]["capex"] for y in sorted_years]
    years = sorted_years

    # 计算最新一年的 YoY 增长率
    rev_growth   = (revenue[-1] - revenue[-2]) / revenue[-2] if revenue[-2] != 0 else 0
    capex_growth = (capex[-1] - capex[-2]) / capex[-2] if capex[-2] != 0 else 0
    diff         = capex_growth - rev_growth

    # 状态判定
    if diff >= 0.2:
        status, sc, si = "过热预警", "#fbbf24", "⚠️"
        status_desc  = "当前AI资本扩张已进入<br>高波动风险阶段。"
        alert_title  = "结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段"
        alert_body   = (f'当前资本开支增速比收入增速高出 <span style="color:#fbbf24;"><b>{diff*100:.2f}%</b></span>，'
                        f'企业AI基础设施投入已超出现实需求支撑。<br>'
                        f'若趋势持续，将提升未来盈利与现金流承压风险，需重点跟踪需求兑现情况。')
    elif diff >= 0:
        status, sc, si = "偏热", "#fbbf24", "⚠️"
        status_desc  = "资本扩张开始领先收入增长。<br>系统进入高估值区间。"
        alert_title  = "结论：资本开支增速超出收入增速，进入偏热区间"
        alert_body   = (f'当前资本开支增速比收入增速高出 <span style="color:#fbbf24;"><b>{diff*100:.2f}%</b></span>，'
                        f'资本扩张速度开始领先，需关注需求兑现节奏。')
    else:
        status, sc, si = "健康", "#22c55e", "✅"
        status_desc  = "收入增长仍高于资本扩张。<br>AI需求尚能支撑投资。"
        alert_title  = "结论：当前AI投资处于健康扩张阶段"
        alert_body   = (f'收入增速高于资本开支增速，差值为 <span style="color:#22c55e;"><b>{abs(diff)*100:.2f}%</b></span>，'
                        f'AI基础设施投入与现实需求匹配良好。')

    # ===== 四张卡片（彻底重写：注入高权重行内样式，放大字体并调白颜色） =====
    c1, c2, c3, c4 = st.columns(4)
    
    card_base_style = "background-color:#0b1120; border:1px solid rgba(255,255,255,0.07); border-radius:14px; padding:20px 22px 18px; height:168px;"
    label_style = "color:#f8fafc !important; font-size:16px !important; font-weight:700 !important; margin-bottom:16px; text-transform:uppercase; letter-spacing:0.4px;"
    num_style = "font-size:38px; font-weight:800; line-height:1; letter-spacing:-1.5px;"
    desc_style = "color:#64748b; font-size:12px; line-height:1.65;"

    with c1:
        st.markdown(f"""<div style="{card_base_style}">
  <div style="{label_style}">收入增长率 (YoY)</div>
  <div style="display:flex; align-items:baseline; gap:8px; margin-bottom:14px;"><span style="{num_style} color:#22c55e;">{rev_growth*100:.2f}%</span><span style="font-size:20px; font-weight:700; color:#22c55e;">↗</span></div>
  <div style="{desc_style}">AI需求仍维持高增长。<br>当前收入扩张速度保持强劲。</div>
</div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""<div style="{card_base_style}">
  <div style="{label_style}">资本开支增长率 (YoY)</div>
  <div style="display:flex; align-items:baseline; gap:8px; margin-bottom:14px;"><span style="{num_style} color:#ef4444;">{capex_growth*100:.2f}%</span><span style="font-size:20px; font-weight:700; color:#ef4444;">↗</span></div>
  <div style="{desc_style}">企业正在加速AI基础设施投入。<br>CapEx扩张速度持续提升。</div>
</div>""", unsafe_allow_html=True)

    with c3:
        ds = "+" if diff >= 0 else ""
        st.markdown(f"""<div style="{card_base_style}">
  <div style="{label_style}">增速差 (CapEx - Revenue)</div>
  <div style="display:flex; align-items:baseline; gap:8px; margin-bottom:14px;"><span style="{num_style} color:#fbbf24;">{ds}{diff*100:.2f}%</span></div>
  <div style="{desc_style}">资本扩张速度已开始超过<br>收入增长速度。</div>
</div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""<div style="{card_base_style}">
  <div style="{label_style}">状态判断</div>
  <div style="display:flex; align-items:baseline; gap:8px; margin-bottom:14px;"><span style="{num_style} color:{sc};">{status}</span><span style="font-size:20px; font-weight:700; color:{sc};">{si}</span></div>
  <div style="{desc_style}">{status_desc}</div>
</div>""", unsafe_allow_html=True)

    # ===== Alert =====
    st.markdown(f"""<div style="margin:18px 0; background:#120e00; border:1px solid rgba(251,191,36,0.18); border-radius:14px; padding:22px 26px; display:flex; gap:18px; align-items:flex-start;">
  <div style="font-size:44px; flex-shrink:0; line-height:1;">⚠️</div>
  <div>
    <div style="font-size:20px; font-weight:700; color:#fbbf24; margin-bottom:10px;">{alert_title}</div>
    <div style="font-size:14px; color:#94a3b8; line-height:1.75;">{alert_body}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ===== 下方面板 =====
    lp, rp = st.columns([1, 1.5])

    with lp:
        st.markdown("""<div style="background-color:#0b1120; border-radius:14px; padding:22px; border:1px solid rgba(255,255,255,0.07);">
  <div style="font-size:15px; font-weight:700; margin-bottom:20px; color:#e2e8f0;">⚙️ 检测逻辑</div>
  <div style="display:flex; gap:12px; margin-bottom:13px; align-items:flex-start;"><div style="width:20px; height:20px; min-width:20px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">1</div><div style="font-size:13px; color:#94a3b8; line-height:1.6;">获取最新两个财年数据：收入、资本开支</div></div>
  <div style="display:flex; gap:12px; margin-bottom:13px; align-items:flex-start;"><div style="width:20px; height:20px; min-width:20px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">2</div><div style="font-size:13px; color:#94a3b8; line-height:1.6;">计算收入增长率 = (本期收入 - 上期收入) / 上期收入</div></div>
  <div style="display:flex; gap:12px; margin-bottom:13px; align-items:flex-start;"><div style="width:20px; height:20px; min-width:20px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">3</div><div style="font-size:13px; color:#94a3b8; line-height:1.6;">计算资本开支增长率 = (本期资本开支 - 上期资本开支) / 上期资本开支</div></div>
  <div style="display:flex; gap:12px; margin-bottom:13px; align-items:flex-start;"><div style="width:20px; height:20px; min-width:20px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">4</div><div style="font-size:13px; color:#94a3b8; line-height:1.6;">计算增速差 = 资本开支增长率 - 收入增长率</div></div>
  <div style="display:flex; gap:12px; margin-bottom:13px; align-items:flex-start;"><div style="width:20px; height:20px; min-width:20px; border-radius:50%; background:#1e3a5f; color:#60a5fa; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; margin-top:2px;">5</div><div style="font-size:13px; color:#94a3b8; line-height:1.6;">根据阈值判断状态：</div></div>
  <div style="margin-left:32px; margin-top:8px;">
    <div style="display:flex; align-items:center; gap:8px; padding:7px 10px; border-radius:7px; margin-bottom:5px; background:rgba(255,255,255,0.02);"><div style="width:7px; height:7px; border-radius:50%; flex-shrink:0; background:#ef4444;"></div><div style="font-size:12px; color:#94a3b8; flex:1;">增速差 ≥ 20%</div><div style="font-size:11px; color:#475569;">→</div><div style="font-size:12px; font-weight:600; color:#ef4444;">过热预警（红色）</div></div>
    <div style="display:flex; align-items:center; gap:8px; padding:7px 10px; border-radius:7px; margin-bottom:5px; background:rgba(255,255,255,0.02);"><div style="width:7px; height:7px; border-radius:50%; flex-shrink:0; background:#fbbf24;"></div><div style="font-size:12px; color:#94a3b8; flex:1;">0% ≤ 增速差 &lt; 20%</div><div style="font-size:11px; color:#475569;">→</div><div style="font-size:12px; font-weight:600; color:#fbbf24;">偏离预警（黄色）</div></div>
    <div style="display:flex; align-items:center; gap:8px; padding:7px 10px; border-radius:7px; margin-bottom:5px; background:rgba(255,255,255,0.02);"><div style="width:7px; height:7px; border-radius:50%; flex-shrink:0; background:#22c55e;"></div><div style="font-size:12px; color:#94a3b8; flex:1;">增速差 &lt; 0%</div><div style="font-size:11px; color:#475569;">→</div><div style="font-size:12px; font-weight:600; color:#22c55e;">健康（绿色）</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    with rp:
        st.markdown('<div style="background-color:#0b1120; border-radius:14px; padding:22px; border:1px solid rgba(255,255,255,0.07);"><div style="font-size:15px; font-weight:700; margin-bottom:20px; color:#e2e8f0;">📈 趋势对比（最近5年）</div>', unsafe_allow_html=True)

        # 趋势图表增幅重算：确保完美按照 X 轴多元素展开
        rg_list, cg_list, cy_list = [], [], []
        for i in range(1, len(revenue)):
            if revenue[i-1] != 0 and capex[i-1] != 0:
                rg_list.append(((revenue[i] - revenue[i-1]) / revenue[i-1]) * 100)
                cg_list.append(((capex[i] - capex[i-1]) / capex[i-1]) * 100)
                cy_list.append(str(years[i]))

        if len(cy_list) > 0:
            annotations = [
                dict(x=cy_list[-1], y=rg_list[-1], text=f"<b>{rg_list[-1]:.2f}%</b>",
                     showarrow=False, xanchor="left", xshift=10, font=dict(color="#22c55e", size=13)),
                dict(x=cy_list[-1], y=cg_list[-1], text=f"<b>{cg_list[-1]:.2f}%</b>",
                     showarrow=False, xanchor="left", xshift=10, font=dict(color="#ef4444", size=13)),
            ]
        else:
            annotations = []

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cy_list, y=rg_list, mode="lines+markers",
            name="收入增长率(%)", line=dict(color="#22c55e", width=2.5), marker=dict(size=7)))
        fig.add_trace(go.Scatter(x=cy_list, y=cg_list, mode="lines+markers",
            name="资本开支增长率(%)", line=dict(color="#ef4444", width=2.5), marker=dict(size=7)))

        fig.update_layout(
            height=340,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#64748b", size=12),
            legend=dict(orientation="h", y=1.15, font=dict(size=12, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=30, r=60, t=10, b=20),
            annotations=annotations,
            xaxis=dict(
                type="category",        # 强制指定为多离散点的类目型轴
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

    st.markdown(f'<div style="margin-top:14px; color:#475569; font-size:11px; text-align:right;">数据来源：Financial Modeling Prep (FMP) · 实时采集 · 当前标的：{symbol}</div>',
                unsafe_allow_html=True)

else:
    st.error(f"API数据加载失败，请检查股票代码是否正确。")
