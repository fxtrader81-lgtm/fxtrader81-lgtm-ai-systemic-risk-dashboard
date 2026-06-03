# =========================================================
# core/data_loader.py
# 所有数据获取统一在此，各 Straw 禁止自己调用外部 API
# =========================================================

import requests
import streamlit as st
from config.api_keys import FMP_API_KEY, FMP_BASE, FRED_API_KEY, FRED_BASE


# ─── 基础 HTTP 工具 ───────────────────────────────────────

def _get(url: str, params: dict = None) -> list | dict:
    """通用 GET，失败返回空列表，不抛异常。"""
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return []
        return r.json()
    except Exception:
        return []


def safe_float(obj: dict, key: str) -> float:
    """安全取 float，缺失/异常返回 0.0。"""
    try:
        return float(obj.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


# ─── FMP 数据源 ───────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fmp_income(symbol: str, limit: int = 5) -> list:
    """FMP 损益表（年度）。"""
    return _get(f"{FMP_BASE}/income-statement",
                params={"symbol": symbol, "limit": limit, "apikey": FMP_API_KEY})


@st.cache_data(ttl=3600, show_spinner=False)
def fmp_cashflow(symbol: str, limit: int = 5) -> list:
    """FMP 现金流量表（年度）。"""
    return _get(f"{FMP_BASE}/cash-flow-statement",
                params={"symbol": symbol, "limit": limit, "apikey": FMP_API_KEY})


@st.cache_data(ttl=3600, show_spinner=False)
def fmp_index_quote(index_symbol: str) -> dict:
    """FMP 单个指数报价（S&P500=^GSPC 等）。"""
    data = _get(f"{FMP_BASE}/quote",
                params={"symbol": index_symbol, "apikey": FMP_API_KEY})
    return data[0] if isinstance(data, list) and data else {}


@st.cache_data(ttl=300, show_spinner=False)
def fmp_historical(symbol: str, from_date: str, to_date: str) -> list:
    """FMP 历史价格。"""
    return _get(f"{FMP_BASE}/historical-price-eod/full",
                params={"symbol": symbol, "from": from_date,
                        "to": to_date, "apikey": FMP_API_KEY})


# ─── FRED 数据源 ──────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fred_series(series_id: str, observation_start: str = "2020-01-01") -> list:
    """
    FRED 时间序列。
    返回 list of {"date": "...", "value": "..."}
    """
    data = _get(FRED_BASE, params={
        "series_id":         series_id,
        "api_key":           FRED_API_KEY,
        "file_type":         "json",
        "observation_start": observation_start,
        "sort_order":        "desc",
        "limit":             100,
    })
    if isinstance(data, dict):
        return data.get("observations", [])
    return []


@st.cache_data(ttl=3600, show_spinner=False)
def fred_latest_value(series_id: str) -> float | None:
    """FRED 最新有效数值（跳过缺失 '.'）。"""
    obs = fred_series(series_id)
    for o in obs:
        try:
            val = float(o["value"])
            return val
        except (KeyError, ValueError):
            continue
    return None


# ─── yfinance 数据源 ──────────────────────────────────────
# 注：yfinance 不走 FMP/FRED，直接用 yf.download。
# 各 Straw 可以直接 import yfinance as yf 使用，
# 或者把常用 ticker 的 wrapper 写在这里。

@st.cache_data(ttl=3600, show_spinner=False)
def yf_history(ticker: str, period: str = "1y", interval: str = "1d"):
    """yfinance 历史价格 DataFrame。"""
    import yfinance as yf
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        return df
    except Exception:
        return None


# ─── GitHub / HuggingFace / OpenRouter ───────────────────
# （Straw2 专用，放在这里统一管理）

@st.cache_data(ttl=3600, show_spinner=False)
def github_stars(owner: str, repo: str) -> int | None:
    """GitHub 仓库 star 数。"""
    data = _get(f"https://api.github.com/repos/{owner}/{repo}")
    if isinstance(data, dict):
        return data.get("stargazers_count")
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def huggingface_downloads(model_id: str) -> int | None:
    """HuggingFace 模型下载量。"""
    data = _get(f"https://huggingface.co/api/models/{model_id}")
    if isinstance(data, dict):
        return data.get("downloads")
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def openrouter_models() -> list:
    """OpenRouter 所有模型价格列表。"""
    data = _get("https://openrouter.ai/api/v1/models")
    if isinstance(data, dict):
        return data.get("data", [])
    return []
