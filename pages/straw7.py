"""
宏观与跨市场传导确认看板

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
from copy import deepcopy
from html import escape
from io import StringIO
import yfinance as yf
from config.api_keys import FMP_API_KEY, FRED_API_KEY
from components.ui import (load_css, metric_card, model_evidence_panel, panel, render_data_freshness,
                           render_footer, render_header, spacer,
                           two_column_info_panel)
from core.alert_engine import render_alert, render_osci_card
from core.macro_data import load_macro_snapshot, load_macro_stress_snapshot
from core.market_outcome_data import load_sp500_daily
from core.macro_risk import COMPONENTS, compute_macro_metrics
from core.transmission_phase import market_phase_from_series
from core.market_event_replay import build_history_rows, event_validation_scope
from core.score_engine import register_score

# =========================================================
# 页面配置
# =========================================================
st.set_page_config(
    page_title="宏观与跨市场传导确认",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()

# =========================================================
# CSS — 黑金风格
# =========================================================

# =========================================================
# 股灾事件数据库（内置）
# =========================================================
CRASH_EVENTS = [
    {"date": "1997-10-27", "label": "Asian Crisis", "event": "亚洲金融危机", "desc": "亚洲危机冲击美国市场；以10月27日美股大跌为观察锚点。", "kind": "金融传导", "anchor": "代表观察日"},
    {"date": "1998-08-17", "label": "LTCM / Russia", "event": "俄罗斯违约与LTCM危机", "desc": "俄罗斯宣布债务延期偿付，随后与LTCM高杠杆头寸共同冲击全球融资流动性。", "kind": "金融传导", "anchor": "事件日"},
    {"date": "2000-03-24", "label": "Dot-com Peak", "event": "科网泡沫见顶", "desc": "以标普500阶段性高点作为长期估值重估的观察锚点。", "kind": "估值周期", "anchor": "代表观察日"},
    {"date": "2001-09-11", "label": "9/11 Attack", "event": "9·11袭击", "desc": "美国纽约和华盛顿遭遇恐怖袭击，股市暂停交易并于9月17日复市。", "kind": "外生冲击", "anchor": "事件日"},
    {"date": "2002-10-09", "label": "Post 9/11 Bottom", "event": "科网熊市低点", "desc": "以熊市低点作为事后观察锚点；不属于风险发生前的预警事件。", "kind": "周期底部", "anchor": "代表观察日"},
    {"date": "2007-08-09", "label": "Subprime Starts", "event": "次贷风险显性化", "desc": "法国巴黎银行暂停旗下基金赎回，信用与银行间融资压力开始外溢。", "kind": "信用周期", "anchor": "事件日"},
    {"date": "2008-09-15", "label": "Lehman Collapse", "event": "雷曼破产", "desc": "雷曼兄弟在美国申请破产，全球融资链与银行间信用迅速收缩。", "kind": "金融传导", "anchor": "事件日"},
    {"date": "2010-05-06", "label": "Flash Crash", "event": "闪电崩盘", "desc": "美国股市盘中流动性与交易结构异常，指数短时间急跌。", "kind": "市场结构", "anchor": "事件日"},
    {"date": "2011-08-08", "label": "US Downgrade", "event": "美国评级下调", "desc": "美国主权评级于8月5日收盘后下调；以随后首个交易日观察市场反应。", "kind": "政策信用", "anchor": "首个可交易日"},
    {"date": "2015-08-11", "label": "China Crash", "event": "中国市场冲击", "desc": "人民币汇率调整叠加A股波动，冲击全球风险偏好。", "kind": "跨市场传导", "anchor": "代表观察日"},
    {"date": "2018-10-03", "label": "Fed Tightening", "event": "紧缩抛售", "desc": "以10月初长端利率上行和紧缩预期重估为观察锚点。", "kind": "紧缩周期", "anchor": "代表观察日"},
    {"date": "2020-02-20", "label": "COVID Crash", "event": "新冠冲击", "desc": "以美国股市由高位转弱的日期为观察锚点；疫情本身并非单日事件。", "kind": "外生冲击", "anchor": "代表观察日"},
    {"date": "2022-01-05", "label": "Rate Hike Cycle", "event": "快速加息周期", "desc": "以联储会议纪要公布后利率重估的日期为观察锚点；不是首次实际加息日。", "kind": "紧缩周期", "anchor": "代表观察日"},
    {"date": "2023-03-10", "label": "SVB Crisis", "event": "硅谷银行事件", "desc": "美国加州监管机构关闭硅谷银行，冲击区域银行信用传导。", "kind": "银行业压力", "anchor": "事件日"},
]

HISTORY_EVENTS = [(item["date"], item["event"], item["desc"], item["kind"]) for item in CRASH_EVENTS]

SEVERITY_COLOR = {
    "SAFE":     "#22c55e",
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
    "10Y Treasury": "#7EE787",
    "30Y Treasury": "#A5B4FC",
}
STOCK_LINE = {
    "S&P 500":    "#00D9FF",
    "NASDAQ 100": "#FF9F1C",
    "Dow Jones":  "#E879F9",
    "上证指数":   "#FF4D6D",
    "深证成指":   "#A78BFA",
}
SPREAD_NAME = "30Y−10Y 期限利差"
SPREAD_COLOR = "#F8FAFC"

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
    **BOND_LINE,
    **STOCK_LINE,
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
        daily = pd.to_numeric(df["close"], errors="coerce").dropna()
        daily.name = symbol
        return daily
    except Exception as e:
        st.warning(f"FMP {symbol} 获取失败: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_yf_index(ticker: str, start: str = "1994-01-01") -> pd.Series:
    try:
        df = yf.download(ticker, start=start, interval="1d", progress=False, auto_adjust=True)
        if df.empty:
            return pd.Series(dtype=float)
        s = df["Close"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        s.index = pd.to_datetime(s.index).tz_localize(None)
        s.name = ticker
        return pd.to_numeric(s, errors="coerce").dropna().sort_index()
    except Exception as e:
        st.warning(f"yfinance {ticker} 获取失败: {e}")
        return pd.Series(dtype=float)


def fetch_yf_yield(ticker: str, start: str = "1994-01-01") -> pd.Series:
    """Normalize Yahoo Treasury indices to percentage points across feed variants."""
    series = fetch_yf_index(ticker, start)
    if series.empty:
        return series
    return series / 10.0 if float(series.median()) > 15 else series


def fetch_market_index(symbol: str, start: str = "1994-01-01") -> pd.Series:
    """优先使用 FMP；无历史数据时自动切换 Yahoo Finance。"""
    series = fetch_fmp_index(symbol, start)
    if not series.empty:
        return series
    return fetch_yf_index(symbol, start)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred_daily(series_id: str, start: str = "1994-01-01") -> pd.Series:
    """Daily Treasury observations for charts; the scoring engine stays monthly."""
    try:
        response = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv",
            params={"id": series_id, "cosd": start}, timeout=25,
        )
        response.raise_for_status()
        frame = pd.read_csv(StringIO(response.text))
        dates = pd.to_datetime(frame.iloc[:, 0], errors="coerce")
        values = pd.to_numeric(frame[series_id], errors="coerce")
        return pd.Series(values.values, index=dates, name=series_id).dropna().sort_index()
    except Exception:
        return pd.Series(dtype=float)


# =========================================================
# 预警计算
# =========================================================

def compute_alert_metrics(stress: dict[str, pd.Series], sp500_daily: pd.Series) -> dict:
    return compute_macro_metrics(
        stress["y10"], stress["y3m"], stress["sp500"],
        stress["stlfsi"], stress["vix"], sp500_daily,
    )


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
        itemclick="toggle",
        itemdoubleclick="toggleothers",
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
        color = SEVERITY_COLOR.get(ev.get("warning_state", "N/A"), "#94a3b8")
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


def treasury_spread(y10: pd.Series, y30: pd.Series, period: str) -> pd.Series:
    """Return the 30Y-10Y spread in percentage points for a shared axis with yields."""
    if y10.empty or y30.empty:
        return pd.Series(dtype=float)
    common = y10.index.intersection(y30.index)
    if common.empty:
        return pd.Series(dtype=float)
    spread = (y30.loc[common] - y10.loc[common]).dropna()
    spread.name = SPREAD_NAME
    return filter_by_period(spread, period)


def add_spread_background(fig, y10, y30, period):
    """Render a compact, bottom-anchored term-spread band behind the lines."""
    spread = treasury_spread(y10, y30, period)
    if spread.empty:
        return

    spread_bps = spread * 100
    # Magnitude is retained in the bar height while sign is encoded by color.
    # Drawing both signs upward keeps the visual band attached to the time axis;
    # inverted observations remain explicit in red and in the exact hover value.
    display_height = spread_bps.abs()
    colors = [
        "rgba(34,197,94,0.48)" if value >= 0 else "rgba(239,68,68,0.62)"
        for value in spread_bps.values
    ]
    fig.add_trace(go.Bar(
        x=spread.index,
        y=display_height.values,
        base=0,
        customdata=spread_bps.round(1),
        name=SPREAD_NAME,
        marker=dict(color=colors, line=dict(width=0)),
        opacity=0.92,
        showlegend=False,
        hovertemplate="30Y−10Y利差: %{customdata:.1f} bps<extra></extra>",
    ))
    fig.data[-1].update(yaxis="y3")

    max_magnitude = max(1.0, float(display_height.max()))
    fig.update_layout(
        barmode="overlay",
        yaxis3=dict(
            overlaying="y",
            side="right",
            range=[0, max_magnitude * 4.5],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            fixedrange=True,
        ),
    )


def render_series_selector(scope: str, series_names: list[str], compact: bool = False) -> set[str]:
    """Explicit checkbox legend that controls the traces in the adjacent chart."""
    item_keys = [f"straw7_{scope}_series_{idx}" for idx in range(len(series_names))]
    for key in item_keys:
        if key not in st.session_state:
            st.session_state[key] = True

    all_key = f"straw7_{scope}_series_all"
    all_checked = all(bool(st.session_state[key]) for key in item_keys)
    st.session_state[all_key] = all_checked

    def toggle_all_series():
        target = bool(st.session_state[all_key])
        for key in item_keys:
            st.session_state[key] = target

    st.markdown('<div class="series-selector-title">图例与显示开关</div>', unsafe_allow_html=True)
    st.checkbox("全选", key=all_key, on_change=toggle_all_series)
    selected = set()
    for idx, name in enumerate(series_names):
        swatch_col, control_col = st.columns([0.3, 3], gap="small")
        color = BOND_LINE.get(name, STOCK_LINE.get(name, SPREAD_COLOR))
        with swatch_col:
            st.markdown(f'<span class="series-swatch" style="background:{color}"></span>', unsafe_allow_html=True)
        with control_col:
            if st.checkbox(name, key=item_keys[idx]):
                selected.add(name)
    return selected


# =========================================================
# 图表构建
# =========================================================

def build_overview_chart(y10, y30, sp500, nasdaq, dow, shcomp, szcomp, period, show_crashes, visible_series=None):
    """ALL tab: 股票指数左轴；利率右轴并以山形面积作为背景。"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    visible_series = set(visible_series or [])
    add_spread_background(fig, y10, y30, period)

    for series, name in [
        (y10, "10Y Treasury"),
        (y30, "30Y Treasury"),
    ]:
        if name not in visible_series:
            continue
        if series.empty:
            continue
        s = filter_by_period(series, period).dropna()
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            fill="tozeroy",
            fillcolor=BOND_FILL[name],
            line=dict(color=BOND_LINE[name], width=1.6),
            mode="lines",
            hovertemplate=f"{name}: %{{y:.2f}}%<extra></extra>",
        ), secondary_y=True)

    for series, name in [
        (sp500, "S&P 500"),
        (nasdaq, "NASDAQ 100"),
        (dow, "Dow Jones"),
        (shcomp, "上证指数"),
        (szcomp, "深证成指"),
    ]:
        if name not in visible_series:
            continue
        if series.empty:
            continue
        s = filter_by_period(series, period).dropna()
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            line=dict(color=STOCK_LINE[name], width=2.2),
            mode="lines",
            hovertemplate=f"{name}: %{{y:,.1f}} 点<extra></extra>",
        ), secondary_y=False)

    if show_crashes:
        add_crash_annotations(fig, CRASH_EVENTS)
    add_inversion_bands(fig, y10, y30)

    layout = deepcopy(PLOTLY_LAYOUT)
    layout["height"] = 560
    layout["title"] = dict(text="全资产双轴走势 · 股指真实点位 / 利率实值 / 利差柱背景", font=dict(size=14, color="#e2e8f0"), x=0.01)
    layout["showlegend"] = False
    fig.update_layout(**layout)
    fig.update_yaxes(
        title_text="股票指数（实际点位）", secondary_y=False,
        showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False,
        rangemode="tozero",
    )
    fig.update_yaxes(
        title_text="美债收益率 (%)", secondary_y=True,
        showgrid=False, zeroline=True, zerolinecolor="rgba(255,255,255,0.24)",
        rangemode="tozero",
    )
    fig.update_xaxes(showline=True, linecolor="rgba(255,255,255,0.20)", linewidth=1)
    return fig


