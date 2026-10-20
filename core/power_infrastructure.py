"""Original NEE/SO detail scoring; utility proxy, not physical grid capacity."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from core.reit_pressure import (_fetch as fetch_financial_row, validate_row, number,
                                archive as archive_snapshot, history as read_history)

STORE = Path(__file__).resolve().parents[1] / ".local" / "power_infrastructure_history.sqlite3"
TICKERS = ("NEE", "SO")
VERSION = "power-detail-original-complete-v1"
RULE = {
    "version": VERSION, "weight": .15,
    "growth_score": "annual growth <3/<8/<15/otherwise -> 15/35/60/80",
    "price_score": "price position >75/>50/>25/otherwise -> 70/50/30/15",
    "formula": "position=(latest_close-year_low)/(year_high-year_low)*100; growth=(latest_annual_revenue/prior_annual_revenue-1)*100; company=.60*growth_score+.40*price_score; score=round(mean(NEE,SO)); contribution=score*.15",
    "states": "unrounded company mean <25/<45/<65/otherwise -> SAFE/WATCH/WARNING/CRITICAL",
    "missing": "Both fixed companies require valid prices, nonconstant range and two adjacent annual revenue values; no 0/50 imputation or averaging one company.",
}
LIMITATION = "使用NEE与SO公司总营收和股价作为电力相关企业代理，不是数据中心供电单独收入、实际用电量、电网剩余容量、缺电程度或接电排队时间。营收增长和股价上涨不能直接证明电力短缺、功率密度危机或数据中心资产减值。"
BUSINESS_SOURCES = {
    "NEE": "https://www.investor.nexteraenergy.com/financial-policy",
    "SO": "https://www.southerncompany.com/about/our-business/our-companies.html",
}
LEGACY_RULES = {
    "detail": "原详情公司分＝年度总营收增长映射分×60%＋股价位置映射分×40%，两公司平均取整；保留公式及15%权重。原营收缺失给50、无效价格区间默认位置50%、缺一家按剩余公司计分、整项缺失返回30分，现停用这些缺失处理。",
    "overview": "原总览只计算两家公司一年调整后收盘区间位置平均，减15后下限0，不含营收；改为共用详情原公式，存在方法断点，不能将总览新旧分差解释为市场变化。",
    "interpretation": "原“电力需求旺盛是功率密度危机的物理证据”不由公司总营收和股价直接支持，现仅作相关企业代理。",
    "history_note": "这些是旧方法资料，不是旧实测成绩；此前未保存的原始数据和分数不回填。",
}


def score_company(growth, position):
    if not number(growth) or not number(position) or not 0 <= position <= 100:
        raise ValueError("年度增长率或股价位置无效，不能填默认分")
    gs = 15 if growth < 3 else 35 if growth < 8 else 60 if growth < 15 else 80
    ps = 70 if position > 75 else 50 if position > 50 else 30 if position > 25 else 15
    return {"growth_score":gs, "price_score":ps, "company_score":gs*.6+ps*.4}


def make_snapshot(rows, checked_at):
    if len(rows) != 2 or {r["ticker"] for r in rows} != set(TICKERS):
        raise ValueError("电力相关企业必须固定NEE和SO，不以单公司或其他公司代替")
    validated = []
    for original in sorted(rows,key=lambda r:TICKERS.index(r["ticker"])):
        row = deepcopy(original)
        errors = validate_row(row)
        if row.get("reason"): errors.insert(0,row["reason"])
        if number(row.get("week52_high")) and number(row.get("week52_low")) and row["week52_high"] <= row["week52_low"]:
            errors.append("一年价格区间无效，不能默认位置50%")
        row["reason"] = "；".join(dict.fromkeys(errors)) or None
        row["metrics"] = None
        row["business_source_url"] = BUSINESS_SOURCES[row["ticker"]]
        if not errors:
            growth = (row["annual_revenue"][0]["revenue"]/row["annual_revenue"][1]["revenue"]-1)*100
            position = (row["current_price"]-row["week52_low"])/(row["week52_high"]-row["week52_low"])*100
            row["metrics"] = dict(score_company(growth,position),rev_growth=growth,price_pos_pct=position)
        validated.append(row)
    coverage = sum(r["metrics"] is not None for r in validated)
    metrics = None
    if coverage == 2:
        mean = sum(r["metrics"]["company_score"] for r in validated)/2
        score = round(mean)
        state,color,arrow = (("SAFE","green","↗") if mean <25 else ("WATCH","yellow","→") if mean <45
                             else ("WARNING","orange","↘") if mean <65 else ("CRITICAL","red","↓"))
        metrics = {"unrounded_score":mean,"score":score,"state":state,"color":color,"arrow":arrow,
                   "contribution":score*.15,"mean_growth":sum(r["metrics"]["rev_growth"] for r in validated)/2}
    return {"version":VERSION,"checked_at":checked_at,"rows":validated,"coverage":coverage,
            "available":coverage==2,"metrics":metrics,"rule":deepcopy(RULE),"limitation":LIMITATION}


def archive(snapshot,path=None):
    archive_snapshot(snapshot, path or STORE)


def history(path=None):
    return read_history(path or STORE)


@st.cache_data(ttl=3600)
def get_power_snapshot():
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(fetch_financial_row,TICKERS))
    return make_snapshot(rows,datetime.now(timezone.utc).isoformat())


def load_power():
    snapshot = get_power_snapshot()
    archive(snapshot)
    return snapshot
