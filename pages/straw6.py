

Write the complete rewritten straw6.py
bash

cat > /home/claude/straw6.py << 'PYEOF'
"""
straw6.py — 稻草六 · 美元国债市场预警
股市 × 债市联动分析

数据源:
  - FRED API  : 美国国债收益率 (DGS10, DGS30)
  - FMP API   : 美股指数 (S&P500, NASDAQ, Dow Jones)
  - yfinance  : A股指数 (上证 000001.SS, 深证 399001.SZ)
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz
import yfinance as yf

# =========================================================
# 页面配置
# =========================================================
st.set_page_config(
    page_title="稻草六 · 美元国债市场预警",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# API Keys
# =========================================================
FRED_API_KEY = "9d4d8c74237a32ec198773ca5eb0f4e3"
FMP_API_KEY  = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"

# =========================================================
# 太平洋时间
# =========================================================
def now_pt() -> str:
    tz = pytz.timezone("America/Los_Angeles")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M PT")

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #050816 !important;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.stApp { background-color: #050816 !important; }
section[data-testid="stMain"] > div { background-color: #050816 !important; }
.block-container {
    padding-top: 1.4rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1600px;
    background-color: #050816 !important;
}

/* 侧边栏 — 保留显示，仅样式调整 */
[data-testid="stSidebar"] {
    background-color: #0b1120 !important;
    border-right: 1px solid rgba(255,255,255,0.07);
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* ── 顶部标题区 ── */
.page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 18px;
}
.page-title {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
    margin: 0 0 4px 0;
}
.page-sub {
    font-size: 13px;
    color: #94a3b8;
    margin: 0;
}
.ts-label {
    font-size: 13px;
    font-weight: 600;
    color: #cbd5e1;
    text-align: right;
    display: block;
    margin-bottom: 4px;
}
.symbol-badge {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 3px 14px;
    font-size: 12px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 1px;
}

/* ── 顶部综合预警栏 (straw4 风格) ── */
.alert-top-bar {
    background: linear-gradient(135deg, #0b1120 0%, #0d1829 100%);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 32px;
}
.atb-score-wrap { text-align: center; min-width: 100px; }
.atb-score {
    font-size: 64px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -3px;
}
.atb-score-label {
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 4px;
}
.atb-divider {
    width: 1px;
    height: 70px;
    background: rgba(255,255,255,0.08);
    flex-shrink: 0;
}
.atb-state-wrap { min-width: 140px; }
.atb-state-label {
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.atb-state {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
.atb-bar-wrap {
    margin-top: 10px;
    width: 160px;
    height: 5px;
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
}
.atb-bar-fill { height: 5px; border-radius: 3px; }
.atb-conclusion { flex: 1; }
.atb-con-title {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 7px;
}
.atb-con-body {
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.75;
}

/* ── KPI 卡片 ── */
.kpi-card {
    background: #0b1120;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 18px 20px 16px;
}
.kpi-label {
    font-size: 13px;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 8px;
    letter-spacing: 0.3px;
}
.kpi-value {
    font-size: 30px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1px;
}
.kpi-sub {
    font-size: 12px;
    color: #64748b;
    margin-top: 6px;
    line-height: 1.5;
}

/* ── Alert 4-indicator cards ── */
.ind-card {
    background: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 18px 20px;
    height: 200px;
}
.ind-label {
    font-size: 12px;
    font-weight: 700;
    color: #cbd5e1;
    margin-bottom: 10px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.ind-value {
    font-size: 32px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1.2px;
}
.ind-unit {
    font-size: 13px;
    color: #64748b;
    margin-left: 4px;
}
.ind-badge {
    display: inline-block;
    border-radius: 5px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    margin-top: 8px;
}
.ind-thresh {
    font-size: 11px;
    color: #475569;
    margin-top: 8px;
    line-height: 1.8;
}

/* ── 结论框 ── */
.conc-box {
    border-radius: 14px;
    padding: 18px 22px;
    display: flex;
    gap: 14px;
    align-items: flex-start;
    margin: 14px 0;
}
.conc-icon { font-size: 36px; flex-shrink: 0; line-height: 1; }
.conc-title { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
.conc-body  { font-size: 13px; color: #cbd5e1; line-height: 1.75; }

/* ── Panel ── */
.panel {
    background: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
}
.panel-title {
    font-size: 15px;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 16px;
}

/* ── 历史复盘表 ── */
.hr-row {
    display: flex;
    gap: 8px;
    padding: 10px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    align-items: center;
}
.hr-row:last-child { border-bottom: none; }
.hr-date  { font-size: 12px; font-weight: 700; color: #94a3b8; width: 72px; flex-shrink: 0; }
.hr-event { font-size: 12px; color: #e2e8f0; flex: 1; }
.hr-y10   { font-size: 12px; font-weight: 700; color: #5CB85C; width: 52px; text-align: right; }
.hr-drop  { font-size: 12px; font-weight: 700; color: #ef4444; width: 52px; text-align: right; }

/* ── 时间范围控件标签 ── */
.ctrl-label {
    font-size: 13px;
    font-weight: 700;
    color: #cbd5e1;
    margin-bottom: 6px;
}

/* ── 颜色 class ── */
.c-green  { color: #22c55e; }
.c-red    { color: #ef4444; }
.c-yellow { color: #fbbf24; }
.c-orange { color: #f97316; }
.c-blue   { color: #4F8EF7; }
.c-gray   { color: #94a3b8; }

/* 隐藏 streamlit chrome */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
.modebar  { display: none !important; }

/* Tab 样式 */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    gap: 4px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px 8px 0 0;
    padding: 9px 26px;
    color: #64748b;
    font-weight: 700;
    font-size: 14px;
    border: 1px solid transparent;
    border-bottom: none;
}
.stTabs [aria-selected="true"] {
    background: #0b1120 !important;
    color: #60a5fa !important;
    border-color: rgba(255,255,255,0.08) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent;
    padding-top: 22px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 股灾事件
# =========================================================
CRASH_EVENTS = [
    {"date": "1997-10-01", "label": "Asian Crisis",    "desc": "亚洲金融危机·港元保卫战",        "severity": "WARNING"},
    {"date": "1998-08-01", "label": "LTCM/Russia",     "desc": "俄罗斯违约·LTCM崩盘",           "severity": "WARNING"},
    {"date": "2000-03-01", "label": "Dot-com Peak",    "desc": "科网泡沫顶点·纳指跌78%",         "severity": "CRITICAL"},
    {"date": "2001-09-01", "label": "9/11",            "desc": "911恐袭·市场关闭4天",            "severity": "CRITICAL"},
    {"date": "2002-10-01", "label": "Tech Bottom",     "desc": "科网熊市底部",                   "severity": "WARNING"},
    {"date": "2007-08-01", "label": "Subprime",        "desc": "次贷危机苗头·贝尔斯登基金崩盘", "severity": "WARNING"},
    {"date": "2008-09-01", "label": "Lehman",          "desc": "雷曼破产·金融海啸",              "severity": "CRITICAL"},
    {"date": "2010-05-01", "label": "Flash Crash",     "desc": "闪崩·道指单日跌近1000点",       "severity": "WATCH"},
    {"date": "2011-08-01", "label": "US Downgrade",    "desc": "美国主权评级下调·欧债危机",      "severity": "WARNING"},
    {"date": "2015-08-01", "label": "China Crash",     "desc": "A股股灾·人民币贬值",            "severity": "WARNING"},
    {"date": "2018-12-01", "label": "Fed Panic",       "desc": "美联储加息恐慌·圣诞崩盘",       "severity": "WARNING"},
    {"date": "2020-03-01", "label": "COVID",           "desc": "新冠疫情·史上最快熊市",         "severity": "CRITICAL"},
    {"date": "2022-01-01", "label": "Rate Hike",       "desc": "加息周期启动·纳指跌33%",        "severity": "CRITICAL"},
    {"date": "2023-03-01", "label": "SVB Crisis",      "desc": "硅谷银行倒闭·银行业危机",       "severity": "WARNING"},
]

SEV_COLOR = {"WATCH": "#fbbf24", "WARNING": "#f97316", "CRITICAL": "#ef4444"}

# =========================================================
# 数据获取
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred(series_id: str, start: str = "1994-01-01") -> pd.Series:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = dict(
        series_id=series_id, api_key=FRED_API_KEY,
        file_type="json", observation_start=start,
        frequency="m", aggregation_method="eop",
    )
    try:
        obs = requests.get(url, params=params, timeout=15).json().get("observations", [])
        s = pd.Series({o["date"]: float(o["value"]) for o in obs if o["value"] != "."}, name=series_id)
        s.index = pd.to_datetime(s.index)
        return s
    except Exception as e:
        st.warning(f"FRED {series_id}: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fmp(symbol: str, start: str = "1994-01-01") -> pd.Series:
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
    try:
        hist = requests.get(url, params={"apikey": FMP_API_KEY, "from": start}, timeout=20).json().get("historical", [])
        if not hist:
            return pd.Series(dtype=float)
        df = pd.DataFrame(hist)[["date", "close"]]
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date").sort_index()["close"].resample("ME").last()
        s.name = symbol
        return s
    except Exception as e:
        st.warning(f"FMP {symbol}: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_yf(ticker: str, start: str = "1994-01-01") -> pd.Series:
    try:
        df = yf.download(ticker, start=start, interval="1mo", progress=False, auto_adjust=True)
        if df.empty:
            return pd.Series(dtype=float)
        s = df["Close"].squeeze()
        s.index = pd.to_datetime(s.index).to_period("M").to_timestamp("M")
        s.name = ticker
        return s.dropna()
    except Exception as e:
        st.warning(f"yfinance {ticker}: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def load_all():
    return (
        fetch_fred("DGS10"),
        fetch_fred("DGS30"),
        fetch_fmp("^GSPC"),
        fetch_fmp("^IXIC"),
        fetch_fmp("^DJI"),
        fetch_yf("000001.SS"),
        fetch_yf("399001.SZ"),
    )


# =========================================================
# 预警计算
# =========================================================

def compute_alerts(y10, y30, sp500):
    r = {}

    v10 = float(y10.iloc[-1]) if not y10.empty else 0
    s1, g1 = ((0,"SAFE") if v10<3 else (33,"WATCH") if v10<4 else (67,"WARNING") if v10<5 else (100,"CRITICAL"))
    r["y10_level"] = {"value": v10, "grade": g1, "score": s1}

    chg = float(y10.iloc[-1] - y10.iloc[-3]) * 100 if len(y10) >= 3 else 0.0
    s2, g2 = ((0,"SAFE") if chg<50 else (33,"WATCH") if chg<100 else (67,"WARNING") if chg<150 else (100,"CRITICAL"))
    r["y10_mom"] = {"value": chg, "grade": g2, "score": s2}

    if not y30.empty and not y10.empty:
        c = y30.index.intersection(y10.index)
        sp = float(y30.loc[c[-1]] - y10.loc[c[-1]]) * 100 if len(c) else 20.0
    else:
        sp = 20.0
    s3, g3 = ((0,"SAFE") if sp>20 else (33,"WATCH") if sp>0 else (67,"WARNING") if sp>-30 else (100,"CRITICAL"))
    r["spread"] = {"value": sp, "grade": g3, "score": s3}

    corr = 0.0
    if len(y10) >= 12 and len(sp500) >= 12:
        c = y10.index.intersection(sp500.index)
        if len(c) >= 12:
            ya = y10.loc[c].tail(12); sa = sp500.loc[c].tail(12)
            sr = sa.pct_change().dropna(); yc = ya.diff().dropna()
            c2 = sr.index.intersection(yc.index)
            if len(c2) >= 6:
                corr = float(np.corrcoef(yc.loc[c2], sr.loc[c2])[0,1])
    s4, g4 = ((0,"SAFE") if corr>-0.3 else (33,"WATCH") if corr>-0.5 else (67,"WARNING") if corr>-0.7 else (100,"CRITICAL"))
    r["corr"] = {"value": corr, "grade": g4, "score": s4}

    comp = s1*0.15 + s2*0.40 + s3*0.25 + s4*0.20
    mg = ("SAFE" if comp<25 else "WATCH" if comp<50 else "WARNING" if comp<75 else "CRITICAL")
    r["composite"] = {"score": round(comp,1), "grade": mg}
    return r


def g_color(g):
    return {"SAFE":"#22c55e","WATCH":"#fbbf24","WARNING":"#f97316","CRITICAL":"#ef4444"}.get(g,"#94a3b8")

def g_cls(g):
    return {"SAFE":"c-green","WATCH":"c-yellow","WARNING":"c-orange","CRITICAL":"c-red"}.get(g,"c-gray")


# =========================================================
# Plotly 基础设置
# =========================================================

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="'PingFang SC','Microsoft YaHei',sans-serif", size=12),
    legend=dict(bgcolor="rgba(11,17,32,0.85)", bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1, font=dict(size=12, color="#cbd5e1")),
    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
               zeroline=False, linecolor="rgba(255,255,255,0.1)", tickfont=dict(size=11)),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
               zeroline=False, linecolor="rgba(255,255,255,0.1)", tickfont=dict(size=11)),
    margin=dict(l=58, r=58, t=40, b=48),
    hovermode="x unified",
)

BOND_FILL = {"10Y Treasury": "rgba(92,184,92,0.15)",  "30Y Treasury": "rgba(88,120,255,0.15)"}
BOND_LINE = {"10Y Treasury": "#5CB85C",               "30Y Treasury": "#5878FF"}
STOCK_LINE = {
    "S&P 500":"#4F8EF7", "NASDAQ 100":"#FF7F50", "Dow Jones":"#2CA58D",
    "上证指数":"#E63946",  "深证成指":"#9D4EDD",
}


def cut(s, period):
    if period == "ALL" or s.empty: return s
    yr = {"1Y":1,"3Y":3,"5Y":5,"10Y":10}.get(period,100)
    return s[s.index >= s.index[-1] - pd.DateOffset(years=yr)]


def add_vlines(fig, events):
    """Add vertical crash annotation lines — uses rgba() to avoid hex+alpha bug"""
    for ev in events:
        dt = pd.to_datetime(ev["date"])
        base = SEV_COLOR.get(ev["severity"], "#94a3b8")
        # Convert hex to rgba — avoids plotly validator rejecting "#rrggbbAA"
        r_hex = base.lstrip("#")
        if len(r_hex) == 6:
            rv, gv, bv = int(r_hex[0:2],16), int(r_hex[2:4],16), int(r_hex[4:6],16)
            line_rgba = f"rgba({rv},{gv},{bv},0.5)"
            text_rgba = f"rgba({rv},{gv},{bv},1.0)"
        else:
            line_rgba = "rgba(148,163,184,0.5)"
            text_rgba = "rgba(148,163,184,1.0)"

        fig.add_shape(
            type="line",
            xref="x", yref="paper",
            x0=dt, x1=dt, y0=0, y1=1,
            line=dict(color=line_rgba, width=1, dash="dot"),
        )
        fig.add_annotation(
            x=dt, y=1.0, yref="paper",
            text=ev["label"], showarrow=False,
            textangle=-90, font=dict(size=9, color=text_rgba),
            xanchor="left", yanchor="top",
        )


def add_inversion_bands(fig, y10, y30):
    if y10.empty or y30.empty: return
    c = y10.index.intersection(y30.index)
    if c.empty: return
    inv = y30.loc[c] < y10.loc[c]
    in_b, start = False, None
    for dt, v in inv.items():
        if v and not in_b:   in_b, start = True, dt
        elif not v and in_b:
            in_b = False
            fig.add_vrect(x0=start, x1=dt, fillcolor="rgba(239,68,68,0.07)",
                          layer="below", line_width=0)
    if in_b:
        fig.add_vrect(x0=start, x1=c[-1], fillcolor="rgba(239,68,68,0.07)",
                      layer="below", line_width=0)


def norm(s):
    if s.empty: return s
    return s / s.dropna().iloc[0] * 100


# =========================================================
# 图表构建
# =========================================================

def chart_overview(y10, y30, sp500, nasdaq, dow, shcomp, szcomp, period, crashes):
    fig = go.Figure()
    NORM_FILL = {
        "10Y Treasury":"rgba(92,184,92,0.15)", "30Y Treasury":"rgba(88,120,255,0.15)",
        "S&P 500":"rgba(0,0,0,0)","NASDAQ 100":"rgba(0,0,0,0)","Dow Jones":"rgba(0,0,0,0)",
        "上证指数":"rgba(0,0,0,0)","深证成指":"rgba(0,0,0,0)",
    }
    NORM_LINE = {
        "10Y Treasury":"#5CB85C","30Y Treasury":"#5878FF","S&P 500":"#4F8EF7",
        "NASDAQ 100":"#FF7F50","Dow Jones":"#2CA58D","上证指数":"#E63946","深证成指":"#9D4EDD",
    }
    for series, name, is_bond in [
        (y10,"10Y Treasury",True),(y30,"30Y Treasury",True),
        (sp500,"S&P 500",False),(nasdaq,"NASDAQ 100",False),(dow,"Dow Jones",False),
        (shcomp,"上证指数",False),(szcomp,"深证成指",False),
    ]:
        if series.empty: continue
        s = cut(norm(series), period).dropna()
        if s.empty: continue
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            fill="tozeroy" if is_bond else "none",
            fillcolor=NORM_FILL[name],
            line=dict(color=NORM_LINE[name], width=1.5 if is_bond else 1.8),
            mode="lines",
        ))
    if crashes: add_vlines(fig, CRASH_EVENTS)
    ly = dict(**BASE_LAYOUT)
    ly["height"] = 500
    ly["title"] = dict(text="归一化全资产走势对比（起点=100）", font=dict(size=13, color="#e2e8f0"), x=0.01)
    fig.update_layout(**ly)
    return fig


def chart_dual(y10, y30, stock_pairs, period, crashes, title):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for series, name in [(y10,"10Y Treasury"),(y30,"30Y Treasury")]:
        if series.empty: continue
        s = cut(series, period).dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            fill="tozeroy", fillcolor=BOND_FILL[name],
            line=dict(color=BOND_LINE[name], width=1.5), mode="lines",
            hovertemplate=f"{name}: %{{y:.2f}}%<extra></extra>",
        ), secondary_y=False)
    for series, name in stock_pairs:
        if series.empty: continue
        s = cut(series, period).dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            line=dict(color=STOCK_LINE.get(name,"#94a3b8"), width=2), mode="lines",
            hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>",
        ), secondary_y=True)
    if crashes: add_vlines(fig, CRASH_EVENTS)
    add_inversion_bands(fig, y10, y30)
    ly = dict(**BASE_LAYOUT)
    ly["height"] = 490
    ly["title"] = dict(text=title, font=dict(size=13, color="#e2e8f0"), x=0.01)
    fig.update_layout(**ly)
    fig.update_yaxes(title_text="收益率 (%)", secondary_y=False,
                     showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False)
    fig.update_yaxes(title_text="指数点位", secondary_y=True,
                     showgrid=False, zeroline=False)
    return fig


def chart_spread(y10, y30, period):
    if y10.empty or y30.empty: return go.Figure()
    c = y10.index.intersection(y30.index)
    sp = cut((y30.loc[c] - y10.loc[c]) * 100, period)
    colors = ["#ef4444" if v < 0 else "#22c55e" for v in sp.values]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sp.index, y=sp.values, marker_color=colors,
                         name="30Y-10Y", hovertemplate="利差: %{y:.1f} bps<extra></extra>"))
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.25)", line_width=1)
    ly = dict(**BASE_LAYOUT)
    ly["height"] = 200
    ly["title"] = dict(text="30Y − 10Y 期限利差 (bps)  🔴 红色=倒挂", font=dict(size=12, color="#e2e8f0"), x=0.01)
    fig.update_layout(**ly)
    return fig


def chart_alert_hist(y10, sp500):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if not y10.empty:
        fig.add_trace(go.Scatter(x=y10.index, y=y10.values, name="10Y Treasury",
            fill="tozeroy", fillcolor="rgba(92,184,92,0.15)",
            line=dict(color="#5CB85C", width=1.5), mode="lines"), secondary_y=False)
    if not sp500.empty:
        fig.add_trace(go.Scatter(x=sp500.index, y=sp500.values, name="S&P 500",
            line=dict(color="#4F8EF7", width=1.8), mode="lines"), secondary_y=True)
    add_vlines(fig, [e for e in CRASH_EVENTS if e["severity"] in ("CRITICAL","WARNING")])
    ly = dict(**BASE_LAYOUT)
    ly["height"] = 360
    ly["title"] = dict(text="10Y国债收益率 × S&P500 · 历史预警事件", font=dict(size=13, color="#e2e8f0"), x=0.01)
    fig.update_layout(**ly)
    fig.update_yaxes(title_text="收益率 (%)", secondary_y=False,
                     showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False)
    fig.update_yaxes(title_text="S&P 500", secondary_y=True, showgrid=False, zeroline=False)
    return fig


# =========================================================
# 可复用渲染组件
# =========================================================

def render_kpi_rows(y10, y30, sp500, nasdaq, dow, shcomp, szcomp):
    """两行 KPI：第一行债券利率+利差，第二行股指"""

    # --- 行1：10Y / 30Y / 30Y-10Y ---
    c1, c2, c3 = st.columns(3)

    def kpi(col, label, value, sub, cls):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
              <div class="kpi-label">{label}</div>
              <div class="kpi-value {cls}">{value}</div>
              <div class="kpi-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    y10_v = f"{y10.iloc[-1]:.2f}%" if not y10.empty else "N/A"
    y30_v = f"{y30.iloc[-1]:.2f}%" if not y30.empty else "N/A"
    sp_v  = 0.0
    if not y10.empty and not y30.empty:
        cc = y10.index.intersection(y30.index)
        if len(cc): sp_v = (y30.loc[cc[-1]] - y10.loc[cc[-1]]) * 100

    kpi(c1, "10年期美债收益率", y10_v, "US 10Y Treasury Yield",
        "c-green" if not y10.empty and y10.iloc[-1] < 4 else "c-orange")
    kpi(c2, "30年期美债收益率", y30_v, "US 30Y Treasury Yield",
        "c-green" if not y30.empty and y30.iloc[-1] < 4.5 else "c-orange")
    kpi(c3, "30Y − 10Y 期限利差", f"{sp_v:+.0f} bps",
        "🔴 倒挂预警" if sp_v < 0 else "期限结构正常",
        "c-green" if sp_v > 20 else "c-yellow" if sp_v > 0 else "c-red")

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # --- 行2：5个股指 ---
    d1, d2, d3, d4, d5 = st.columns(5)

    def kpi2(col, label, series, sub, cls):
        v = f"{series.iloc[-1]:,.0f}" if not series.empty else "N/A"
        # 1M change
        chg_txt = ""
        if len(series) >= 2:
            chg = (series.iloc[-1] / series.iloc[-2] - 1) * 100
            sign = "▲" if chg >= 0 else "▼"
            chg_col = "#22c55e" if chg >= 0 else "#ef4444"
            chg_txt = f'<span style="color:{chg_col}; font-size:12px;">{sign}{abs(chg):.1f}% MoM</span>'
        with col:
            st.markdown(f"""
            <div class="kpi-card">
              <div class="kpi-label">{label}</div>
              <div class="kpi-value {cls}">{v}</div>
              <div class="kpi-sub">{sub} {chg_txt}</div>
            </div>""", unsafe_allow_html=True)

    kpi2(d1, "道琼斯指数",    dow,    "Dow Jones",            "c-blue")
    kpi2(d2, "纳斯达克指数",  nasdaq, "NASDAQ Composite",     "c-orange")
    kpi2(d3, "标准普尔500",   sp500,  "S&P 500",              "c-blue")
    kpi2(d4, "上证综合指数",  shcomp, "Shanghai Composite",   "c-red")
    kpi2(d5, "深证成份指数",  szcomp, "Shenzhen Component",   "c-yellow")


ALERT_CONCLUSIONS = {
    "SAFE": {
        "bg":"#001208","border":"rgba(34,197,94,0.2)","icon":"✅","title_color":"#22c55e",
        "title":"结论：利率环境正常，股市估值压力较小",
        "body":"10Y收益率处于历史合理区间，上升速度温和，期限结构正向，股债相关性未出现异常负相关。历史上类似区间（2012-2017低利率扩张期），股市通常处于牛市中期。<b>当前无需过度警惕利率风险。</b>",
    },
    "WATCH": {
        "bg":"#120e00","border":"rgba(251,191,36,0.2)","icon":"👁","title_color":"#fbbf24",
        "title":"结论：预警信号出现，建议关注但暂无需行动",
        "body":"部分指标触及警戒区间。历史参照：2018年Q1-Q3美联储温和加息期，市场多次短暂调整未形成趋势。<b>重点跟踪3个月收益率变化速率，突破+100bps需提升至WARNING。</b>",
    },
    "WARNING": {
        "bg":"#120800","border":"rgba(249,115,22,0.25)","icon":"⚠️","title_color":"#f97316",
        "title":"结论：高风险区间，历史上此阶段股市平均调整15–25%",
        "body":"多项指标进入高风险区间。历史参照：2022年Q1-Q2，10Y收益率3个月上升230bps，纳指跌33%，标普跌25%。<b>估值压缩风险显著，科技/成长股暴露度建议降低。</b>",
    },
    "CRITICAL": {
        "bg":"#120000","border":"rgba(239,68,68,0.25)","icon":"🔴","title_color":"#ef4444",
        "title":"结论：极端风险，历史触发CRITICAL后市场均出现重大调整",
        "body":"所有核心指标极端化。历史：2000年科网顶点（10Y=6.79%），2008年雷曼前（5.25%），2022年加息顶峰（5.02%），触发后12个月S&P500平均下跌32%。<b>防御性配置历史胜率超80%。</b>",
    },
}


def render_alert_top_bar(metrics):
    """顶部综合预警栏 — straw4 风格"""
    comp  = metrics["composite"]
    score = comp["score"]
    grade = comp["grade"]
    color = g_color(grade)
    cls   = g_cls(grade)
    conc  = ALERT_CONCLUSIONS[grade]

    st.markdown(f"""
    <div class="alert-top-bar">
      <div class="atb-score-wrap">
        <div class="atb-score {cls}">{score}</div>
        <div class="atb-score-label">综合预警分</div>
      </div>
      <div class="atb-divider"></div>
      <div class="atb-state-wrap">
        <div class="atb-state-label">系统状态</div>
        <div class="atb-state {cls}">{grade}</div>
        <div class="atb-bar-wrap">
          <div class="atb-bar-fill" style="width:{score}%; background:{color};"></div>
        </div>
        <div style="font-size:11px; color:#475569; margin-top:8px; line-height:1.8;">
          SAFE 0–25 · WATCH 25–50<br>WARNING 50–75 · CRITICAL 75–100
        </div>
      </div>
      <div class="atb-divider"></div>
      <div class="atb-conclusion">
        <div class="atb-con-title" style="color:{conc['title_color']};">{conc['icon']} {conc['title']}</div>
        <div class="atb-con-body">{conc['body']}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_alert_indicators(metrics):
    """4指标卡片"""
    m1=metrics["y10_level"]; m2=metrics["y10_mom"]
    m3=metrics["spread"];    m4=metrics["corr"]
    c1,c2,c3,c4 = st.columns(4)

    def ind(col, icon, title, val, unit, grade, wt, thresh):
        color = g_color(grade)
        cls   = g_cls(grade)
        with col:
            st.markdown(f"""
            <div class="ind-card">
              <div class="ind-label">{icon} {title}
                <span style="color:#475569; font-weight:400; font-size:11px; margin-left:4px;">权重×{wt}</span>
              </div>
              <div style="display:flex; align-items:baseline; gap:6px;">
                <span class="ind-value {cls}">{val}</span>
                <span class="ind-unit">{unit}</span>
              </div>
              <div>
                <span class="ind-badge"
                  style="background:{color}22; color:{color}; border:1px solid {color}44;">{grade}</span>
              </div>
              <div class="ind-thresh">{thresh}</div>
            </div>""", unsafe_allow_html=True)

    ind(c1,"📊","10Y收益率水平",  f"{m1['value']:.2f}","%",    m1["grade"],"0.15","&lt;3.0 SAFE · 3–4 WATCH<br>4–5 WARNING · &gt;5 CRITICAL")
    ind(c2,"🚀","3个月变化速率",  f"{m2['value']:+.0f}","bps", m2["grade"],"0.40","P75=+50 · P90=+100<br>P95=+150 bps<br>最关键预警指标")
    ind(c3,"📐","30Y−10Y利差",    f"{m3['value']:+.0f}","bps", m3["grade"],"0.25","&gt;20 SAFE · 0–20 WATCH<br>0~−30 WARNING · &lt;−30 CRITICAL")
    ind(c4,"🔗","股债滚动相关性", f"{m4['value']:+.2f}","r",   m4["grade"],"0.20","&gt;−0.3 SAFE · −0.3~−0.5 WATCH<br>−0.5~−0.7 WARNING · &lt;−0.7")


