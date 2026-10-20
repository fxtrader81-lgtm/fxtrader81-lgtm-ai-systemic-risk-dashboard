"""EQIX/DLR price-and-annual-revenue proxy; original detail scoring retained."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import streamlit as st
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / ".local" / "reit_pressure_history.sqlite3"
TICKERS = ("EQIX", "DLR")
VERSION = "reit-detail-original-complete-v1"
RULE = {
    "version": VERSION, "weight": .35,
    "price_score": "drawdown <5/15/25/40/otherwise -> 10/35/60/80/95",
    "growth_score": "annual growth >12/>6/>0/otherwise -> 10/30/55/80",
    "formula": "drawdown=(year_high-latest_close)/year_high*100; growth=(latest_annual_revenue/prior_annual_revenue-1)*100; company=.65*price_score+.35*growth_score; score=round(mean(EQIX,DLR)); contribution=score*.35",
    "states": "unrounded company mean <25/<50/<70/otherwise -> SAFE/WATCH/WARNING/CRITICAL",
    "missing": "Both fixed companies must have valid prices, dates and two comparable annual revenue values; otherwise no REIT score. No zero/50 imputation or averaging one company.",
}
LEGACY_RULES = {
    "detail": "两家公司价格分×65%＋年度营收增长分×35%，公司分平均后round；原营收缺失给50、缺一家按剩余公司、全部缺失给50。这些缺失处理现已停用。",
    "overview": "原总览只计算100－一年调整后收盘区间位置，不含营收增长；改为共用详情原算法，存在方法断点，不将分差解释为市场变化。",
    "card": "原卡片缺失一家时将其跌幅当0且仍除以2，现不再生成这种平均值。",
    "history_note": "旧方法资料不是旧实测成绩；此前未保存的价格、营收和分数不回填。",
}
LIMITATION = "股价回撤与年度营收只是REIT市场和经营压力代理，不是NAV折价、底层数据中心资产减值比例或会计减值证据；股价还可能受利率和整体市场影响。"


def number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def score_company(drawdown, growth):
    if not number(drawdown) or not 0 <= drawdown <= 100 or not number(growth):
        raise ValueError("REIT跌幅或年度增长率无效，不能填默认分")
    ps = 10 if drawdown < 5 else 35 if drawdown < 15 else 60 if drawdown < 25 else 80 if drawdown < 40 else 95
    gs = 10 if growth > 12 else 30 if growth > 6 else 55 if growth > 0 else 80
    return {"price_score": ps, "growth_score": gs, "company_score": ps*.65+gs*.35}


def validate_row(row):
    errors = []
    for key in ("current_price", "week52_high", "week52_low"):
        if not number(row.get(key)) or row[key] <= 0:
            errors.append(key+"缺失或无效")
    if not errors and not row["week52_low"] <= row["current_price"] <= row["week52_high"]:
        errors.append("当前价不在同口径价格区间内")
    for key in ("price_date", "window_start", "window_end", "high_date", "low_date"):
        try: datetime.strptime(row.get(key, ""), "%Y-%m-%d")
        except (ValueError, TypeError): errors.append(key+"缺失或无效")
    periods = row.get("annual_revenue", [])
    if len(periods) != 2:
        errors.append("最近两个年度营收不完整")
    else:
        try:
            dates = [datetime.strptime(p["period_end"], "%Y-%m-%d") for p in periods]
            if not 330 <= (dates[0]-dates[1]).days <= 400:
                errors.append("财务期间不是相邻年度")
        except (ValueError, TypeError, KeyError): errors.append("财务日期缺失或无效")
        values = [p.get("revenue") for p in periods]
        if any(not number(v) or v < 0 for v in values) or (number(values[1]) and values[1] == 0):
            errors.append("年度营收缺失、无效或前期为零")
    if not errors:
        if not row["window_start"] <= row["price_date"] == row["window_end"]:
            errors.append("价格日期与窗口不一致")
        if any(not row["window_start"] <= row[k] <= row["window_end"] for k in ("high_date", "low_date")):
            errors.append("高低点日期不在窗口内")
    return errors


def make_snapshot(rows, checked_at):
    if len(rows) != 2 or {r["ticker"] for r in rows} != set(TICKERS):
        raise ValueError("REIT必须固定EQIX和DLR，不以其他公司或单公司替代")
    validated = []
    for original in sorted(rows, key=lambda r: TICKERS.index(r["ticker"])):
        row = deepcopy(original)
        errors = validate_row(row)
        if row.get("reason"): errors.insert(0, row["reason"])
        row["reason"] = "；".join(dict.fromkeys(errors)) or None
        row["metrics"] = None
        if not errors:
            growth = (row["annual_revenue"][0]["revenue"]/row["annual_revenue"][1]["revenue"]-1)*100
            drawdown = (row["week52_high"]-row["current_price"])/row["week52_high"]*100
            row["metrics"] = dict(score_company(drawdown,growth), from_high_pct=drawdown, rev_growth=growth)
        validated.append(row)
    coverage = sum(r["metrics"] is not None for r in validated)
    metrics = None
    if coverage == 2:
        mean = sum(r["metrics"]["company_score"] for r in validated)/2
        score = round(mean)
        state, color, arrow = (("SAFE","green","↗") if mean <25 else ("WATCH","yellow","→") if mean <50
                               else ("WARNING","orange","↘") if mean <70 else ("CRITICAL","red","↓"))
        metrics = {"unrounded_score": mean, "score": score, "state": state, "color": color, "arrow": arrow,
                   "contribution": score*.35, "mean_drawdown": sum(r["metrics"]["from_high_pct"] for r in validated)/2}
    return {"version": VERSION, "checked_at": checked_at, "rows": validated, "coverage": coverage,
            "available": coverage == 2, "metrics": metrics, "rule": deepcopy(RULE), "limitation": LIMITATION}


def _fetch(ticker):
    row = {"ticker": ticker, "source_url": f"https://finance.yahoo.com/quote/{ticker}/history/",
           "financial_source_url": f"https://finance.yahoo.com/quote/{ticker}/financials/",
           "annual_revenue": [], "raw": {}, "reason": None,
           "price_basis": "USD，auto_adjust=True；最新调整后日收盘价与一年窗口调整后日内High/Low",
           "financial_basis": "年度营收，来源报表原币；不是季度或TTM"}
    errors = []
    t = yf.Ticker(ticker)
    try:
        frame = t.history(period="1y", auto_adjust=True, timeout=12)
        if frame is None or frame.empty or not {"Close", "High", "Low"}.issubset(frame.columns):
            raise ValueError("价格序列不完整")
        frame = frame.sort_index()
        if frame.index.has_duplicates: raise ValueError("价格日期重复")
        frame = frame.loc[frame["Close"].notna()]
        if frame.empty or frame[["Close","High","Low"]].isna().any().any():
            raise ValueError("价格字段缺失")
        raw = [{"date": date.date().isoformat(), **{k:float(r[k]) for k in ("Close","High","Low")}}
               for date,r in frame.iterrows()]
        if any(not number(v) or v<=0 for r in raw for k,v in r.items() if k!="date"):
            raise ValueError("价格字段无效")
        row["raw"]["adjusted_daily_prices"] = raw
        row.update(current_price=float(frame["Close"].iloc[-1]), week52_high=float(frame["High"].max()),
                   week52_low=float(frame["Low"].min()), price_date=raw[-1]["date"], window_start=raw[0]["date"],
                   window_end=raw[-1]["date"], high_date=frame["High"].idxmax().date().isoformat(),
                   low_date=frame["Low"].idxmin().date().isoformat(), observed_sessions=len(raw))
    except Exception as exc: errors.append(f"价格读取失败（{type(exc).__name__}）")
    try:
        financials = t.financials
        if financials is None or financials.empty or financials.columns.has_duplicates:
            raise ValueError("年度报表缺失或期间重复")
        key = next((k for k in ("Total Revenue","Operating Revenue") if k in financials.index),None)
        if key is None: raise ValueError("营收字段缺失")
        revenue = financials.loc[key].sort_index(ascending=False)
        # Select the latest two report columns BEFORE handling missing values.
        # Never silently skip a missing recent year to substitute an older pair.
        periods = [{"period_end": date.date().isoformat(), "revenue": float(value) if number(value) else None}
                   for date,value in revenue.items()]
        row["raw"]["annual_revenue"] = periods
        row["raw"]["revenue_field"] = key
        row["annual_revenue"] = periods[:2]
    except Exception as exc: errors.append(f"年度营收读取失败（{type(exc).__name__}）")
    row["reason"] = "；".join(errors) or None
    return row


def archive(snapshot, path=None):
    path = Path(path or STORE)
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = {k:v for k,v in snapshot.items() if k != "checked_at"}
    key = hashlib.sha256(json.dumps(identity,sort_keys=True,allow_nan=False).encode()).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, checked_at TEXT NOT NULL, payload TEXT NOT NULL)")
        db.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?)", (key,snapshot["checked_at"],json.dumps(snapshot,ensure_ascii=False,sort_keys=True,allow_nan=False)))


def history(path=None):
    path = Path(path or STORE)
    if not path.exists(): return []
    with sqlite3.connect(path) as db:
        return [json.loads(r[0]) for r in db.execute("SELECT payload FROM snapshots ORDER BY checked_at DESC,rowid DESC")]


@st.cache_data(ttl=3600)
def get_reit_snapshot():
    with ThreadPoolExecutor(max_workers=2) as pool: rows = list(pool.map(_fetch,TICKERS))
    return make_snapshot(rows,datetime.now(timezone.utc).isoformat())


def load_reit():
    snapshot = get_reit_snapshot()
    archive(snapshot)
    return snapshot
