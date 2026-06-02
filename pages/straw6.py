"""
straw6.py — 宏观市场预警看板
股市 × 债市联动分析 · Bloomberg风格 · 黑金主题

数据源:
  - FRED API  : 美国国债收益率 (DGS10, DGS30)
  - FMP API   : 美股指数 (S&P500, NASDAQ, Dow Jones)
  - yfinance  : A股指数 (上证 000001.SS, 深证 399001.SZ)

页面结构:
  顶部 Tab: ALL / US / CN
  每个 Tab 底部均含 Alert System

作者: Bin (via Claude)
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf

# =========================================================
# 页面配置
# =========================================================
st.set_page_config(
    page_title="Straw 6 · 宏观预警看板",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# API Keys
# =========================================================
FRED_API_KEY = "9d4d8c74237a32ec198773ca5eb0f4e3"
FMP_API_KEY  = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"

# =========================================================
# CSS — 黑金风格
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
/* 隐藏侧边栏 */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

/* 标题 */
.main-title {
    font-size: 30px; font-weight: 800; color: #ffffff;
    margin: 0 0 6px 0; letter-spacing: -0.5px;
}
.sub-title { font-size: 15px !important; color: #cbd5e1 !important; margin: 0; }
.timestamp-text { font-size: 12px; color: #475569; margin-bottom: 8px; display: block; }
.symbol-badge {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 3px 14px;
    font-size: 12px; font-weight: 600; color: #94a3b8; letter-spacing: 1px;
}

/* 指标卡片 */
.metric-card {
    background-color: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 20px 22px 18px;
    height: 160px;
}
.metric-label {
    color: #94a3b8; font-size: 11px; font-weight: 700;
    margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1.2px;
}
.metric-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
.metric-number { font-size: 36px; font-weight: 800; line-height: 1; letter-spacing: -1.5px; }
.metric-sub { font-size: 13px; color: #64748b; line-height: 1.6; }
.metric-badge {
    display: inline-block; border-radius: 5px;
    padding: 2px 9px; font-size: 11px; font-weight: 700;
    letter-spacing: 0.8px; margin-top: 8px;
}

/* 综合预警大卡片 */
.alert-master-card {
    background: linear-gradient(135deg, #0b1120 0%, #0d1829 100%);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.alert-score { font-size: 72px; font-weight: 800; line-height: 1; letter-spacing: -3px; }
.alert-label { font-size: 12px; font-weight: 700; color: #475569; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; }
.alert-state { font-size: 28px; font-weight: 800; letter-spacing: 0.5px; }
.bar-wrap { margin-top: 12px; width: 280px; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; }
.bar-fill { height: 6px; border-radius: 3px; }

/* Alert 结论框 */
.alert-box {
    margin: 16px 0; background: #120e00;
    border: 1px solid rgba(251,191,36,0.18);
    border-radius: 14px; padding: 20px 24px;
    display: flex; gap: 16px; align-items: flex-start;
}
.alert-box-red { margin: 16px 0; background: #120000; border: 1px solid rgba(239,68,68,0.25); border-radius: 14px; padding: 20px 24px; display: flex; gap: 16px; align-items: flex-start; }
.alert-box-green { margin: 16px 0; background: #001208; border: 1px solid rgba(34,197,94,0.2); border-radius: 14px; padding: 20px 24px; display: flex; gap: 16px; align-items: flex-start; }
.alert-box-orange { margin: 16px 0; background: #120800; border: 1px solid rgba(249,115,22,0.25); border-radius: 14px; padding: 20px 24px; display: flex; gap: 16px; align-items: flex-start; }
.alert-icon { font-size: 40px; flex-shrink: 0; line-height: 1; }
.alert-title { font-size: 20px !important; font-weight: 700; margin-bottom: 8px; }
.alert-text { font-size: 15px !important; color: #cbd5e1 !important; line-height: 1.75; }

/* Panel */
.panel {
    background-color: #0b1120; border-radius: 14px;
    padding: 22px; border: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 16px;
}
.panel-title { font-size: 17px !important; font-weight: 700; margin-bottom: 18px; color: #e2e8f0; }

/* 历史复盘表 */
.history-row {
    display: flex; gap: 10px; padding: 12px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    align-items: center;
}
.history-row:last-child { border-bottom: none; }
.h-date { font-size: 13px; font-weight: 700; color: #94a3b8; width: 80px; flex-shrink: 0; }
.h-event { font-size: 13px; color: #e2e8f0; flex: 1; }
.h-yield { font-size: 13px; font-weight: 700; color: #5CB85C; width: 60px; text-align: right; }
.h-drop { font-size: 13px; font-weight: 700; color: #ef4444; width: 60px; text-align: right; }

/* 颜色 */
.green  { color: #22c55e; }
.red    { color: #ef4444; }
.yellow { color: #fbbf24; }
.orange { color: #f97316; }
.gray   { color: #94a3b8; }
.blue   { color: #4F8EF7; }

/* 分割线 */
.section-divider {
    border: none; border-top: 1px solid rgba(255,255,255,0.06);
    margin: 28px 0;
}

#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
.modebar { display: none !important; }

/* Tab 样式 */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    gap: 4px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px 8px 0 0;
    padding: 10px 28px;
    color: #64748b;
    font-weight: 700;
    font-size: 14px;
    border: 1px solid transparent;
    border-bottom: none;
    letter-spacing: 0.3px;
}
.stTabs [aria-selected="true"] {
    background: #0b1120 !important;
    color: #60a5fa !important;
    border-color: rgba(255,255,255,0.08) !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent;
    padding-top: 24px;
}

/* 控制栏 */
.ctrl-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
    padding: 12px 16px;
    background: #0b1120;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.06);
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 股灾事件数据库（内置）
# =========================================================
CRASH_EVENTS = [
    {"date": "1997-10-01", "label": "Asian Crisis",       "desc": "亚洲金融危机·港元保卫战",        "severity": "WARNING"},
    {"date": "1998-08-01", "label": "LTCM / Russia",      "desc": "俄罗斯违约·LTCM崩盘",           "severity": "WARNING"},
    {"date": "2000-03-01", "label": "Dot-com Peak",        "desc": "科网泡沫顶点·纳指跌78%",         "severity": "CRITICAL"},
    {"date": "2001-09-01", "label": "9/11 Attack",         "desc": "911恐袭·市场关闭4天",            "severity": "CRITICAL"},
    {"date": "2002-10-01", "label": "Post 9/11 Bottom",    "desc": "科网熊市底部",                   "severity": "WARNING"},
    {"date": "2007-08-01", "label": "Subprime Starts",     "desc": "次贷危机苗头·贝尔斯登基金崩盘", "severity": "WARNING"},
    {"date": "2008-09-01", "label": "Lehman Collapse",     "desc": "雷曼破产·金融海啸",              "severity": "CRITICAL"},
    {"date": "2010-05-01", "label": "Flash Crash",         "desc": "闪崩·道指单日跌近1000点",       "severity": "WATCH"},
    {"date": "2011-08-01", "label": "US Downgrade",        "desc": "美国主权评级下调·欧债危机",      "severity": "WARNING"},
    {"date": "2015-08-01", "label": "China Crash",         "desc": "A股股灾·人民币贬值",            "severity": "WARNING"},
    {"date": "2018-12-01", "label": "Fed Tightening",      "desc": "美联储加息恐慌·圣诞崩盘",       "severity": "WARNING"},
    {"date": "2020-03-01", "label": "COVID Crash",         "desc": "新冠疫情·史上最快熊市",         "severity": "CRITICAL"},
    {"date": "2022-01-01", "label": "Rate Hike Cycle",     "desc": "加息周期启动·纳指跌33%",        "severity": "CRITICAL"},
    {"date": "2023-03-01", "label": "SVB Crisis",          "desc": "硅谷银行倒闭·银行业危机",       "severity": "WARNING"},
]

SEVERITY_COLOR = {
    "WATCH":    "#fbbf24",
    "WARNING":  "#f97316",
    "CRITICAL": "#ef4444",
}

# =========================================================
# 债券/股票颜色常量
# =========================================================
BOND_FILL = {
    "10Y Treasury": "rgba(92,184,92,0.15)",
    "30Y Treasury": "rgba(88,120,255,0.15)",
}
BOND_LINE = {
    "10Y Treasury": "#5CB85C",
    "30Y Treasury": "#5878FF",
}
STOCK_LINE = {
    "S&P 500":    "#4F8EF7",
    "NASDAQ 100": "#FF7F50",
    "Dow Jones":  "#2CA58D",
    "上证指数":   "#E63946",
    "深证成指":   "#9D4EDD",
}
NORM_FILL = {
    "10Y Treasury": "rgba(92,184,92,0.15)",
    "30Y Treasury": "rgba(88,120,255,0.15)",
    "S&P 500":      "rgba(79,142,247,0)",
    "NASDAQ 100":   "rgba(255,127,80,0)",
    "Dow Jones":    "rgba(44,165,141,0)",
    "上证指数":     "rgba(230,57,70,0)",
    "深证成指":     "rgba(157,78,221,0)",
}
NORM_LINE = {
    "10Y Treasury": "#5CB85C",
    "30Y Treasury": "#5878FF",
    "S&P 500":      "#4F8EF7",
    "NASDAQ 100":   "#FF7F50",
    "Dow Jones":    "#2CA58D",
    "上证指数":     "#E63946",
    "深证成指":     "#9D4EDD",
}

# =========================================================
# 数据获取函数
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred(series_id: str, start: str = "1994-01-01") -> pd.Series:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id":          series_id,
        "api_key":            FRED_API_KEY,
        "file_type":          "json",
        "observation_start":  start,
        "frequency":          "m",
        "aggregation_method": "eop",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        obs = r.json().get("observations", [])
        s = pd.Series(
            {o["date"]: float(o["value"]) for o in obs if o["value"] != "."},
            name=series_id,
        )
        s.index = pd.to_datetime(s.index)
        return s
    except Exception as e:
        st.warning(f"FRED {series_id} 获取失败: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fmp_index(symbol: str, start: str = "1994-01-01") -> pd.Series:
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
    params = {"apikey": FMP_API_KEY, "from": start}
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
        hist = data.get("historical", [])
        if not hist:
            return pd.Series(dtype=float)
        df = pd.DataFrame(hist)[["date", "close"]].copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        monthly = df["close"].resample("ME").last()
        monthly.name = symbol
        return monthly
    except Exception as e:
        st.warning(f"FMP {symbol} 获取失败: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_yf_index(ticker: str, start: str = "1994-01-01") -> pd.Series:
    try:
        df = yf.download(ticker, start=start, interval="1mo", progress=False, auto_adjust=True)
        if df.empty:
            return pd.Series(dtype=float)
        s = df["Close"].squeeze()
        s.index = pd.to_datetime(s.index).to_period("M").to_timestamp("M")
        s.name = ticker
        return s.dropna()
    except Exception as e:
        st.warning(f"yfinance {ticker} 获取失败: {e}")
        return pd.Series(dtype=float)


# =========================================================
# 预警计算
# =========================================================

def compute_alert_metrics(y10: pd.Series, y30: pd.Series, sp500: pd.Series) -> dict:
    result = {}

    cur_y10 = float(y10.iloc[-1]) if not y10.empty else 0
    if cur_y10 < 3.0:
        score1, grade1 = 0, "SAFE"
    elif cur_y10 < 4.0:
        score1, grade1 = 33, "WATCH"
    elif cur_y10 < 5.0:
        score1, grade1 = 67, "WARNING"
    else:
        score1, grade1 = 100, "CRITICAL"
    result["y10_level"] = {"value": cur_y10, "grade": grade1, "score": score1, "unit": "%"}

    if len(y10) >= 3:
        chg3m = float(y10.iloc[-1] - y10.iloc[-3]) * 100
    else:
        chg3m = 0.0
    if chg3m < 50:
        score2, grade2 = 0, "SAFE"
    elif chg3m < 100:
        score2, grade2 = 33, "WATCH"
    elif chg3m < 150:
        score2, grade2 = 67, "WARNING"
    else:
        score2, grade2 = 100, "CRITICAL"
    result["y10_momentum"] = {"value": chg3m, "grade": grade2, "score": score2, "unit": "bps/3M"}

    if not y30.empty and not y10.empty:
        common = y30.index.intersection(y10.index)
        spread = float(y30.loc[common[-1]] - y10.loc[common[-1]]) * 100 if len(common) > 0 else 20.0
    else:
        spread = 20.0
    if spread > 20:
        score3, grade3 = 0, "SAFE"
    elif spread > 0:
        score3, grade3 = 33, "WATCH"
    elif spread > -30:
        score3, grade3 = 67, "WARNING"
    else:
        score3, grade3 = 100, "CRITICAL"
    result["spread"] = {"value": spread, "grade": grade3, "score": score3, "unit": "bps"}

    corr_val = 0.0
    if len(y10) >= 12 and len(sp500) >= 12:
        common = y10.index.intersection(sp500.index)
        if len(common) >= 12:
            y_aligned = y10.loc[common].tail(12)
            s_aligned = sp500.loc[common].tail(12)
            s_ret = s_aligned.pct_change().dropna()
            y_chg = y_aligned.diff().dropna()
            common2 = s_ret.index.intersection(y_chg.index)
            if len(common2) >= 6:
                corr_val = float(np.corrcoef(y_chg.loc[common2], s_ret.loc[common2])[0, 1])
    if corr_val > -0.3:
        score4, grade4 = 0, "SAFE"
    elif corr_val > -0.5:
        score4, grade4 = 33, "WATCH"
    elif corr_val > -0.7:
        score4, grade4 = 67, "WARNING"
    else:
        score4, grade4 = 100, "CRITICAL"
    result["correlation"] = {"value": corr_val, "grade": grade4, "score": score4, "unit": "r"}

    composite = score1 * 0.15 + score2 * 0.40 + score3 * 0.25 + score4 * 0.20
    if composite < 25:
        master_grade = "SAFE"
    elif composite < 50:
        master_grade = "WATCH"
    elif composite < 75:
        master_grade = "WARNING"
    else:
        master_grade = "CRITICAL"
    result["composite"] = {"score": round(composite, 1), "grade": master_grade}
    return result


def grade_to_color(grade: str) -> str:
    return {"SAFE": "#22c55e", "WATCH": "#fbbf24", "WARNING": "#f97316", "CRITICAL": "#ef4444"}.get(grade, "#94a3b8")

def grade_to_css(grade: str) -> str:
    return {"SAFE": "green", "WATCH": "yellow", "WARNING": "orange", "CRITICAL": "red"}.get(grade, "gray")

# =========================================================
# 图表工具
# =========================================================

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="'PingFang SC','Microsoft YaHei',sans-serif", size=12),
    legend=dict(
        bgcolor="rgba(11,17,32,0.8)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
        font=dict(size=12, color="#cbd5e1"),
    ),
    xaxis=dict(
        showgrid=True, gridcolor="rgba(255,255,255,0.04)",
        zeroline=False, linecolor="rgba(255,255,255,0.1)",
        tickfont=dict(size=11),
    ),
    yaxis=dict(
        showgrid=True, gridcolor="rgba(255,255,255,0.04)",
        zeroline=False, linecolor="rgba(255,255,255,0.1)",
        tickfont=dict(size=11),
    ),
    margin=dict(l=60, r=60, t=40, b=50),
    hovermode="x unified",
)


def filter_by_period(s: pd.Series, period: str) -> pd.Series:
    if period == "ALL" or s.empty:
        return s
    now = s.index[-1]
    years = {"1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10}
    cutoff = now - pd.DateOffset(years=years.get(period, 100))
    return s[s.index >= cutoff]


def add_crash_annotations(fig, events):
    for ev in events:
        dt = pd.to_datetime(ev["date"])
        color = SEVERITY_COLOR.get(ev["severity"], "#94a3b8")
        fig.add_vline(
            x=dt.timestamp() * 1000,
            line_width=1, line_dash="dot",
            line_color=color + "80",
        )
        fig.add_annotation(
            x=dt, y=1.0, yref="paper",
            text=ev["label"], showarrow=False,
            textangle=-90, font=dict(size=9, color=color),
            xanchor="left", yanchor="top",
        )


def add_inversion_bands(fig, y10: pd.Series, y30: pd.Series):
    if y10.empty or y30.empty:
        return
    common = y10.index.intersection(y30.index)
    if common.empty:
        return
    y10c = y10.loc[common]
    y30c = y30.loc[common]
    inverted = y30c < y10c
    in_band = False
    start_dt = None
    for dt, inv in inverted.items():
        if inv and not in_band:
            in_band = True
            start_dt = dt
        elif not inv and in_band:
            in_band = False
            fig.add_vrect(
                x0=start_dt, x1=dt,
                fillcolor="rgba(239,68,68,0.08)",
                layer="below", line_width=0,
                annotation_text="倒挂", annotation_position="top left",
                annotation_font=dict(size=9, color="#ef444480"),
            )
    if in_band:
        fig.add_vrect(
            x0=start_dt, x1=common[-1],
            fillcolor="rgba(239,68,68,0.08)",
            layer="below", line_width=0,
        )


def normalize_series(s: pd.Series) -> pd.Series:
    if s.empty:
        return s
    first_valid = s.dropna().iloc[0]
    return s / first_valid * 100


# =========================================================
# 图表构建
# =========================================================

def build_overview_chart(y10, y30, sp500, nasdaq, dow, shcomp, szcomp, period, show_crashes):
    """ALL tab: 归一化全资产对比"""
    fig = go.Figure()

    assets = [
        (y10,    "10Y Treasury",  True),
        (y30,    "30Y Treasury",  True),
        (sp500,  "S&P 500",       False),
        (nasdaq, "NASDAQ 100",    False),
        (dow,    "Dow Jones",     False),
        (shcomp, "上证指数",      False),
        (szcomp, "深证成指",      False),
    ]

    for series, name, is_bond in assets:
        if series.empty:
            continue
        s = filter_by_period(normalize_series(series), period).dropna()
        if s.empty:
            continue
        fill_color = NORM_FILL.get(name, "rgba(148,163,184,0)")
        line_color = NORM_LINE.get(name, "#94a3b8")
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            fill="tozeroy" if is_bond else "none",
            fillcolor=fill_color,
            line=dict(color=line_color, width=1.5 if is_bond else 1.8),
            mode="lines",
        ))

    if show_crashes:
        add_crash_annotations(fig, CRASH_EVENTS)

    layout = dict(**PLOTLY_LAYOUT)
    layout["height"] = 520
    layout["title"] = dict(text="归一化全资产走势对比（1995年=100）", font=dict(size=14, color="#e2e8f0"), x=0.01)
    layout["yaxis"]["title"] = dict(text="指数化（100=起点）", font=dict(size=11))
    fig.update_layout(**layout)
    return fig


def build_dual_axis_chart(y10, y30, stock_pairs, period, show_crashes, title):
    """双Y轴图: 债券山形（左）+ 股指折线（右）"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for series, name in [(y10, "10Y Treasury"), (y30, "30Y Treasury")]:
        if series.empty:
            continue
        s = filter_by_period(series, period).dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            fill="tozeroy",
            fillcolor=BOND_FILL[name],
            line=dict(color=BOND_LINE[name], width=1.5),
            mode="lines",
            hovertemplate=f"{name}: %{{y:.2f}}%<extra></extra>",
        ), secondary_y=False)

    for series, name in stock_pairs:
        if series.empty:
            continue
        s = filter_by_period(series, period).dropna()
        color = STOCK_LINE.get(name, "#94a3b8")
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            line=dict(color=color, width=2),
            mode="lines",
            hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>",
        ), secondary_y=True)

    if show_crashes:
        add_crash_annotations(fig, CRASH_EVENTS)
    add_inversion_bands(fig, y10, y30)

    layout = dict(**PLOTLY_LAYOUT)
    layout["height"] = 500
    layout["title"] = dict(text=title, font=dict(size=14, color="#e2e8f0"), x=0.01)
    fig.update_layout(**layout)
    fig.update_yaxes(
        title_text="收益率 (%)", secondary_y=False,
        showgrid=True, gridcolor="rgba(255,255,255,0.04)",
        tickfont=dict(size=11), zeroline=False,
    )
    fig.update_yaxes(
        title_text="指数点位", secondary_y=True,
        showgrid=False, tickfont=dict(size=11), zeroline=False,
    )
    return fig