def build_dual_axis_chart(y10, y30, stock_pairs, period, show_crashes, title, visible_series=None):
    """双Y轴图: 股指折线（左）+ 债券山形（右）。"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    visible_series = set(visible_series or [])
    add_spread_background(fig, y10, y30, period)

    for series, name in [(y10, "10Y Treasury"), (y30, "30Y Treasury")]:
        if name not in visible_series:
            continue
        if series.empty:
            continue
        s = filter_by_period(series, period).dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            fill="tozeroy",
            fillcolor=BOND_FILL[name],
            line=dict(color=BOND_LINE[name], width=1.6),
            mode="lines",
            hovertemplate=f"{name}: %{{y:.2f}}%<extra></extra>",
        ), secondary_y=True)

    for series, name in stock_pairs:
        if name not in visible_series:
            continue
        if series.empty:
            continue
        s = filter_by_period(series, period).dropna()
        color = STOCK_LINE.get(name, "#94a3b8")
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            line=dict(color=color, width=2.3),
            mode="lines",
            hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>",
        ), secondary_y=False)

    if show_crashes:
        add_crash_annotations(fig, CRASH_EVENTS)
    add_inversion_bands(fig, y10, y30)

    layout = deepcopy(PLOTLY_LAYOUT)
    layout["height"] = 500
    layout["title"] = dict(text=title, font=dict(size=14, color="#e2e8f0"), x=0.01)
    layout["showlegend"] = False
    fig.update_layout(**layout)
    fig.update_yaxes(
        title_text="指数点位", secondary_y=False,
        showgrid=True, gridcolor="rgba(255,255,255,0.04)",
        tickfont=dict(size=11), zeroline=False, rangemode="tozero",
    )
    fig.update_yaxes(
        title_text="美债收益率 (%)", secondary_y=True,
        showgrid=False, tickfont=dict(size=11), zeroline=True,
        zerolinecolor="rgba(255,255,255,0.24)", rangemode="tozero",
    )
    fig.update_xaxes(showline=True, linecolor="rgba(255,255,255,0.20)", linewidth=1)
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


def build_alert_history_chart(y10, sp500, period, history_rows, selected_month=None):
    """历史事件图：悬停看详情，点击事件顶部圆点可锁定并联动下方列表。"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    y_min, y_max = 0.0, 8.0
    if not y10.empty:
        s = filter_by_period(y10, period)
        if not s.empty:
            y_min = max(0.0, float(s.min()) - 0.35)
            y_max = float(s.max()) + 0.45
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name="10Y Treasury",
            fill="tozeroy", fillcolor="rgba(92,184,92,0.15)",
            line=dict(color=BOND_LINE["10Y Treasury"], width=1.8), mode="lines",
            hovertemplate="10Y收益率: %{y:.2f}%<extra></extra>",
        ), secondary_y=False)
    if not sp500.empty:
        s = filter_by_period(sp500, period)
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name="S&P 500",
            line=dict(color=STOCK_LINE["S&P 500"], width=2.2), mode="lines",
            hovertemplate="S&P 500: %{y:,.0f}<extra></extra>",
        ), secondary_y=True)

    for row in history_rows:
        month, event = row["month"], row["event"]
        severity = row.get("state", "N/A")
        dt = pd.Timestamp(row["event_date"]) if row.get("event_date") not in (None, "N/A") else pd.Period(month, freq="M").to_timestamp("M")
        color = SEVERITY_COLOR.get(severity, "#94a3b8")
        active = month == selected_month
        hit_y = np.linspace(y_min, y_max, 81)
        marker_colors = ["rgba(255,255,255,0.001)"] * (len(hit_y) - 1) + [color]
        marker_sizes = [14] * (len(hit_y) - 1) + [13 if active else 9]
        fig.add_trace(go.Scatter(
            x=[dt] * len(hit_y), y=hit_y,
            mode="lines+markers",
            line=dict(color=color, width=5.5 if active else 2.0, dash="solid" if active else "dot"),
            marker=dict(size=marker_sizes, color=marker_colors, symbol="circle", line=dict(width=0)),
            customdata=[[month]] * len(hit_y),
            name=event,
            showlegend=False,
            hovertemplate=(
                f"<b>{row.get('event_date', month)} · {event}</b><br>事件当月指标状态: "
                f"{('N/A' if row.get('score') is None else str(row['score']) + '/100')} · {severity}<br>"
                f"10Y: {row.get('y10', 'N/A')}<br>六个月内最大跌幅: {row.get('drawdown', 'N/A')}"
                f"（第{row.get('drawdown_days', 'N/A')}天）<br>首次恢复前跌幅: {row.get('initial_drawdown', 'N/A')}"
                f"（第{row.get('initial_drawdown_days', 'N/A')}天）<extra></extra>"
            ),
        ), secondary_y=False)
        fig.add_annotation(
            x=dt,
            y=0.985,
            yref="paper",
            text=event,
            showarrow=False,
            textangle=-90,
            font=dict(size=10 if active else 9, color="#ffffff" if active else color),
            bgcolor=f"{color}22" if active else "rgba(0,0,0,0)",
            xanchor="left",
            yanchor="top",
        )
        if active:
            fig.add_annotation(
                x=dt, y=y_max, text=f"聚焦：{event}", showarrow=True,
                arrowcolor=color, font=dict(color="#ffffff", size=11),
                bgcolor="rgba(11,17,32,.92)", bordercolor=color,
            )

    layout = deepcopy(PLOTLY_LAYOUT)
    layout["height"] = 470
    layout["title"] = dict(text="10Y国债收益率 × S&P500 · 事件线标记当月指标状态 / 点击锁定", font=dict(size=14, color="#e2e8f0"), x=0.01)
    layout["clickmode"] = "event+select"
    layout["hovermode"] = "closest"
    layout["hoverdistance"] = 36
    layout["hoverlabel"] = dict(
        bgcolor="#111827",
        bordercolor="#94a3b8",
        font=dict(size=16, color="#f8fafc", family="'PingFang SC','Microsoft YaHei',sans-serif"),
        align="left",
    )
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="收益率 (%)", secondary_y=False, showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, range=[y_min, y_max])
    fig.update_yaxes(title_text="S&P 500", secondary_y=True, showgrid=False, zeroline=False)
    return fig


