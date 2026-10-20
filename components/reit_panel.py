"""Current evidence and immutable history in the existing dark factor-03 scope."""
import json
import streamlit as st
from components.ui import evidence_table
from core.reit_pressure import LEGACY_RULES


def _value(value, suffix="", decimals=2):
    return f"{value:,.{decimals}f}{suffix}" if value is not None else "N/A"


def render_current(snapshot):
    rows = snapshot["rows"]
    st.markdown(evidence_table("两家公司价格与一年窗口（USD，调整后日线）",
        ["公司", "最新收盘/日期", "一年最高/日期", "一年最低/日期", "实际窗口", "状态"], [
            (r["ticker"], f"{_value(r.get('current_price'))} / {r.get('price_date','未取得')}",
             f"{_value(r.get('week52_high'))} / {r.get('high_date','未取得')}",
             f"{_value(r.get('week52_low'))} / {r.get('low_date','未取得')}",
             f"{r.get('window_start','未取得')} 至 {r.get('window_end','未取得')}",r["reason"] or "完整") for r in rows
        ]), unsafe_allow_html=True)
    st.markdown(evidence_table("最近两个年度营收（报表原币，不是季度或TTM）",
        ["公司", "本期年度截止", "本期营收", "上期年度截止", "上期营收", "同比"], [
            (r["ticker"], (r["annual_revenue"]+[{},{}])[0].get("period_end","未取得"),
             _value((r["annual_revenue"]+[{},{}])[0].get("revenue")),
             (r["annual_revenue"]+[{},{}])[1].get("period_end","未取得"),
             _value((r["annual_revenue"]+[{},{}])[1].get("revenue")),
             _value(r["metrics"]["rev_growth"],"%") if r["metrics"] else "N/A") for r in rows
        ]), unsafe_allow_html=True)
    st.caption(f"采集时间UTC：{snapshot['checked_at']} · 必要数据覆盖{snapshot['coverage']}/2家公司。价格日期、财务年度和采集日期分别列示，不把读取时间当数据日期。")
    st.write("股价回撤＝（一年最高价－最新日收盘价）÷一年最高价×100%；最高/最低使用调整后日内High/Low，不是收盘高低点。营收同比＝（本期年度营收÷上期年度营收－1）×100%。")
    st.markdown(evidence_table("逐家公司计算（沿用原详情公式）", ["公司", "股价回撤", "价格分P", "营收同比", "增长分G", "公司分P×65%＋G×35%"], [
        (r["ticker"], _value(r["metrics"]["from_high_pct"],"%") if r["metrics"] else "N/A",
         r["metrics"]["price_score"] if r["metrics"] else "N/A",
         _value(r["metrics"]["rev_growth"],"%") if r["metrics"] else "N/A",
         r["metrics"]["growth_score"] if r["metrics"] else "N/A",
         _value(r["metrics"]["company_score"]) if r["metrics"] else "N/A") for r in rows
    ]), unsafe_allow_html=True)
    m = snapshot["metrics"]
    if m:
        terms = "＋".join(f"{r['metrics']['company_score']:.4f}" for r in rows)
        st.write(f"两家公司均分＝（{terms}）÷2＝{m['unrounded_score']:.4f}；按原规则取整为{m['score']}分，REIT状态{m['state']}；×整页35%权重贡献{m['contribution']:.4f}分。状态按取整前均分判断，沿用旧逻辑。")
    else:
        st.warning("REIT必要数据不完整，分项N/A；不按一家计分、不补0或50分。详情完整DCOI暂不可用；总览沿用原有效权重覆盖政策，缺失REIT不贡献分数。旧有效记录仅供历史查阅，不冒充本次结果。")
    st.write(snapshot["limitation"])
    st.markdown(evidence_table("原价格映射（保留）",["回撤d", "价格分P"],[
        ("0 ≤ d < 5%",10),("5% ≤ d < 15%",35),("15% ≤ d < 25%",60),("25% ≤ d < 40%",80),("d ≥ 40%",95)]), unsafe_allow_html=True)
    st.markdown(evidence_table("原营收映射（保留）",["年度同比g", "增长分G"],[
        ("g > 12%",10),("6% < g ≤ 12%",30),("0% < g ≤ 6%",55),("g ≤ 0%",80)]), unsafe_allow_html=True)
    st.write("REIT状态：取整前均分＜25为SAFE；25≤均分＜50为WATCH；50≤均分＜70为WARNING；均分≥70为CRITICAL。不是只凭股价跌幅判断，也不同于整页DCOI的25/45/65切点。上述均为项目既有研究规则，未重新校准。")
    for r in rows:
        st.markdown(f"[{r['ticker']}价格来源]({r['source_url']}) · [{r['ticker']}年度报表来源]({r['financial_source_url']})")
    st.caption("自动读取、缓存1小时；下次打开或重新加载页面且缓存过期时重取，不新增手动刷新或后台定时任务。总览与详情共用此REIT入口；各分项按各自已确认的规则独立计算。")


def render_history(snapshot, records):
    st.markdown(evidence_table("REIT采集记录", ["采集时间UTC", "覆盖", "分项分数", "状态", "35%贡献", "两家公司价格日期"], [
        (r["checked_at"],f"{r['coverage']}/2",r["metrics"]["score"] if r["metrics"] else "N/A",
         r["metrics"]["state"] if r["metrics"] else "N/A",
         _value(r["metrics"]["contribution"]) if r["metrics"] else "N/A",
         " / ".join(f"{row['ticker']} {row.get('price_date','未取得')}" for row in r["rows"])) for r in records
    ]), unsafe_allow_html=True)
    for record in records:
        label = record["metrics"]["state"] if record["metrics"] else "N/A"
        with st.expander(f"采集资料：{record['checked_at']} · {label}", expanded=False):
            render_current(record)
    with st.expander("旧版方法资料（不是旧实测成绩）", expanded=False):
        for text in LEGACY_RULES.values(): st.write(text)
    st.caption("从本轮起按原始内容追加去重；失败不覆盖旧有效记录，不回填不存在的旧数据或旧分数。历史存当前部署本地磁盘，云端重建不保证持久，请下载备份。保留一年价格原始序列、年度营收、日期、公式、版本、分数与状态。")
    st.download_button("下载REIT历史与原始资料", json.dumps({"current":snapshot,"records":records,"legacy_methods":LEGACY_RULES},ensure_ascii=False,indent=2),
        file_name="reit-pressure-history.json",mime="application/json",key="download_reit_history")