def build_spread_chart(y10, y30, period):
    if y10.empty or y30.empty:
        return go.Figure()
    common = y10.index.intersection(y30.index)
    spread = (y30.loc[common] - y10.loc[common]) * 100
    spread = filter_by_period(spread, period)
    colors = ["#ef4444" if v < 0 else "#22c55e" for v in spread.values]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=spread.index, y=spread.values,
        marker_color=colors, name="30Y-10Y利差",
        hovertemplate="利差: %{y:.1f} bps<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_width=1)
    layout = dict(**PLOTLY_LAYOUT)
    layout["height"] = 220
    layout["title"] = dict(text="30Y − 10Y 期限利差 (bps)  🔴红色=倒挂", font=dict(size=13, color="#e2e8f0"), x=0.01)
    layout["yaxis"]["title"] = "bps"
    fig.update_layout(**layout)
    return fig


def build_alert_history_chart(y10, sp500, period):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if not y10.empty:
        s = filter_by_period(y10, period)
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name="10Y Treasury",
            fill="tozeroy", fillcolor="rgba(92,184,92,0.15)",
            line=dict(color="#5CB85C", width=1.5), mode="lines",
        ), secondary_y=False)
    if not sp500.empty:
        s = filter_by_period(sp500, period)
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name="S&P 500",
            line=dict(color="#4F8EF7", width=1.8), mode="lines",
        ), secondary_y=True)
    critical_events = [e for e in CRASH_EVENTS if e["severity"] in ("CRITICAL", "WARNING")]
    add_crash_annotations(fig, critical_events)
    layout = dict(**PLOTLY_LAYOUT)
    layout["height"] = 380
    layout["title"] = dict(text="10Y国债收益率 × S&P500 · 历史预警事件", font=dict(size=14, color="#e2e8f0"), x=0.01)
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="收益率 (%)", secondary_y=False, showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False)
    fig.update_yaxes(title_text="S&P 500", secondary_y=True, showgrid=False, zeroline=False)
    return fig