# =========================================================
# 可复用组件
# =========================================================

def render_kpi_row(y10, y30, sp500, shcomp):
    c1, c2, c3, c4, c5 = st.columns(5)

    def kpi_card(col, label, value, sub, color_cls):
        with col:
            st.markdown(metric_card(label, value, color_cls, "", sub, extra_class="metric-card-compact"),
                        unsafe_allow_html=True)

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


def render_alert_system(stress, y30, sp500_daily, market_phase, daily_source, show_hist_chart=True):
    """Render the factor-07 score, evidence and historical validation."""
    y10, sp500 = stress["y10"], stress["sp500"]
    metrics = compute_alert_metrics(stress, sp500_daily)
    composite  = metrics["composite"]
    master_score = composite["score"]
    master_grade = composite["grade"]
    history_rows = build_history_rows(stress, HISTORY_EVENTS, sp500_daily)

    st.markdown(
        '<div class="alert-system-heading">🚨 市场传导确认 · 探索性状态</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(6)
    thresholds = {
        "equity_momentum": "SAFE ≥0%｜WATCH −5%–0｜WARNING −12%–−5%｜CRITICAL <−12%",
        "equity_drawdown": "SAFE ≥−3%｜WATCH −8%–−3%｜WARNING −15%–−8%｜CRITICAL <−15%",
        "volatility": "SAFE ≤20｜WATCH 20–25｜WARNING 25–35｜CRITICAL >35",
        "rate_shock": "SAFE ≤40bp｜WATCH 40–80bp｜WARNING 80–140bp｜CRITICAL >140bp",
        "financial_stress": "SAFE ≤0｜WATCH 0–0.32｜WARNING 0.32–0.83｜CRITICAL >0.83",
        "curve": "SAFE ≥+30bp｜WATCH 0–+30bp｜WARNING −50–0bp｜CRITICAL <−50bp",
    }
    icons = ["📉", "📉", "🌪", "📈", "🌡", "📐"]
    metric_notes = {
        "equity_drawdown": (
            "市场确认项：最新日收盘价相对近六个月最高日收盘价"
            + (f"（数据截至 {pd.to_datetime(sp500_daily.index[-1]):%Y-%m-%d}）" if not sp500_daily.empty else "（日线缺失）")
            + "<br>"
        ),
    }
    for column, icon, (key, definition) in zip(columns, icons, COMPONENTS.items()):
        item = metrics.get(key)
        with column:
            if item is None:
                st.markdown(metric_card(f"{icon} {definition['label']} ×{definition['weight']:.2f}", "N/A", "gray", "", "数据缺失，不按 SAFE 处理"), unsafe_allow_html=True)
            else:
                css = grade_to_css(item["grade"])
                value = (f"{item['value']:.2f}{item['unit']}"
                         if key in {"equity_drawdown", "volatility"}
                         else f"{item['value']:+.2f}{item['unit']}")
                st.markdown(metric_card(
                    f"{icon} {definition['label']} ×{definition['weight']:.2f}", value, css, "",
                    f"当前 {item['grade']}<br>{metric_notes.get(key, '')}{thresholds[key]}",
                ), unsafe_allow_html=True)

    st.markdown(spacer("sm"), unsafe_allow_html=True)

    # 结论框
    ALERT_CONCLUSIONS = {
        "SAFE": {
            "box": "alert-box-green", "icon": "✅",
            "title_color": "#22c55e",
            "title": "结论：尚未观察到多指标压力共振",
            "body": "股市趋势、波动率、利率冲击与市场压力未形成同步恶化。SAFE 只表示本模型当前未捕捉到跨市场确认，<b>不代表外生事件不会发生。</b>",
        },
        "WATCH": {
            "box": "alert-box", "icon": "👁",
            "title_color": "#fbbf24",
            "title": "结论：市场压力初步出现",
            "body": "至少一项市场确认指标越过切点，但尚未形成广泛共振。应观察股票回撤、VIX、利率冲击与市场压力是否继续同时恶化。",
        },
        "WARNING": {
            "box": "alert-box-orange", "icon": "⚠️",
            "title_color": "#f97316",
            "title": "结论：多项市场压力信号正在共振",
            "body": "股票趋势、波动率或利率冲击中的多项信号进入高风险区。下方历史状态按事件月末重建，用于确认市场传导，而非证明事前预测。",
        },
        "CRITICAL": {
            "box": "alert-box-red", "icon": "🔴",
            "title_color": "#ef4444",
            "title": "结论：极端风险，多项宏观压力已形成共振",
            "body": "股票趋势、波动率、利率冲击和金融市场压力出现广泛恶化。下方逐项展示原始值、子评分、权重与贡献；当前应开展情景压力测试，而不是把历史事件视为确定性预测。",
        },
    }
    conc = ALERT_CONCLUSIONS.get(master_grade, ALERT_CONCLUSIONS["WATCH"])
    phase_detail = market_phase["detail"].rstrip("。；; ")
    phase_copy = (
        f'<br><small><b>辅助阶段：{escape(market_phase["label"])}</b> · '
        f'{escape(phase_detail)}。阶段只描述当前表现，不改变四级评级。</small>'
    )
    st.markdown(render_alert(master_grade, conc["title"], conc["body"] + phase_copy), unsafe_allow_html=True)

    if show_hist_chart:
        selected_month = st.session_state.get("straw7_selected_event")
        if selected_month and st.button("清除事件聚焦", key="straw7_clear_event"):
            st.session_state.pop("straw7_selected_event", None)
            st.rerun()

        fig_hist = build_alert_history_chart(y10, sp500, "ALL", history_rows, selected_month)
        chart_event = st.plotly_chart(
            fig_hist,
            use_container_width=True,
            key="straw7_alert_history",
            on_select="rerun",
            selection_mode="points",
        )
        try:
            points = chart_event.selection.points
            custom = points[0].get("customdata") if points else None
            clicked_month = custom[0] if isinstance(custom, (list, tuple)) else custom
            if clicked_month and clicked_month != selected_month:
                st.session_state["straw7_selected_event"] = clicked_month
                st.rerun()
        except (AttributeError, IndexError, TypeError):
            pass

        st.markdown("""
        <div class="panel">
          <div class="panel-title">📋 历史事件复盘 <span class="source-tag-warn static-data-badge">⚠ 静态事件库</span></div>
          <div class="history-help">悬停事件线查看详情；点击事件点可锁定对应事件。评分与颜色表示事件当月的指标状态，不是事前预报。两项跌幅均以观察日前一交易日的标普500日收盘价为基准：第一项取随后六个月内最低日收盘；第二项只取首次收盘恢复到基准之前的最低日收盘。天数从观察日算起；未跌破基准记0%。持续性事件使用明确标注的代表观察日。历史压力序列按当前版本重建，可能包含修订值。</div>
          <div class="history-header">
            <div class="history-header-date">时间</div>
            <div class="history-header-event">事件与计算依据</div>
            <div class="history-header-yield history-cell-yield">10Y</div>
            <div class="history-header-drawdown">六个月内最大跌幅</div>
            <div class="history-header-drawdown">首次恢复前跌幅</div>
            <div class="history-header-score">事件当月指标状态</div>
          </div>
        """, unsafe_allow_html=True)

        for row in history_rows:
            date, event = row["month"], row["event"]
            sev = row.get("state", "N/A")
            color = SEVERITY_COLOR.get(sev, "#94a3b8")
            active_class = " history-row-active" if date == st.session_state.get("straw7_selected_event") else ""
            st.markdown(f"""
            <div class="history-row{active_class}">
              <div class="h-date history-cell-date">{date}</div>
              <div class="h-event"><b>{event}</b>
                <span class="history-state-badge" style="background:{color}22; color:{color};">{sev}</span>
                <small><b>{row.get('kind', '')}</b> · {row.get('summary', row['description'])}</small>
                <small>观察锚点：{row.get('event_date', 'N/A')} · {next((e['anchor'] for e in CRASH_EVENTS if e['date'] == row.get('event_date')), '日期待确认')} · 事前基准：{row.get('baseline_date', 'N/A')} 收盘 {row.get('baseline_close', 'N/A')} 点</small>
                <small>{row.get('scope', '')}</small>
                <small>事件观察月：{row.get('as_of', 'N/A')} · 有效权重覆盖率 {row.get('coverage', 0)}%</small>
                <details class="history-calculation"><summary>查看评分计算与数据追溯</summary><div>{row.get('components', '该事件时点的源数据不足，未生成评分。')}</div></details>
              </div>
              <div class="h-yield history-cell-yield">{row.get('y10', 'N/A')}</div>
              <div class="h-drop history-cell-drawdown">{row.get('drawdown', 'N/A')}<small>{row.get('drawdown_date', 'N/A')} · 第{row.get('drawdown_days', 'N/A')}天</small></div>
              <div class="h-drop history-cell-drawdown">{row.get('initial_drawdown', 'N/A')}<small>{row.get('initial_drawdown_date', 'N/A')} · 第{row.get('initial_drawdown_days', 'N/A')}天</small></div>
              <div class="history-score history-cell-score" style="color:{color};">{'N/A' if row.get('score') is None else f'{row["score"]}/100'} · {sev}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    logic_tab, evidence_tab, source_tab = st.tabs(["检测逻辑", "指标与历史证据", "数据覆盖与来源"])
    with logic_tab:
        st.markdown(panel("⚙️ 确认逻辑、阈值与数据口径", """
          <div class="history-help">本风险因子识别已经传导到市场的压力，不是下跌前的预测模型。标普500三个月收益、VIX、10Y收益率三个月变化和STLFSI由时间序列计算；距近六个月高点的跌幅按最新日收盘价与过去六个月最高日收盘价计算，历史事件评分仅使用截至事件月末的数据；两项事后跌幅另用观察日前一交易日基准，不进入评分。信用利差、实际利率和NFCI由“AI信贷与再融资压力”指标单独监测。综合得分采用“最强主触发 ×0.65 + 加权压力广度 ×0.35”；期限曲线仅作为低权重背景。切点仍是探索性规则，当前状态不代表回调概率。</div>
          <div class="boundary-note">⚠️ <b>边界声明</b>：该指标用于识别已发生的市场压力，无法提前预测9·11、COVID等外生冲击；外生事件应标为模型边界，不将事件月末状态改写成事前预测。</div>
        """), unsafe_allow_html=True)
    with evidence_tab:
        st.markdown(model_evidence_panel(
            sample="19个领先压力信号起点中，5条正例归属2008、2020、2022三轮独立下跌；不是19次独立危机。",
            validation="2017年后21个重叠联合信号月中7个月随后回调，样本表观比例33.3%；不作为预测概率，独立样本置信区间尚不可估。",
            boundary="三轮下跌的07月末确认均晚于标普500自近期高点下跌5%；外生冲击不在预测范围内，市场底部不纳入预警验证。",
            calibration="当前结果足以支持分层设计，不足以确定精确阈值；历史STLFSI4存在回填，尚未完成发布版本的样本外校准。",
        ), unsafe_allow_html=True)
    with source_tab:
        render_data_freshness([
            {"name": "金融市场压力", "source": "FRED · STLFSI4", "updated_at": "每小时缓存", "mode": "live"},
            {"name": "市场波动率", "source": "Yahoo Finance · VIX", "updated_at": "每小时缓存", "mode": "live"},
            {"name": "期限结构", "source": "FRED · DGS3MO / DGS10 / DGS30", "updated_at": "每小时缓存", "mode": "live"},
            {"name": "股票指数", "source": "每日收盘价：FMP · Yahoo Finance 备用", "updated_at": "每小时缓存", "mode": "live"},
            {"name": "历史事件说明", "source": f"静态事件库；事件评分中的距六个月高点及两项事后跌幅均使用{daily_source}", "updated_at": "2026-09", "mode": "static"},
        ])
    return history_rows


# =========================================================
# 数据加载
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data():
    monthly_y10, monthly_y30, _monthly_sp500, _macro_source = load_macro_snapshot()
    stress, stress_source = load_macro_stress_snapshot()
    sp500_daily, daily_source = load_sp500_daily()
    y10 = fetch_fred_daily("DGS10")
    y30 = fetch_fred_daily("DGS30")
    y10 = y10 if not y10.empty else monthly_y10
    y30 = y30 if not y30.empty else monthly_y30
    # Do not silently substitute monthly points for a chart labeled daily.
    sp500 = sp500_daily
    nasdaq = fetch_market_index("^IXIC", "1994-01-01")
    dow    = fetch_market_index("^DJI",  "1994-01-01")
    shcomp = fetch_yf_index("000001.SS", "1994-01-01")
    szcomp = fetch_yf_index("399001.SZ", "1994-01-01")
    return y10, y30, sp500, nasdaq, dow, shcomp, szcomp, stress, stress_source, sp500_daily, daily_source


with st.spinner("正在从 FRED · FMP · Yahoo Finance 拉取数据..."):
    y10, y30, sp500, nasdaq, dow, shcomp, szcomp, stress, stress_source, sp500_daily, daily_source = load_all_data()

# =========================================================
# 页面顶部：标题 + 控制栏
# =========================================================

render_header(
    "📡 宏观与跨市场传导确认",
    "核心监测维度：融资与宏观压力是否已经传导到股票、波动率及跨资产市场",
    symbol="MACRO ALERT",
)

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

st.markdown(spacer("xs"), unsafe_allow_html=True)

# 四级评级与评分是主结果；市场阶段仅作辅助解释。
top_metrics = compute_alert_metrics(stress, sp500_daily)
top_composite = top_metrics["composite"]
if top_composite["score"] is not None:
    register_score("straw7", top_composite["score"])
current_market_phase = market_phase_from_series(stress)
top_state = top_composite["grade"]
top_summary = {
    "SAFE": "结论：当前市场指标尚未形成同步压力。SAFE表示本模型尚未观察到广泛市场传导。",
    "WATCH": "结论：部分市场指标开始恶化，尚未形成广泛共振。",
    "WARNING": "结论：多项市场指标正在共振，市场压力已经明显出现。",
    "CRITICAL": "结论：市场指标强烈共振，风险正在释放。",
}.get(top_state, "结论：有效数据不足，暂不判断市场状态。")
st.markdown(render_osci_card(
    "市场状态 · 宏观与跨市场传导确认",
    top_composite["score"], top_state, top_summary,
    bar_color=SEVERITY_COLOR.get(top_state, "#94a3b8"),
    state_detail=f"有效数据覆盖率 {top_composite['coverage']}% · SAFE表示当前未发现广泛市场传导",
    components_html=(
        "标普500三个月收益 ×0.30 · 距近六个月每日收盘高点 ×0.20 · VIX ×0.20<br>"
        "10Y三个月变化 ×0.15 · STLFSI ×0.10 · 10Y−3M利差 ×0.05<br>"
        "综合评分＝最强主触发 ×0.65＋加权压力广度 ×0.35"
    ),
    score_display="N/A" if top_composite["score"] is None else f"{top_composite['score']:.1f}",
), unsafe_allow_html=True)
# 预警系统统一放在综合评分卡下方，不再在各市场 Tab 中重复展示。
history_rows = render_alert_system(stress, y30, sp500_daily, current_market_phase, daily_source, show_hist_chart=True)
history_rows_by_month = {row["month"]: row for row in history_rows}
for event in CRASH_EVENTS:
    event["warning_state"] = history_rows_by_month.get(event["date"][:7], {}).get("state", "N/A")

# KPI 行（全局共用）
render_kpi_row(y10, y30, sp500, shcomp)

st.markdown(spacer("md"), unsafe_allow_html=True)

# =========================================================
# 顶部 Tab: ALL / US / CN
# =========================================================

tab_all, tab_us, tab_cn = st.tabs(["🌐  ALL — 全资产概览", "🇺🇸  US — 美国市场", "🇨🇳  CN — 中国市场"])

# ─────────────────────────────────────────────
# Tab: ALL
# ─────────────────────────────────────────────
with tab_all:
    all_series = [
        "10Y Treasury", "30Y Treasury",
        "S&P 500", "NASDAQ 100", "Dow Jones", "上证指数", "深证成指",
    ]
    chart_col, legend_col = st.columns([5.2, 1.3])
    with legend_col:
        selected_all = render_series_selector("all", all_series, compact=True)
    with chart_col:
        fig_overview = build_overview_chart(
            y10, y30, sp500, nasdaq, dow, shcomp, szcomp,
            period=period, show_crashes=show_crashes, visible_series=selected_all,
        )
        st.plotly_chart(fig_overview, use_container_width=True, key="straw7_all_overview")
    st.caption("股指采用每日收盘价连续曲线；右侧勾选框控制折线，色块与曲线同色。期限利差背景柱固定显示：绿色为正利差、红色为倒挂，悬停显示 bps。")

    st.caption("事件索引与详细复盘已合并至上方『历史事件复盘』；点击上方事件图中的事件点可聚焦对应行。")

# ─────────────────────────────────────────────
# Tab: US
# ─────────────────────────────────────────────
with tab_us:
    us_series = ["10Y Treasury", "30Y Treasury", "S&P 500", "NASDAQ 100", "Dow Jones"]
    chart_col, legend_col = st.columns([5.2, 1.3])
    with legend_col:
        selected_us = render_series_selector("us", us_series, compact=True)
    with chart_col:
        fig_us = build_dual_axis_chart(
            y10, y30,
            [(sp500, "S&P 500"), (nasdaq, "NASDAQ 100"), (dow, "Dow Jones")],
            period=period, show_crashes=show_crashes,
            title="美股三大指数（左轴）× 美债收益率山形背景（右轴）",
            visible_series=selected_us,
        )
        st.plotly_chart(fig_us, use_container_width=True, key="straw7_us_markets")
    st.caption("股指采用每日收盘价连续曲线；右侧色块与曲线同色。期限利差背景柱固定显示，绿色为正、红色为倒挂。")

    st.markdown(two_column_info_panel("📖 美股 × 美债联动解读", [
        {"title": "📈 收益率上行 × 股市表现", "color_class": "blue", "body": """
            <b class="green">三个月温和上行（&lt;50bp）</b>：通常伴随经济复苏，股市可同步上涨<br>
            <b class="orange">三个月快速上行（50–150bp）</b>：开始压制估值，科技股/成长股首当其冲<br>
            <b class="red">三个月急速上行（&gt;150bp）</b>：需要重点评估估值压缩风险"""},
        {"title": "🏔️ 山形图 × 折线图观察重点", "color_class": "green", "body": """
            <b class="yellow">红色区域</b>：30Y-10Y倒挂，历史上先于衰退出现<br>
            <b class="red">收益率峰值</b>：通常在加息末期，股市往往同期底部<br>
            <b class="blue">2022年</b>：收益率+230bps，标普跌25%，最典型负相关案例"""},
    ]), unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Tab: CN
# ─────────────────────────────────────────────
with tab_cn:
    cn_series = ["10Y Treasury", "30Y Treasury", "上证指数", "深证成指"]
    chart_col, legend_col = st.columns([5.2, 1.3])
    with legend_col:
        selected_cn = render_series_selector("cn", cn_series, compact=True)
    with chart_col:
        fig_cn = build_dual_axis_chart(
            y10, y30,
            [(shcomp, "上证指数"), (szcomp, "深证成指")],
            period=period, show_crashes=show_crashes,
            title="A股指数（左轴）× 美债收益率山形背景（右轴）",
            visible_series=selected_cn,
        )
        st.plotly_chart(fig_cn, use_container_width=True, key="straw7_cn_markets")
    st.caption("股指采用每日收盘价连续曲线；右侧色块与曲线同色。期限利差背景柱固定显示，绿色为正、红色为倒挂。")

    st.markdown(two_column_info_panel("📖 A股 × 美债联动特征", [
        {"title": "🇨🇳 A股与美债相关性特点", "color_class": "red", "body": """
            A股与美债相关性显著低于美股，主要受国内政策驱动<br>
            <b class="yellow">关键传导路径</b>：美债↑ → 美元强 → 人民币贬值压力 → 外资撤离 → A股承压<br>
            <b class="red">典型案例</b>：2015年人民币贬值 + 股灾，2022年外资大幅净卖出"""},
        {"title": "⚠️ 关注信号", "color_class": "purple", "body": """
            <b class="green">美债收益率下行</b>：美元走弱，有利于A股外资回流<br>
            <b class="orange">美债快速上行</b>：人民币贬值压力加大，关注资本外流数据<br>
            <b class="blue">中美利差收窄至负</b>：资本外流压力显著增加"""},
    ]), unsafe_allow_html=True)

# =========================================================
# 底部版权
# =========================================================
render_footer(f"FRED（STLFSI4、DGS3MO、DGS10、DGS30）· FMP（美股）· Yahoo Finance（VIX、A股）· 距六个月高点及两项历史跌幅：{daily_source}")
