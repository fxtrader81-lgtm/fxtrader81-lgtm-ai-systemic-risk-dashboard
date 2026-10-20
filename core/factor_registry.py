"""Dashboard-facing factor data service.

All providers return the same small result schema.  Live failures are represented
as unavailable data instead of silently turning into a safe (zero) score.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from core.market_freshness import download_yahoo

from config.thresholds import STRAW_WEIGHTS
from core.credit_risk import compute_credit_metrics
from core.macro_data import load_credit_stress_snapshot, load_macro_stress_snapshot
from core.macro_risk import compute_macro_metrics
from core.straw5_engine import load_straw5_analysis
from core.transmission_phase import market_phase, system_phase
from core.capability_gap import ensure_full_baseline as current_capability_snapshot
from core.model_prices import load_prices
from core.deployment_interest import load_deployment
from core.ecology_downloads import load_ecology
from core.aof import load_aof
from core.reit_pressure import load_reit
from core.liquid_signal import load_liquid
from core.power_infrastructure import load_power


@dataclass
class FactorResult:
    id: str
    name: str
    score: float | None
    state: str
    available: bool
    coverage: float
    detail: str
    source: str


FACTOR_NAMES = {
    "straw1": "资本开支偏离",
    "straw2": "开源商业化压缩",
    "straw3": "数据中心资产减值",
    "straw4": "AI能源约束",
    "straw5": "AI融资结构脆弱性",
    "straw6": "AI信贷与再融资压力",
    "straw7": "宏观与跨市场传导确认",
}


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def state_for(score: float | None) -> str:
    if score is None:
        return "N/A"
    if score < 25:
        return "SAFE"
    if score < 50:
        return "WATCH"
    if score < 75:
        return "WARNING"
    return "CRITICAL"


def straw1_score(diff_ratio: float) -> float:
    """Map CapEx minus revenue growth to the shared 0–100 scale."""
    return round(clamp(25 + 250 * diff_ratio), 1)


def _result(straw_id: str, score: float | None, coverage: float, detail: str, source: str):
    score = None if score is None else round(clamp(float(score)), 1)
    return asdict(FactorResult(
        id=straw_id,
        name=FACTOR_NAMES[straw_id],
        score=score,
        state=state_for(score),
        available=score is not None,
        coverage=round(clamp(coverage, 0, 1) * 100, 0),
        detail=detail,
        source=source,
    ))


def _unavailable(straw_id: str, reason: str):
    return _result(straw_id, None, 0, reason, "暂无可用数据源")


def _statement_row(frame: pd.DataFrame, names: list[str]):
    if frame is None or frame.empty:
        return None
    for name in names:
        if name in frame.index:
            return frame.loc[name].dropna()
    return None


def _straw1() -> dict:
    ticker = yf.Ticker("NVDA")
    revenue = _statement_row(ticker.financials, ["Total Revenue", "Operating Revenue"])
    capex = _statement_row(ticker.cashflow, ["Capital Expenditure", "Capital Expenditure Reported"])
    if revenue is None or capex is None:
        return _unavailable("straw1", "收入或资本开支字段缺失")
    common = sorted(set(revenue.index) & set(capex.index), reverse=True)
    if len(common) < 2:
        return _unavailable("straw1", "共同年度少于两期")
    now, prev = common[0], common[1]
    prev_rev, prev_capex = float(revenue.loc[prev]), abs(float(capex.loc[prev]))
    if not prev_rev or not prev_capex:
        return _unavailable("straw1", "上期基数为零")
    rev_growth = (float(revenue.loc[now]) - prev_rev) / prev_rev
    capex_growth = (abs(float(capex.loc[now])) - prev_capex) / prev_capex
    diff = capex_growth - rev_growth
    return _result(
        "straw1", straw1_score(diff), 1,
        f"NVDA 资本开支增速较收入增速高 {diff * 100:+.1f} 个百分点",
        "Yahoo Finance · 年度财务报表",
    )


def _get_json(url: str):
    response = requests.get(url, timeout=12, headers={"User-Agent": "AI-risk-dashboard/1.0"})
    response.raise_for_status()
    return response.json()


def _straw2() -> dict:
    # All four factor-02 component inputs are shared with the detail page.
    capability = current_capability_snapshot()
    components = [(0.20, capability["metrics"]["score"], "能力基准")]
    sources = [f"LiveBench {capability['release']} · 能力相对差距"]

    try:
        prices = load_prices(capability)
        if prices["available"]:
            components.append((0.35, prices["metrics"]["score"], "价格"))
            sources.append("OpenRouter · 同本期六型号输入价")
    except Exception:
        pass

    try:
        deployment = load_deployment()
        if deployment["available"]:
            components.append((0.30, deployment["metrics"]["score"], "部署工具关注度"))
            sources.append("GitHub · 固定三仓库累计stars代理")
    except Exception:
        pass

    try:
        ecology = load_ecology(capability)
        if ecology["available"]:
            components.append((0.15, ecology["metrics"]["score"], "入选模型下载热度"))
            sources.append("Hugging Face · 本期三模型近30天下载")
    except Exception:
        pass

    weight = sum(item[0] for item in components)
    if weight < 0.5:
        return _unavailable("straw2", "实时覆盖不足 50%")
    score = sum(w * value for w, value, _ in components) / weight
    return _result("straw2", score, weight, f"{len(components)}/4 个分项有效，按可用权重重算", " · ".join(sources))


def _history(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    data = download_yahoo(tickers, period=period, interval="1d", progress=False, auto_adjust=True)
    if data.empty:
        return pd.DataFrame()
    close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]].rename(columns={"Close": tickers[0]})
    return close.dropna(how="all")


def _price_position(series: pd.Series) -> float | None:
    series = series.dropna()
    if series.empty or series.max() == series.min():
        return None
    return float((series.iloc[-1] - series.min()) / (series.max() - series.min()) * 100)


def _straw3() -> dict:
    reit = load_reit()
    liquid = load_liquid()
    power = load_power()
    aof = load_aof()
    aof_score = aof["metrics"]["score"]
    components = [(0.25, aof_score)]
    if reit["available"]:
        components.append((0.35, reit["metrics"]["score"]))
    if liquid["available"]:
        components.append((0.25, liquid["metrics"]["score"]))
    if power["available"]:
        components.append((0.15, power["metrics"]["score"]))
    weight = sum(w for w, _ in components)
    if weight < 0.6:
        return _unavailable("straw3", "资产组覆盖不足 60%")
    score = sum(w * value for w, value in components) / weight
    return _result("straw3", score, weight,
                   f"AOF参考情景{aof['metrics']['aof']:g}倍/{aof_score}分（非已确认减值）；REIT{'共用详情原公式' if reit['available'] else '数据不完整，不计分'}；液冷{'共用详情原公式（相关企业代理）' if liquid['available'] else '数据不完整，不计分'}；电力{'共用详情原公式（相关企业代理）' if power['available'] else '数据不完整，不计分'}",
                   "NVIDIA GB200 NVL72参考规格 / 项目25kW情景 · Yahoo Finance")


def _straw4() -> dict:
    queue_s = clamp((43 - 12) / 36 * 100)
    transformer_s = clamp((36 - 12) / 36 * 100)
    reserve_s = clamp((20 - np.mean([16.5, 12.8])) / 12 * 100)
    infra = queue_s * 0.45 + transformer_s * 0.30 + reserve_s * 0.25
    ppp_s = clamp((0.6 - 0.028 / 0.079) / 0.4 * 100)
    cost = ppp_s * 0.55 + clamp((15 - 10) / 25 * 100) * 0.45
    efficiency = clamp((2.0 - 1.75) / 0.9 * 100)
    components = [(0.40, infra), (0.25, cost), (0.20, efficiency)]
    sources = "FERC/NERC/EIA 静态基准 · NVIDIA规格"
    try:
        close = _history(["CEG", "VST", "NEE", "XLU", "ICLN"])
        positions = [_price_position(close[t]) for t in close.columns]
        positions = [p for p in positions if p is not None]
        if positions:
            market = float(np.mean([75 if p > 80 else 55 if p > 60 else 35 if p > 40 else 20 for p in positions]))
            components.append((0.15, market))
            sources += " · Yahoo Finance"
    except Exception:
        pass
    weight = sum(w for w, _ in components)
    score = sum(w * value for w, value in components) / weight
    return _result("straw4", score, weight, "电网、成本、GPU效率与能源市场信号", sources)


def _single_close(ticker: str, period: str = "2y", interval: str = "1mo") -> pd.Series:
    """Return one numeric close series across yfinance's flat/MultiIndex variants."""
    frame = download_yahoo(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if not isinstance(frame, pd.DataFrame) or frame.empty or "Close" not in frame.columns:
        return pd.Series(dtype=float)
    close = frame["Close"]
    if isinstance(close, pd.DataFrame):
        if close.empty:
            return pd.Series(dtype=float)
        close = close.iloc[:, 0]
    return pd.to_numeric(close, errors="coerce").dropna()


def _yield_series(ticker: str) -> pd.Series:
    series = _single_close(ticker)
    if series.empty:
        return series
    return series / 10.0 if float(series.median()) > 15 else series


def _straw6() -> dict:
    series, source = load_credit_stress_snapshot()
    metrics = compute_credit_metrics(
        series["hy_oas"], series["real_yield"], series["nfci"],
        baa_spread=series["baa10y"],
    )
    composite = metrics["composite"]
    if composite["score"] is None:
        return _unavailable("straw6", f"信贷压力序列覆盖不足（{composite['coverage']}%）")
    return _result(
        "straw6", composite["score"], composite["coverage"] / 100,
        "HY信用利差、10Y实际利率与NFCI；AI交易定价待可比数据齐备后计分", source,
    )


def _straw7() -> dict:
    series, source = load_macro_stress_snapshot()
    metrics = compute_macro_metrics(
        series["y10"], series["y3m"], series["sp500"],
        series["stlfsi"], series["vix"],
    )
    composite = metrics["composite"]
    if composite["score"] is None:
        return _unavailable("straw7", f"跨市场序列覆盖不足（{composite['coverage']}%）")
    return _result(
        "straw7", composite["score"], composite["coverage"] / 100,
        "市场传导确认强度：股票动量与回撤、VIX、利率冲击、市场压力与期限曲线；非下跌预测概率", source,
    )


PROVIDERS: dict[str, Callable[[], dict]] = {
    "straw1": _straw1,
    "straw2": _straw2,
    "straw3": _straw3,
    "straw4": _straw4,
    "straw6": _straw6,
    "straw7": _straw7,
}


@st.cache_data(ttl=3600, show_spinner=False)
def load_factor_results() -> dict[str, dict]:
    """Load providers; capability refresh explicitly invalidates this result cache."""
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as pool:
        future_map = {pool.submit(provider): straw_id for straw_id, provider in PROVIDERS.items()}
        for future in as_completed(future_map):
            straw_id = future_map[future]
            try:
                results[straw_id] = future.result()
            except Exception as exc:
                results[straw_id] = _unavailable(straw_id, f"数据源异常：{type(exc).__name__}")
    try:
        dcoi = results.get("straw3", {}).get("score") if results.get("straw3", {}).get("available") else None
        analysis = load_straw5_analysis(dcoi)
        results["straw5"] = _result(
            "straw5",
            analysis["score"],
            analysis["coverage"] / 100,
            f"期限错配、资本闭环、证券化传染与DCOI联动 · {analysis['confidence']}",
            "SEC季度披露 · 数据中心资产减值指数",
        )
    except Exception as exc:
        results["straw5"] = _unavailable("straw5", f"数据源异常：{type(exc).__name__}")
    # Keep presentation names in this cached result tied to the current
    # registry revision; changing the function body also invalidates older
    # Streamlit cache entries after a deployment.
    for straw_id, item in results.items():
        item["name"] = FACTOR_NAMES[straw_id]
    return results


def aggregate_factor_results(results: dict[str, dict], minimum_coverage: float = 0.70,
                             market_phase_result: dict | None = None) -> dict:
    """Return structural score plus the credit/market transmission phase."""
    active = dict(STRAW_WEIGHTS)
    active_total = sum(active.values())
    available_weight = sum(weight for key, weight in active.items() if results.get(key, {}).get("available"))
    coverage = available_weight / active_total if active_total else 0
    if coverage < minimum_coverage or available_weight == 0:
        base = {"score": None, "state": "N/A", "coverage": round(coverage * 100), "available": False}
    else:
        weighted = sum(results[key]["score"] * weight for key, weight in active.items() if results.get(key, {}).get("available"))
        score = round(weighted / available_weight, 1)
        base = {"score": score, "state": state_for(score), "coverage": round(coverage * 100), "available": True}

    rank = {"N/A": -1, "SAFE": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}
    s5 = results.get("straw5", {}).get("state", "N/A")
    s6 = results.get("straw6", {}).get("state", "N/A")
    s7 = results.get("straw7", {}).get("state", "N/A")
    cascade = rank[s5] >= 2 and rank[s6] >= 2 and rank[s7] >= 1
    critical = cascade and (rank[s5] >= 3 or rank[s6] >= 3) and rank[s7] >= 2
    observed_phase = system_phase(s5, s6, market_phase_result or market_phase(s7))
    return {**base, "phase": observed_phase["label"], "phase_key": observed_phase["key"],
            "phase_nodes": observed_phase["nodes"], "cascade": cascade,
            "critical_cascade": critical, "credit_state": s6, "market_state": s7}