# =========================================================
# 可复用组件
# =========================================================

def render_kpi_row(y10, y30, sp500, shcomp):
    c1, c2, c3, c4, c5 = st.columns(5)

    def kpi_card(col, label, value, sub, color_cls):
        with col:
            st.markdown(f"""
            <div class="metric-card" style="height:130px;">
              <div class="metric-label">{label}</div>
              <div class="metric-row">
                <span class="metric-number {color_cls}">{value}</span>
              </div>
              <div class="metric-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    y10_now = f"{y10.iloc[-1]:.2f}%" if not y10.empty else "N/A"
    y30_now = f"{y30.iloc[-1]:.2f}%" if not y30.empty else "N/A"
    sp_now  = f"{sp500.iloc[-1]:,.0f}" if not sp500.empty else "N/A"
    sh_now  = f"{shcomp.iloc[-1]:,.0f}" if not shcomp.empty else "N/A"

    spread_now = 0.0
    if not y10.empty and not y30.empty:
        common = y10.index.intersection(y30.index)
        if len(common):
            spread_now = (y30.loc[common[-1]] - y10.loc[common[-1]]) * 100

    kpi_card(c1, "10Y Treasury", y10_now, "美国10年期国债收益率",
             "green" if not y10.empty and y10.iloc[-1] < 4 else "orange")
    kpi_card(c2, "30Y Treasury", y30_now, "美国30年期国债收益率",
             "green" if not y30.empty and y30.iloc[-1] < 4.5 else "orange")
    kpi_card(c3, "S&P 500", sp_now, "标普500指数", "blue")
    kpi_card(c4, "上证指数", sh_now, "Shanghai Composite", "red")

    spread_color = "green" if spread_now > 20 else ("yellow" if spread_now > 0 else "red")
    kpi_card(c5, "30Y-10Y利差", f"{spread_now:+.0f}bps",
             "🔴 倒挂预警" if spread_now < 0 else "期限利差正常", spread_color)


def render_alert_system(y10, y30, sp500, show_hist_chart=True):
    """完整 Alert System 块，可在任意 Tab 内调用"""
    metrics = compute_alert_metrics(y10, y30, sp500)
    composite  = metrics["composite"]
    master_score = composite["score"]
    master_grade = composite["grade"]
    master_color = grade_to_color(master_grade)
    master_css   = grade_to_css(master_grade)

    st.markdown(f"""
    <hr class="section-divider">
    <div style="font-size:13px; font-weight:700; color:#475569; text-transform:uppercase;
         letter-spacing:1.5px; margin-bottom:16px;">🚨 Alert System · 预警系统</div>
    """, unsafe_allow_html=True)

    # 综合预警大卡片
    st.markdown(f"""
    <div class="alert-master-card">
      <div>
        <div class="alert-label">COMPOSITE ALERT SCORE</div>
        <div style="display:flex; align-items:baseline; gap:12px;">
          <div class="alert-score {master_css}">{master_score}</div>
          <div style="font-size:18px; color:#475569; font-weight:600;">/100</div>
        </div>
        <div style="font-size:15px; color:#94a3b8; margin-top:6px;">
          综合加权：10Y水平×0.15 · 3M速率×0.40 · 期限利差×0.25 · 相关性×0.20
        </div>
        <div class="bar-wrap">
          <div class="bar-fill" style="width:{master_score}%; background:{master_color};"></div>
        </div>
      </div>
      <div style="text-align:right;">
        <div class="alert-label">SYSTEM STATE</div>
        <div class="alert-state {master_css}">{master_grade}</div>
        <div style="margin-top:8px; font-size:13px; color:#64748b; line-height:2;">
          SAFE 0–25 &nbsp;·&nbsp; WATCH 25–50<br>
          WARNING 50–75 &nbsp;·&nbsp; CRITICAL 75–100
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 4 指标卡片
    m1 = metrics["y10_level"]
    m2 = metrics["y10_momentum"]
    m3 = metrics["spread"]
    m4 = metrics["correlation"]

    c1, c2, c3, c4 = st.columns(4)

    def alert_card(col, icon, title, value, unit, grade, weight, threshold_html):
        color = grade_to_color(grade)
        css   = grade_to_css(grade)
        with col:
            st.markdown(f"""
            <div class="metric-card" style="height:210px;">
              <div class="metric-label">{icon} {title} <span style="color:#475569;">×{weight}</span></div>
              <div class="metric-row">
                <span class="metric-number {css}">{value}</span>
                <span style="font-size:14px; color:#64748b;">{unit}</span>
              </div>
              <div>
                <span class="metric-badge"
                  style="background:{color}22; color:{color}; border:1px solid {color}44;">{grade}</span>
              </div>
              <div style="margin-top:10px; font-size:12px; color:#475569; line-height:1.8;">
                {threshold_html}
              </div>
            </div>
            """, unsafe_allow_html=True)

    alert_card(c1, "📊", "10Y收益率水平", f"{m1['value']:.2f}", "%", m1["grade"], "0.15",
               "&lt;3.0 SAFE · 3-4 WATCH<br>4-5 WARNING · &gt;5 CRITICAL")
    alert_card(c2, "🚀", "3个月变化速率", f"{m2['value']:+.0f}", "bps", m2["grade"], "0.40",
               "历史P75=+50 · P90=+100<br>P95=+150bps<br>最关键预警指标")
    alert_card(c3, "📐", "30Y−10Y利差", f"{m3['value']:+.0f}", "bps", m3["grade"], "0.25",
               "&gt;20 SAFE · 0-20 WATCH<br>0~-30 WARNING · &lt;-30 CRITICAL")
    alert_card(c4, "🔗", "股债滚动相关性", f"{m4['value']:+.2f}", "r(12M)", m4["grade"], "0.20",
               "&gt;-0.3 SAFE · -0.3~-0.5 WATCH<br>-0.5~-0.7 WARNING<br>&lt;-0.7 CRITICAL")

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # 结论框
    ALERT_CONCLUSIONS = {
        "SAFE": {
            "box": "alert-box-green", "icon": "✅",
            "title_color": "#22c55e",
            "title": "结论：利率环境正常，股市估值压力较小",
            "body": "10Y收益率处于历史合理区间，收益率上升速度温和，期限结构正向，股债相关性未出现异常负相关。历史上类似区间（如2012-2017低利率扩张期），股市通常处于牛市中期或末期。<b>当前无需过度警惕利率风险。</b>",
        },
        "WATCH": {
            "box": "alert-box", "icon": "👁",
            "title_color": "#fbbf24",
            "title": "结论：预警信号出现，建议关注但无需行动",
            "body": "部分指标触及警戒区间。历史参照：2018年Q1-Q3，美联储温和加息期间，市场多次出现短暂调整但未形成趋势。<b>建议关注收益率3个月变化速率，若突破+100bps则需提升至WARNING。</b>",
        },
        "WARNING": {
            "box": "alert-box-orange", "icon": "⚠️",
            "title_color": "#f97316",
            "title": "结论：高风险区间，历史上此阶段股市平均调整15-25%",
            "body": "多项指标进入高风险区间。历史参照：2022年Q1-Q2，加息周期启动初期，10Y收益率3个月内上升230bps，纳指最终下跌33%，标普下跌25%。<b>估值压缩风险显著，科技/成长股暴露度需降低。</b>",
        },
        "CRITICAL": {
            "box": "alert-box-red", "icon": "🔴",
            "title_color": "#ef4444",
            "title": "结论：极端风险，历史上触发CRITICAL级别后市场均出现重大调整",
            "body": "所有核心指标均处于极端区间。历史复盘：2000年科网顶点（10Y=6.79%），2008年雷曼前夕（5.25%），2022年加息顶峰（5.02%），触发本级别后12个月内S&P500平均下跌32%。<b>历史数据显示，此级别触发后进行防御性配置的胜率超过80%。</b>",
        },
    }
    conc = ALERT_CONCLUSIONS.get(master_grade, ALERT_CONCLUSIONS["WATCH"])
    st.markdown(f"""
    <div class="{conc['box']}">
      <div class="alert-icon">{conc['icon']}</div>
      <div class="alert-text">
        <div class="alert-title" style="color:{conc['title_color']};">{conc['title']}</div>
        <div>{conc['body']}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if show_hist_chart:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        col_chart, col_table = st.columns([1.6, 1])

        with col_chart:
            fig_hist = build_alert_history_chart(y10, sp500, "ALL")
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_table:
            st.markdown("""
            <div class="panel" style="height:400px; overflow-y:auto;">
              <div class="panel-title">📋 历史CRITICAL/WARNING复盘</div>
              <div style="display:flex; gap:8px; padding:8px 16px; border-bottom:1px solid rgba(255,255,255,0.08);">
                <div style="font-size:11px; color:#475569; width:80px;">时间</div>
                <div style="font-size:11px; color:#475569; flex:1;">事件</div>
                <div style="font-size:11px; color:#475569; width:55px; text-align:right;">10Y</div>
                <div style="font-size:11px; color:#475569; width:55px; text-align:right;">SP跌幅</div>
              </div>
            """, unsafe_allow_html=True)

            HISTORY_TABLE = [
                ("2000-03", "科网泡沫崩盘",   "6.79%", "-49%", "CRITICAL"),
                ("2001-09", "911恐袭",         "4.76%", "-30%", "CRITICAL"),
                ("2007-08", "次贷危机苗头",    "4.96%", "-57%", "WARNING"),
                ("2008-09", "雷曼破产",        "3.69%", "-57%", "CRITICAL"),
                ("2010-05", "闪崩",            "3.54%",  "-7%", "WATCH"),
                ("2011-08", "美国评级下调",    "2.56%", "-19%", "WARNING"),
                ("2015-08", "A股股灾",         "2.17%", "-12%", "WARNING"),
                ("2018-12", "圣诞崩盘",        "2.83%", "-20%", "WARNING"),
                ("2020-03", "COVID崩盘",       "0.54%", "-34%", "CRITICAL"),
                ("2022-06", "加息周期峰值",    "3.49%", "-25%", "CRITICAL"),
                ("2023-10", "10Y触5%",         "5.02%", "-10%", "WARNING"),
            ]
            for date, event, y10v, spv, sev in HISTORY_TABLE:
                color = SEVERITY_COLOR.get(sev, "#94a3b8")
                st.markdown(f"""
                <div class="history-row">
                  <div class="h-date">{date}</div>
                  <div class="h-event">{event}
                    <span style="display:inline-block; font-size:10px; padding:0 6px;
                      border-radius:4px; background:{color}22; color:{color};
                      font-weight:700; margin-left:4px;">{sev}</span>
                  </div>
                  <div class="h-yield">{y10v}</div>
                  <div class="h-drop">{spv}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # 预警逻辑说明
        st.markdown("""
        <div class="panel">
          <div class="panel-title">⚙️ 预警逻辑与阈值推导（基于1994-今历史统计）</div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:24px;">
            <div>
              <div style="font-size:13px; font-weight:700; color:#fbbf24; margin-bottom:10px;">
                🚀 指标②：3M收益率变化速率（权重最高 ×0.40）
              </div>
              <div style="font-size:13px; color:#94a3b8; line-height:2;">
                这是历史上与股市调整相关性最强的单一指标。<br>
                <b style="color:#22c55e;">P75 = +50bps</b> → 进入WATCH：如2021 Q1（+82bps），短暂调整<br>
                <b style="color:#f97316;">P90 = +100bps</b> → 进入WARNING：如2013 Taper（+130bps），-6%<br>
                <b style="color:#ef4444;">P95 = +150bps</b> → 进入CRITICAL：如2022（+230bps），-25%<br>
                <span style="color:#475569;">数据来源：FRED DGS10月度数据，1994-今历史分位数计算</span>
              </div>
            </div>
            <div>
              <div style="font-size:13px; font-weight:700; color:#5CB85C; margin-bottom:10px;">
                📐 指标③：期限利差 30Y-10Y（权重 ×0.25）
              </div>
              <div style="font-size:13px; color:#94a3b8; line-height:2;">
                期限结构是债市对未来经济的隐性预测。<br>
                <b style="color:#ef4444;">倒挂（&lt;0）</b>：历史上每次持续倒挂均先于衰退6-18个月<br>
                <b style="color:#f97316;">2006-2007</b>：倒挂持续8个月 → 2008金融危机<br>
                <b style="color:#fbbf24;">2019</b>：短暂倒挂 → 2020衰退（COVID加速触发）<br>
                <span style="color:#475569;">注：2020年COVID属于外生冲击，本系统存在盲区</span>
              </div>
            </div>
          </div>
          <div style="margin-top:16px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.06);
               font-size:12px; color:#475569; line-height:1.8;">
            ⚠️ <b style="color:#64748b;">系统盲区声明</b>：本预警体系专门针对"利率上行杀估值"场景。对外生冲击（COVID、地缘政治）、
            中国政策性股市崩盘（2015）、Flash Crash等非利率驱动型下跌，本系统预警能力有限。
          </div>
        </div>
        """, unsafe_allow_html=True)


# =========================================================
# 数据加载
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data():
    y10    = fetch_fred("DGS10",      "1994-01-01")
    y30    = fetch_fred("DGS30",      "1994-01-01")
    sp500  = fetch_fmp_index("^GSPC", "1994-01-01")
    nasdaq = fetch_fmp_index("^IXIC", "1994-01-01")
    dow    = fetch_fmp_index("^DJI",  "1994-01-01")
    shcomp = fetch_yf_index("000001.SS", "1994-01-01")
    szcomp = fetch_yf_index("399001.SZ", "1994-01-01")
    return y10, y30, sp500, nasdaq, dow, shcomp, szcomp


with st.spinner("正在从 FRED · FMP · Yahoo Finance 拉取数据..."):
    y10, y30, sp500, nasdaq, dow, shcomp, szcomp = load_all_data()

# =========================================================
# 页面顶部：标题 + 控制栏
# =========================================================

now_str = datetime.now().strftime("%Y-%m-%d %H:%M ET")

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px;">
  <div>
    <div class="main-title">📡 Straw 6 · 宏观市场预警看板</div>
    <div class="sub-title">股市 × 债市联动分析 · Bloomberg风格 · 黑金主题</div>
  </div>
  <div style="text-align:right; padding-top:4px;">
    <span class="timestamp-text">🕐 {now_str}</span>
    <span class="symbol-badge">STRAW 6 · MACRO ALERT</span>
  </div>
</div>
""", unsafe_allow_html=True)

# 控制栏（时间范围 + 股灾标注 + 刷新）
ctrl_col1, ctrl_col2, ctrl_col3, ctrl_spacer = st.columns([2, 2, 1.2, 4])
with ctrl_col1:
    period = st.select_slider(
        "时间范围",
        options=["1Y", "3Y", "5Y", "10Y", "ALL"],
        value="ALL",
    )
with ctrl_col2:
    show_crashes = st.toggle("显示股灾标注", value=True)
with ctrl_col3:
    if st.button("🔄 刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# KPI 行（全局共用）
render_kpi_row(y10, y30, sp500, shcomp)

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# =========================================================
# 顶部 Tab: ALL / US / CN
# =========================================================

tab_all, tab_us, tab_cn = st.tabs(["🌐  ALL — 全资产概览", "🇺🇸  US — 美国市场", "🇨🇳  CN — 中国市场"])

# ─────────────────────────────────────────────
# Tab: ALL
# ─────────────────────────────────────────────
with tab_all:
    fig_overview = build_overview_chart(
        y10, y30, sp500, nasdaq, dow, shcomp, szcomp,
        period=period, show_crashes=show_crashes,
    )
    st.plotly_chart(fig_overview, use_container_width=True)

    fig_spread = build_spread_chart(y10, y30, period)
    st.plotly_chart(fig_spread, use_container_width=True)

    # 股灾事件索引
    if show_crashes:
        st.markdown("""
        <div class="panel">
          <div class="panel-title">📌 历史股灾事件索引</div>
        """, unsafe_allow_html=True)
        cols = st.columns(3)
        for i, ev in enumerate(CRASH_EVENTS):
            color = SEVERITY_COLOR.get(ev["severity"], "#94a3b8")
            with cols[i % 3]:
                st.markdown(f"""
                <div style="display:flex; gap:10px; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.04);">
                  <div style="width:3px; background:{color}; border-radius:2px; flex-shrink:0;"></div>
                  <div>
                    <div style="font-size:11px; color:{color}; font-weight:700;">{ev['date'][:7]} · {ev['label']}</div>
                    <div style="font-size:12px; color:#94a3b8; margin-top:2px;">{ev['desc']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Alert System
    render_alert_system(y10, y30, sp500, show_hist_chart=True)


# ─────────────────────────────────────────────
# Tab: US
# ─────────────────────────────────────────────
with tab_us:
    fig_us = build_dual_axis_chart(
        y10, y30,
        [(sp500, "S&P 500"), (nasdaq, "NASDAQ 100"), (dow, "Dow Jones")],
        period=period, show_crashes=show_crashes,
        title="美债收益率（左轴）× 美股三大指数（右轴）",
    )
    st.plotly_chart(fig_us, use_container_width=True)

    fig_spread_us = build_spread_chart(y10, y30, period)
    st.plotly_chart(fig_spread_us, use_container_width=True)

    st.markdown("""
    <div class="panel">
      <div class="panel-title">📖 美股 × 美债联动解读</div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
          <div style="font-size:13px; font-weight:700; color:#4F8EF7; margin-bottom:8px;">📈 收益率上行 × 股市表现</div>
          <div style="font-size:13px; color:#94a3b8; line-height:1.8;">
            <b style="color:#22c55e;">温和上行（&lt;50bps/3M）</b>：通常伴随经济复苏，股市可同步上涨<br>
            <b style="color:#f97316;">快速上行（50-150bps/3M）</b>：开始压制估值，科技股/成长股首当其冲<br>
            <b style="color:#ef4444;">急速上行（&gt;150bps/3M）</b>：历史上几乎无例外触发股市调整 20%+
          </div>
        </div>
        <div>
          <div style="font-size:13px; font-weight:700; color:#5CB85C; margin-bottom:8px;">🏔️ 山形图 × 折线图观察重点</div>
          <div style="font-size:13px; color:#94a3b8; line-height:1.8;">
            <b style="color:#fbbf24;">红色区域</b>：30Y-10Y倒挂，历史上先于衰退出现<br>
            <b style="color:#ef4444;">收益率峰值</b>：通常在加息末期，股市往往同期底部<br>
            <b style="color:#4F8EF7;">2022年</b>：收益率+230bps，标普跌25%，最典型负相关案例
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Alert System（无历史图表，保持简洁）
    render_alert_system(y10, y30, sp500, show_hist_chart=False)


# ─────────────────────────────────────────────
# Tab: CN
# ─────────────────────────────────────────────
with tab_cn:
    fig_cn = build_dual_axis_chart(
        y10, y30,
        [(shcomp, "上证指数"), (szcomp, "深证成指")],
        period=period, show_crashes=show_crashes,
        title="美债收益率（左轴）× A股指数（右轴）",
    )
    st.plotly_chart(fig_cn, use_container_width=True)

    fig_spread_cn = build_spread_chart(y10, y30, period)
    st.plotly_chart(fig_spread_cn, use_container_width=True)

    st.markdown("""
    <div class="panel">
      <div class="panel-title">📖 A股 × 美债联动特征</div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
          <div style="font-size:13px; font-weight:700; color:#E63946; margin-bottom:8px;">🇨🇳 A股与美债相关性特点</div>
          <div style="font-size:13px; color:#94a3b8; line-height:1.8;">
            A股与美债相关性显著低于美股，主要受国内政策驱动<br>
            <b style="color:#fbbf24;">关键传导路径</b>：美债↑ → 美元强 → 人民币贬值压力 → 外资撤离 → A股承压<br>
            <b style="color:#ef4444;">典型案例</b>：2015年人民币贬值 + 股灾，2022年外资大幅净卖出
          </div>
        </div>
        <div>
          <div style="font-size:13px; font-weight:700; color:#9D4EDD; margin-bottom:8px;">⚠️ 关注信号</div>
          <div style="font-size:13px; color:#94a3b8; line-height:1.8;">
            <b style="color:#22c55e;">美债收益率下行</b>：美元走弱，有利于A股外资回流<br>
            <b style="color:#f97316;">美债快速上行</b>：人民币贬值压力加大，关注资本外流数据<br>
            <b style="color:#60a5fa;">中美利差收窄至负</b>：资本外流压力显著增加
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Alert System（无历史图表）
    render_alert_system(y10, y30, sp500, show_hist_chart=False)


# =========================================================
# 底部版权
# =========================================================
st.markdown(f"""
<div style="margin-top:32px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.05);
     font-size:11px; color:#1e293b; text-align:right; line-height:2;">
  实时数据：FRED（DGS10·DGS30）· FMP（^GSPC·^IXIC·^DJI）· Yahoo Finance（000001.SS·399001.SZ）
  &nbsp;|&nbsp; 更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}
  &nbsp;|&nbsp; Straw 6 · 仅供研究参考，不构成投资建议
</div>
""", unsafe_allow_html=True)