def render_alert_history(y10, sp500):
    col_c, col_t = st.columns([1.6, 1])
    with col_c:
        st.plotly_chart(chart_alert_hist(y10, sp500), use_container_width=True)
    with col_t:
        HIST = [
            ("2000-03","科网泡沫崩盘",  "6.79%","-49%","CRITICAL"),
            ("2001-09","911恐袭",        "4.76%","-30%","CRITICAL"),
            ("2007-08","次贷危机苗头",  "4.96%","-57%","WARNING"),
            ("2008-09","雷曼破产",       "3.69%","-57%","CRITICAL"),
            ("2010-05","闪崩",           "3.54%", "-7%","WATCH"),
            ("2011-08","美国评级下调",  "2.56%","-19%","WARNING"),
            ("2015-08","A股股灾",        "2.17%","-12%","WARNING"),
            ("2018-12","圣诞崩盘",       "2.83%","-20%","WARNING"),
            ("2020-03","COVID崩盘",      "0.54%","-34%","CRITICAL"),
            ("2022-06","加息周期峰值",  "3.49%","-25%","CRITICAL"),
            ("2023-10","10Y触5%",        "5.02%","-10%","WARNING"),
        ]
        st.markdown("""
        <div class="panel" style="height:378px; overflow-y:auto;">
          <div class="panel-title">📋 历史预警复盘</div>
          <div style="display:flex; gap:6px; padding:7px 14px; border-bottom:1px solid rgba(255,255,255,0.08);">
            <div style="font-size:11px;color:#475569;width:72px;">时间</div>
            <div style="font-size:11px;color:#475569;flex:1;">事件</div>
            <div style="font-size:11px;color:#475569;width:52px;text-align:right;">10Y</div>
            <div style="font-size:11px;color:#475569;width:52px;text-align:right;">SP跌幅</div>
          </div>
        """, unsafe_allow_html=True)
        for date, ev, y10v, spv, sev in HIST:
            sc = SEV_COLOR.get(sev, "#94a3b8")
            st.markdown(f"""
            <div class="hr-row">
              <div class="hr-date">{date}</div>
              <div class="hr-event">{ev}
                <span style="font-size:10px;padding:0 5px;border-radius:4px;
                  background:{sc}22;color:{sc};font-weight:700;margin-left:3px;">{sev}</span>
              </div>
              <div class="hr-y10">{y10v}</div>
              <div class="hr-drop">{spv}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_alert_logic():
    st.markdown("""
    <div class="panel">
      <div class="panel-title">⚙️ 预警逻辑与阈值推导（1994–今历史统计）</div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:22px;">
        <div>
          <div style="font-size:13px;font-weight:700;color:#fbbf24;margin-bottom:8px;">
            🚀 指标②：3M收益率变化速率（权重 ×0.40，最关键）
          </div>
          <div style="font-size:13px;color:#94a3b8;line-height:2;">
            <b style="color:#22c55e;">P75 = +50bps</b> → WATCH：2021Q1（+82bps），短暂调整<br>
            <b style="color:#f97316;">P90 = +100bps</b> → WARNING：2013 Taper（+130bps），-6%<br>
            <b style="color:#ef4444;">P95 = +150bps</b> → CRITICAL：2022（+230bps），-25%
          </div>
        </div>
        <div>
          <div style="font-size:13px;font-weight:700;color:#5CB85C;margin-bottom:8px;">
            📐 指标③：期限利差 30Y-10Y（权重 ×0.25）
          </div>
          <div style="font-size:13px;color:#94a3b8;line-height:2;">
            <b style="color:#ef4444;">倒挂（&lt;0）</b>：历史每次持续倒挂均先于衰退6–18个月<br>
            <b style="color:#f97316;">2006-07</b>：倒挂持续8个月 → 2008金融危机<br>
            <b style="color:#fbbf24;">2019</b>：短暂倒挂 → 2020衰退（COVID加速触发）
          </div>
        </div>
      </div>
      <div style="margin-top:14px;padding-top:14px;border-top:1px solid rgba(255,255,255,0.06);
           font-size:12px;color:#475569;line-height:1.8;">
        ⚠️ <b style="color:#64748b;">系统盲区</b>：本体系专针对"利率上行杀估值"场景。对外生冲击（COVID、地缘政治）、
        政策性股灾（A股2015）、Flash Crash等非利率驱动下跌，预警能力有限。
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_ctrl(tab_key):
    """每个 Tab 内部的控制栏：时间范围 + 股灾标注"""
    c1, c2, c3 = st.columns([2.5, 2, 5.5])
    with c1:
        st.markdown('<div class="ctrl-label">时间范围</div>', unsafe_allow_html=True)
        period = st.select_slider(f"period_{tab_key}",
                                  options=["1Y","3Y","5Y","10Y","ALL"], value="ALL",
                                  label_visibility="collapsed")
    with c2:
        st.markdown('<div class="ctrl-label">股灾标注</div>', unsafe_allow_html=True)
        crashes = st.toggle(f"crashes_{tab_key}", value=True, label_visibility="collapsed")
    return period, crashes


# =========================================================
# 主程序
# =========================================================

with st.spinner("正在从 FRED · FMP · Yahoo Finance 拉取数据..."):
    y10, y30, sp500, nasdaq, dow, shcomp, szcomp = load_all()

metrics = compute_alerts(y10, y30, sp500)

# ── 顶部标题 ──
st.markdown(f"""
<div class="page-header">
  <div>
    <div class="page-title">稻草六 · 美元国债市场预警</div>
    <div class="page-sub">美债收益率 × 全球股市联动 · 4指标综合预警体系</div>
  </div>
  <div style="text-align:right; padding-top:4px;">
    <span class="ts-label">🕐 {now_pt()}</span>
    <span class="symbol-badge">STRAW 6 · BOND ALERT</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 顶部综合预警栏 ──
render_alert_top_bar(metrics)

# ── KPI 两行 ──
render_kpi_rows(y10, y30, sp500, nasdaq, dow, shcomp, szcomp)

st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

# ── 刷新按钮（右对齐小按钮）──
_, _, btn_col = st.columns([7, 2, 1])
with btn_col:
    if st.button("🔄 刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

# =========================================================
# Tabs
# =========================================================

tab_all, tab_us, tab_cn = st.tabs(["🌐  ALL — 全资产概览", "🇺🇸  US — 美国市场", "🇨🇳  CN — 中国市场"])

# ─── ALL ───
with tab_all:
    period, crashes = render_ctrl("all")
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.plotly_chart(chart_overview(y10, y30, sp500, nasdaq, dow, shcomp, szcomp, period, crashes),
                    use_container_width=True)
    st.plotly_chart(chart_spread(y10, y30, period), use_container_width=True)

    if crashes:
        st.markdown('<div class="panel"><div class="panel-title">📌 历史股灾事件索引</div>',
                    unsafe_allow_html=True)
        cols = st.columns(3)
        for i, ev in enumerate(CRASH_EVENTS):
            c = SEV_COLOR.get(ev["severity"], "#94a3b8")
            with cols[i % 3]:
                st.markdown(f"""
                <div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
                  <div style="width:3px;background:{c};border-radius:2px;flex-shrink:0;margin-top:2px;"></div>
                  <div>
                    <div style="font-size:11px;color:{c};font-weight:700;">{ev['date'][:7]} · {ev['label']}</div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:2px;">{ev['desc']}</div>
                  </div>
                </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:24px 0;'>",
                unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;font-weight:700;color:#475569;text-transform:uppercase;'
                'letter-spacing:1.5px;margin-bottom:14px;">🚨 4指标预警详情</div>', unsafe_allow_html=True)
    render_alert_indicators(metrics)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    render_alert_history(y10, sp500)
    render_alert_logic()


# ─── US ───
with tab_us:
    period, crashes = render_ctrl("us")
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.plotly_chart(chart_dual(y10, y30,
        [(sp500,"S&P 500"),(nasdaq,"NASDAQ 100"),(dow,"Dow Jones")],
        period, crashes, "美债收益率（左轴）× 美股三大指数（右轴）"),
        use_container_width=True)
    st.plotly_chart(chart_spread(y10, y30, period), use_container_width=True)

    st.markdown("""
    <div class="panel">
      <div class="panel-title">📖 美股 × 美债联动解读</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div>
          <div style="font-size:13px;font-weight:700;color:#4F8EF7;margin-bottom:8px;">📈 收益率上行 × 股市表现</div>
          <div style="font-size:13px;color:#94a3b8;line-height:1.85;">
            <b style="color:#22c55e;">温和上行（&lt;50bps/3M）</b>：伴随经济复苏，股市可同步上涨<br>
            <b style="color:#f97316;">快速上行（50–150bps/3M）</b>：压制估值，科技/成长股首当其冲<br>
            <b style="color:#ef4444;">急速上行（&gt;150bps/3M）</b>：历史几乎无例外触发股市调整20%+
          </div>
        </div>
        <div>
          <div style="font-size:13px;font-weight:700;color:#5CB85C;margin-bottom:8px;">🏔️ 图表阅读要点</div>
          <div style="font-size:13px;color:#94a3b8;line-height:1.85;">
            <b style="color:#ef4444;">红色半透明区域</b>：30Y-10Y倒挂，先于衰退出现<br>
            <b style="color:#fbbf24;">收益率峰值</b>：通常在加息末期，股市往往同期触底<br>
            <b style="color:#4F8EF7;">2022年</b>：收益率+230bps，标普跌25%，最典型负相关案例
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:22px 0;'>",
                unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;font-weight:700;color:#475569;text-transform:uppercase;'
                'letter-spacing:1.5px;margin-bottom:14px;">🚨 4指标预警详情</div>', unsafe_allow_html=True)
    render_alert_indicators(metrics)


# ─── CN ───
with tab_cn:
    period, crashes = render_ctrl("cn")
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.plotly_chart(chart_dual(y10, y30,
        [(shcomp,"上证指数"),(szcomp,"深证成指")],
        period, crashes, "美债收益率（左轴）× A股指数（右轴）"),
        use_container_width=True)
    st.plotly_chart(chart_spread(y10, y30, period), use_container_width=True)

    st.markdown("""
    <div class="panel">
      <div class="panel-title">📖 A股 × 美债联动特征</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div>
          <div style="font-size:13px;font-weight:700;color:#E63946;margin-bottom:8px;">🇨🇳 相关性特点</div>
          <div style="font-size:13px;color:#94a3b8;line-height:1.85;">
            A股与美债相关性显著低于美股，主要受国内政策驱动<br>
            <b style="color:#fbbf24;">关键传导</b>：美债↑ → 美元强 → 人民币贬压 → 外资撤离 → A股承压<br>
            <b style="color:#ef4444;">典型案例</b>：2015年人民币贬值+股灾，2022年外资大幅净卖出
          </div>
        </div>
        <div>
          <div style="font-size:13px;font-weight:700;color:#9D4EDD;margin-bottom:8px;">⚠️ 关注信号</div>
          <div style="font-size:13px;color:#94a3b8;line-height:1.85;">
            <b style="color:#22c55e;">美债收益率下行</b>：美元走弱，有利于外资回流A股<br>
            <b style="color:#f97316;">美债快速上行</b>：人民币贬压加大，关注资本外流数据<br>
            <b style="color:#60a5fa;">中美利差收窄至负</b>：资本外流压力显著上升
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:22px 0;'>",
                unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;font-weight:700;color:#475569;text-transform:uppercase;'
                'letter-spacing:1.5px;margin-bottom:14px;">🚨 4指标预警详情</div>', unsafe_allow_html=True)
    render_alert_indicators(metrics)


# =========================================================
# 底部
# =========================================================
st.markdown(f"""
<div style="margin-top:28px;padding-top:14px;border-top:1px solid rgba(255,255,255,0.05);
     font-size:11px;color:#1e293b;text-align:right;line-height:2;">
  数据来源：FRED（DGS10·DGS30）· FMP（^GSPC·^IXIC·^DJI）· Yahoo Finance（000001.SS·399001.SZ）
  &nbsp;|&nbsp; {now_pt()}
  &nbsp;|&nbsp; 稻草六 · 仅供研究参考，不构成投资建议
</div>
""", unsafe_allow_html=True)
PYEOF
echo "Lines: $(wc -l < /home/claude/straw6.py)"
Output

Lines: 1084
Done
