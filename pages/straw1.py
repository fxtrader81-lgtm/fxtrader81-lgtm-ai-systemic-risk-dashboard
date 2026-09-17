import streamlit as st
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
from config.api_keys import FMP_API_KEY, FMP_BASE
from components.ui import load_css
from core.alert_engine import render_alert, score_to_state
from core.factor_registry import straw1_score
from core.score_engine import register_score

# =========================================================
# 页面配置
# =========================================================

st.set_page_config(
    page_title="AI资本开支风险系统",
    layout="wide"
)
load_css()

# =========================================================
# API 配置 — 保持最稳定的原始限制模式
# =========================================================

API_KEY = FMP_API_KEY
BASE = FMP_BASE

# =========================================================
# CSS — 完美保留截图黑金高级风格
# =========================================================


# =========================================================
# 工具函数
# =========================================================

def fetch_fmp(endpoint, symbol):
    """Return FMP data and a safe diagnostic message."""
    if not API_KEY:
        return [], "FMP_API_KEY 未配置"

    try:
        r = requests.get(
            f"{BASE}/{endpoint}",
            params={"symbol": symbol, "limit": 5, "apikey": API_KEY},
            timeout=15,
        )
        if r.status_code != 200:
            return [], f"FMP 返回 HTTP {r.status_code}"
        data = r.json()
        if not isinstance(data, list):
            return [], "FMP 返回了非预期数据格式"
        return data, ""
    except requests.RequestException as exc:
        return [], f"FMP 网络请求失败：{type(exc).__name__}"
    except ValueError:
        return [], "FMP 返回内容无法解析"


def _financial_row(frame, names):
    if frame is None or frame.empty:
        return None
    for name in names:
        if name in frame.index:
            return frame.loc[name]
    return None


def fetch_yfinance_financials(symbol):
    """Fallback source when FMP is unavailable; returns FMP-shaped rows."""
    try:
        ticker = yf.Ticker(symbol)
        income_frame = ticker.financials
        cash_frame = ticker.cashflow
        revenue = _financial_row(income_frame, ["Total Revenue", "Operating Revenue"])
        capex = _financial_row(cash_frame, ["Capital Expenditure", "Capital Expenditure Reported"])
        if revenue is None or capex is None:
            return [], [], "Yahoo Finance 缺少收入或资本开支字段"

        income, cash = [], []
        common_dates = sorted(set(revenue.dropna().index) & set(capex.dropna().index), reverse=True)
        for period in common_dates[:5]:
            date_str = period.strftime("%Y-%m-%d")
            income.append({
                "date": date_str,
                "calendarYear": str(period.year),
                "revenue": float(revenue.loc[period]),
            })
            cash.append({
                "date": date_str,
                "capitalExpenditure": float(capex.loc[period]),
            })
        if len(income) < 2:
            return [], [], "Yahoo Finance 可用年度数据少于两期"
        return income, cash, ""
    except Exception as exc:
        return [], [], f"Yahoo Finance 获取失败：{type(exc).__name__}"


@st.cache_data(ttl=3600, show_spinner=False)
def load_financial_data(symbol):
    diagnostics = []
    income, income_error = fetch_fmp("income-statement", symbol)
    cash, cash_error = fetch_fmp("cash-flow-statement", symbol)
    if len(income) >= 2 and len(cash) >= 2:
        return income, cash, "Financial Modeling Prep", ""

    diagnostics.extend(message for message in [income_error, cash_error] if message)
    income, cash, yf_error = fetch_yfinance_financials(symbol)
    if len(income) >= 2 and len(cash) >= 2:
        return income, cash, "Yahoo Finance（FMP 备用源）", "；".join(diagnostics)

    if yf_error:
        diagnostics.append(yf_error)
    return [], [], "", "；".join(dict.fromkeys(diagnostics))

def safe(x, k):
    try:
        return float(x.get(k, 0))
    except:
        return 0

# =========================================================
# 顶部控制
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
# 稳定获取：硬性 limit=5
# =========================================================

income, cash, data_source, load_diagnostic = load_financial_data(symbol.strip().upper())

