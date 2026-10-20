"""Original VRT/SMCI detail scoring; related-company proxy, not cooling revenue."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from core.reit_pressure import (_fetch as fetch_financial_row, validate_row, number,
                                archive as archive_snapshot, history as read_history)

STORE = Path(__file__).resolve().parents[1] / ".local" / "liquid_signal_history.sqlite3"
TICKERS = ("VRT", "SMCI")
VERSION = "liquid-detail-original-complete-v1"
RULE = {
    "version": VERSION, "weight": .25,
    "growth_score": "annual growth <10/<30/<60/<100/otherwise -> 10/30/55/75/90",
    "price_score": "price position >80/>60/>40/otherwise -> 80/60/40/20",
    "formula": "position=(latest_close-year_low)/(year_high-year_low)*100; growth=(latest_annual_revenue/prior_annual_revenue-1)*100; company=.65*growth_score+.35*price_score; score=round(mean(VRT,SMCI)); contribution=score*.25",
    "states": "unrounded company mean <25/<50/<70/otherwise -> SAFE/WATCH/WARNING/CRITICAL",
    "missing": "Both fixed companies require valid prices, nonconstant range and two adjacent annual revenue values; no 0/50 imputation or averaging one company.",
}
LIMITATION = "使用VRT与SMCI公司总营收和股价作为液冷相关企业代理，不是液冷业务单独收入、实际订单、装机量或营收增长率的加速度。公司增长和股价上涨不能直接证明风冷机房淘汰或资产减值。"
BUSINESS_SOURCES = {
    "VRT": "https://www.vertiv.com/en-us/about/about-us/",
    "SMCI": "https://ir.supermicro.com/",
}
LEGACY_RULES = {
    "detail": "原详情公司分＝年度总营收增长映射分×65%＋股价区间位置映射分×35%，两公司平均取整；保留公式及25%权重。原缺失营收给50、无效区间默认50、缺一家按剩余公司计分，现已停用这些缺失处理。",
    "overview": "原总览仅取两家公司一年调整后收盘区间位置平均，不含年度营收，且高低点口径不同。现改为共用详情原公式，存在方法断点，不将总览分差说成市场突然变化。",
    "interpretation": "原文“液冷厂商爆发＝风冷淘汰加速”缺乏直接证据，现明确为相关企业代理，不作淘汰或减值证明。",
    "history_note": "这些是旧方法资料，不是旧实测成绩；此前未保存的原始数据和分数不回填。",
}


def score_company(growth, position):
    if not number(growth) or not number(position) or not 0 <= position <= 100:
        raise ValueError("年度增长率或股价位置无效，不能填默认分")
    gs = 10 if growth < 10 else 30 if growth < 30 else 55 if growth < 60 else 75 if growth < 100 else 90
    ps = 80 if position > 80 else 60 if position > 60 else 40 if position > 40 else 20
    return {"growth_score":gs, "price_score":ps, "company_score":gs*.65+ps*.35}


def make_snapshot(rows, checked_at):
    if len(rows) != 2 or {r["ticker"] for r in rows} != set(TICKERS):
        raise ValueError("液冷相关企业必须固定VRT和SMCI，不以单公司或其他公司代替")
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
        state,color,arrow = (("SAFE","green","↗") if mean <25 else ("WATCH","yellow","→") if mean <50
                             else ("WARNING","orange","↘") if mean <70 else ("CRITICAL","red","↓"))
        metrics = {"unrounded_score":mean,"score":score,"state":state,"color":color,"arrow":arrow,
                   "contribution":score*.25,"mean_growth":sum(r["metrics"]["rev_growth"] for r in validated)/2}
    return {"version":VERSION,"checked_at":checked_at,"rows":validated,"coverage":coverage,
            "available":coverage==2,"metrics":metrics,"rule":deepcopy(RULE),"limitation":LIMITATION}


def archive(snapshot,path=None):
    archive_snapshot(snapshot, path or STORE)


def history(path=None):
    return read_history(path or STORE)


@st.cache_data(ttl=3600)
def get_liquid_snapshot():
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(fetch_financial_row,TICKERS))
    return make_snapshot(rows,datetime.now(timezone.utc).isoformat())


def load_liquid():
    snapshot = get_liquid_snapshot()
    archive(snapshot)
    return snapshot