if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2:

    cash_map = {item["date"]: item for item in cash if "date" in item}
    
    raw_list = []
    for inc in income:
        d_str = inc.get("date", "")
        if d_str in cash_map:
            csh = cash_map[d_str]
            try:
                y_val = int(inc.get("calendarYear", d_str[:4]))
            except:
                continue
                
            raw_list.append({
                "year": y_val,
                "revenue": safe(inc, "revenue"),
                "capex": abs(safe(csh, "capitalExpenditure"))
            })
            
    raw_list.sort(key=lambda x: x["year"])
    
    final_timeline = []
    seen_years = set()
    for item in raw_list:
        if item["year"] not in seen_years:
            seen_years.add(item["year"])
            final_timeline.append(item)

    if len(final_timeline) < 2:
        st.error("收入与资本开支的共同年度数据少于两期，暂时无法计算增长率。")
        if load_diagnostic:
            st.caption(load_diagnostic)
        st.stop()

    # 计算最新财年的增长率与增速差
    rev_growth   = (final_timeline[-1]["revenue"] - final_timeline[-2]["revenue"]) / final_timeline[-2]["revenue"]
    capex_growth = (final_timeline[-1]["capex"] - final_timeline[-2]["capex"]) / final_timeline[-2]["capex"]
    diff         = capex_growth - rev_growth
    risk_score   = straw1_score(diff)
    risk_state   = score_to_state(risk_score)
    register_score("straw1", risk_score)

    # 结论与顶部总状态共用同一套四级标准，避免出现互相冲突的状态名称。
    risk_color_class = {
        "SAFE": "green", "WATCH": "yellow", "WARNING": "orange", "CRITICAL": "red"
    }[risk_state]
    conclusions = {
        "SAFE": (
            "结论：收入增长快于资本开支，当前处于 SAFE 区间",
            f"收入增速高于资本开支增速 {abs(diff) * 100:.2f} 个百分点，AI基础设施投入仍有现实需求支撑。",
        ),
        "WATCH": (
            "结论：资本开支开始领先收入增长，进入 WATCH 区间",
            f"资本开支增速比收入增速高出 {diff * 100:.2f} 个百分点，建议提高对需求兑现与现金流的监测频率。",
        ),
        "WARNING": (
            "结论：资本扩张显著领先收入增长，进入 WARNING 区间",
            f"资本开支增速比收入增速高出 {diff * 100:.2f} 个百分点，资本回报和自由现金流压力正在上升。",
        ),
        "CRITICAL": (
            "结论：资本开支严重超前，进入 CRITICAL 危机区间",
            f"资本开支增速比收入增速高出 {diff * 100:.2f} 个百分点，AI基础设施投入已明显超前；若趋势持续，将显著提升盈利与现金流风险。",
        ),
    }
    alert_title, alert_body = conclusions[risk_state]

    state_details = {
        "SAFE": "Revenue growth supports current investment",
        "WATCH": "CapEx growth is beginning to outpace revenue",
        "WARNING": "CapEx expansion is materially ahead of revenue",
        "CRITICAL": "CapEx growth materially exceeds revenue",
    }

    risk_color = {
        "SAFE": "#22c55e", "WATCH": "#fbbf24",
        "WARNING": "#f97316", "CRITICAL": "#ef4444",
    }[risk_state]
    st.markdown(f"""
<div class="osci-card">
  <div class="osci-left">
    <div class="osci-label">CAPEX–REVENUE RISK INDEX</div>
    <div class="osci-score-row">
      <div class="osci-score" style="color:{risk_color};">{risk_score:.0f}</div>
      <div class="osci-scale">/100</div>
    </div>
    <div class="osci-desc">综合评分：资本开支增速与收入增速差为 {diff * 100:+.2f} 个百分点。</div>
    <div class="osci-bar-wrap">
      <div class="osci-bar-fill" style="width:{risk_score}%; background:{risk_color};"></div>
    </div>
  </div>
  <div class="osci-right">
    <div class="osci-state-label">SYSTEM STATE</div>
    <div class="osci-state" style="color:{risk_color};">{risk_state}</div>
    <div style="margin-top:8px; font-size:14px; color:#64748b;">{state_details[risk_state]}</div>
    <div style="margin-top:16px; font-size:13px; color:#64748b; line-height:1.8;">
      收入增长 {rev_growth * 100:.2f}% · 资本开支增长 {capex_growth * 100:.2f}%<br>
      增速差 {diff * 100:+.2f} 个百分点 · 单因子评分
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ===== 三张核心指标卡片（状态仅在顶部总卡展示） =====
    c1, c2, c3 = st.columns(3)

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
  <div class="metric-row"><span class="metric-number {risk_color_class}">{ds}{diff*100:.2f}%</span></div>
  <div class="metric-desc">资本扩张速度已开始超过<br>收入增长速度。</div>
</div>""", unsafe_allow_html=True)

    # ===== Alert =====
    st.markdown(render_alert(risk_state, alert_title, alert_body), unsafe_allow_html=True)

    # ===== 下方面板 =====
    lp, rp = st.columns([1, 1.5])

    with lp:
        st.markdown("""<div class="panel">
  <div class="panel-title">⚙️ 检测逻辑</div>
  <div class="logic-step"><div class="step-num">1</div><div class="step-text">获取最新两个财年数据：收入、资本开支</div></div>
  <div class="logic-step"><div class="step-num">2</div><div class="step-text">计算收入增长率 = (本期收入 - 上期收入) / 上期收入</div></div>
  <div class="logic-step"><div class="step-num">3</div><div class="step-text">计算资本开支增长率 = (本期资本开支 - 上期资本开支) / 上期资本开支</div></div>
  <div class="logic-step"><div class="step-num">4</div><div class="step-text">计算增速差 = 资本开支增长率 - 收入增长率</div></div>
  <div class="logic-step"><div class="step-num">5</div><div class="step-text">映射风险分数：Score = clamp(25 + 250 × 增速差, 0, 100)，再按统一四级阈值判断状态：</div></div>
  <div class="threshold-block">
    <div class="threshold-row"><div class="t-dot" style="background:#22c55e;"></div><div class="t-label">增速差 &lt; 0%（Score &lt; 25）</div><div class="t-arrow">→</div><div class="t-status green">SAFE</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#fbbf24;"></div><div class="t-label">0% ≤ 增速差 &lt; 10%（25 ≤ Score &lt; 50）</div><div class="t-arrow">→</div><div class="t-status yellow">WATCH</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#f97316;"></div><div class="t-label">10% ≤ 增速差 &lt; 20%（50 ≤ Score &lt; 75）</div><div class="t-arrow">→</div><div class="t-status orange">WARNING</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#ef4444;"></div><div class="t-label">增速差 ≥ 20%（Score ≥ 75）</div><div class="t-arrow">→</div><div class="t-status red">CRITICAL</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    with rp:
        st.markdown('<div class="panel"><div class="panel-title">📈 趋势对比（最近5年）</div>', unsafe_allow_html=True)

        rg_list, cg_list, cy_list = [], [], []
        for i in range(1, len(final_timeline)):
            prev = final_timeline[i-1]
            curr = final_timeline[i]
            if prev["revenue"] > 0 and prev["capex"] > 0:
                if curr["year"] >= 2023:
                    rg_list.append(((curr["revenue"] - prev["revenue"]) / prev["revenue"]) * 100)
                    cg_list.append(((curr["capex"] - prev["capex"]) / prev["capex"]) * 100)
                    cy_list.append(curr["year"])

        fig = go.Figure()
        
        if cy_list:
            fig.add_trace(go.Scatter(x=cy_list, y=rg_list, mode="lines+markers",
                name="收入增长率(%)", line=dict(color="#22c55e", width=2.5), marker=dict(size=7)))
            fig.add_trace(go.Scatter(x=cy_list, y=cg_list, mode="lines+markers",
                name="资本开支增长率(%)", line=dict(color="#ef4444", width=2.5), marker=dict(size=7)))

            # 动态生成所有节点的数值标注
            annotations = []
            for idx in range(len(cy_list)):
                year = cy_list[idx]
                rev_val = rg_list[idx]
                cap_val = cg_list[idx]
                
                # 判断是否为最新的一个点（最后一年，即2026年）
                if idx == len(cy_list) - 1:
                    # 最新数据：移到右侧空白区，加粗放大到 size=20
                    annotations.append(
                        dict(x=year, y=rev_val, text=f"<b>{rev_val:.2f}%</b>",
                             showarrow=False, xanchor="left", xshift=14, font=dict(color="#22c55e", size=20))
                    )
                    annotations.append(
                        dict(x=year, y=cap_val, text=f"<b>{cap_val:.2f}%</b>",
                             showarrow=False, xanchor="left", xshift=14, font=dict(color="#ef4444", size=20))
                    )
                else:
                    # 历史节点（2023、2024、2025）：直观标在数据点上方，尺寸设为精致的 size=11
                    annotations.append(
                        dict(x=year, y=rev_val, text=f"{rev_val:.2f}%",
                             showarrow=False, yanchor="bottom", yshift=8, font=dict(color="#22c55e", size=11))
                    )
                    annotations.append(
                        dict(x=year, y=cap_val, text=f"{cap_val:.2f}%",
                             showarrow=False, yanchor="bottom", yshift=8, font=dict(color="#ef4444", size=11))
                    )
        else:
            annotations = []

        fig.update_layout(
            height=340,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#64748b", size=12),
            legend=dict(orientation="h", y=1.15, font=dict(size=12, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=10, r=95, t=10, b=10), # 完美放宽右边距至95，承托放大后的20字号
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

    st.markdown(f'<div class="footer-text">数据来源：{data_source} · 实时采集 · 当前标的：{symbol}</div>',
                unsafe_allow_html=True)

else:
    st.error("财务数据加载失败。这通常不是股票代码错误，而是数据源密钥、限额或网络状态异常。")
    if load_diagnostic:
        st.caption(load_diagnostic)
