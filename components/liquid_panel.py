"""Factor-02 style collapsed current/history evidence within dark factor-03 UI."""
import json
import streamlit as st
from components.ui import evidence_table
from components.reit_panel import _value
from core.liquid_signal import LEGACY_RULES


def render_current(snapshot):
    rows = snapshot["rows"]
    st.write(snapshot["limitation"])
    st.markdown(evidence_table("相关企业价格与一年窗口（USD，调整后日线）",
        ["公司", "最新收盘/日期", "一年最高/日期", "一年最低/日期", "实际窗口", "状态"], [
            (r["ticker"],f"{_value(r.get('current_price'))} / {r.get('price_date','未取得')}",
             f"{_value(r.get('week52_high'))} / {r.get('high_date','未取得')}",
             f"{_value(r.get('week52_low'))} / {r.get('low_date','未取得')}",
             f"{r.get('window_start','未取得')} 至 {r.get('window_end','未取得')}",r["reason"] or "完整") for r in rows
        ]),unsafe_allow_html=True)
    st.markdown(evidence_table("公司总营收原始数据（年度、报表原币，非液冷分部收入）",
        ["公司", "本期财年截止", "本期总营收", "上期财年截止", "上期总营收", "年度同比"], [
            (r["ticker"],(r["annual_revenue"]+[{},{}])[0].get("period_end","未取得"),
             _value((r["annual_revenue"]+[{},{}])[0].get("revenue")),
             (r["annual_revenue"]+[{},{}])[1].get("period_end","未取得"),
             _value((r["annual_revenue"]+[{},{}])[1].get("revenue")),
             _value(r["metrics"]["rev_growth"],"%") if r["metrics"] else "N/A") for r in rows
        ]),unsafe_allow_html=True)
    st.caption(f"采集时间UTC：{snapshot['checked_at']} · 必要数据覆盖{snapshot['coverage']}/2家公司。两家公司按各自最新相邻财年同比，不冒充相同自然年度、季度或TTM；采集时间不是财报发布日期。")
    st.write("股价位置＝（最新调整后日收盘价－一年调整后日内最低价）÷（一年调整后日内最高价－最低价）×100%；营收同比＝（本期年度总营收÷上期年度总营收－1）×100%。")
    st.markdown(evidence_table("逐家公司计算（保留原公式）",["公司", "年度同比", "增长分G", "股价位置", "价格分P", "公司分G×65%＋P×35%"],[
        (r["ticker"],_value(r["metrics"]["rev_growth"],"%") if r["metrics"] else "N/A",
         r["metrics"]["growth_score"] if r["metrics"] else "N/A",
         _value(r["metrics"]["price_pos_pct"],"%") if r["metrics"] else "N/A",
         r["metrics"]["price_score"] if r["metrics"] else "N/A",
         _value(r["metrics"]["company_score"]) if r["metrics"] else "N/A") for r in rows
    ]),unsafe_allow_html=True)
    m = snapshot["metrics"]
    if m:
        terms = "＋".join(f"{r['metrics']['company_score']:.4f}" for r in rows)
        st.write(f"两家公司平均＝（{terms}）÷2＝{m['unrounded_score']:.4f}；按原规则取整{m['score']}分，状态{m['state']}；×整页25%贡献{m['contribution']:.4f}分。状态按取整前均分判断。卡片百分比为两家公司年度总营收同比均值，不是本分项分数或液冷业务增速。")
    else:
        st.warning("液冷相关企业必要数据不完整，分项N/A；不按一家计分、不补0或50分。详情完整DCOI暂不可用；总览沿用原有效权重覆盖政策，缺失本分项不计分。旧有效记录仅供查阅，不冒充本次结果。")
    st.markdown(evidence_table("原营收增长映射（保留）",["年度同比g", "增长分G"],[
        ("g < 10%",10),("10% ≤ g < 30%",30),("30% ≤ g < 60%",55),("60% ≤ g < 100%",75),("g ≥ 100%",90)]),unsafe_allow_html=True)
    st.markdown(evidence_table("原股价位置映射（保留）",["位置p", "价格分P"],[
        ("p > 80%",80),("60% < p ≤ 80%",60),("40% < p ≤ 60%",40),("0% ≤ p ≤ 40%",20)]),unsafe_allow_html=True)
    st.write("液冷分项状态：取整前均分＜25为SAFE；25≤均分＜50为WATCH；50≤均分＜70为WARNING；均分≥70为CRITICAL。沿用原研究规则，未重新校准；不是单看营收增速，也不等于整页DCOI状态。")
    for r in rows:
        st.markdown(f"[{r['ticker']}价格来源]({r['source_url']}) · [{r['ticker']}年度报表来源]({r['financial_source_url']}) · [{r['ticker']}业务范围]({r['business_source_url']})")
    st.caption("自动读取、缓存1小时；下次打开或重新加载页面且缓存过期时重取。不另加刷新按钮或后台定时任务。总览与详情共用本分项入口；各分项仍保留各自已确认的公式和权重。")


def render_history(snapshot,records):
    st.markdown(evidence_table("液冷相关企业采集记录",["采集时间UTC", "覆盖", "分项分数", "状态", "25%贡献", "两家公司财年截止"],[
        (r["checked_at"],f"{r['coverage']}/2",r["metrics"]["score"] if r["metrics"] else "N/A",
         r["metrics"]["state"] if r["metrics"] else "N/A",_value(r["metrics"]["contribution"]) if r["metrics"] else "N/A",
         " / ".join(f"{row['ticker']} {row['annual_revenue'][0]['period_end'] if row['annual_revenue'] else '未取得'}" for row in r["rows"])) for r in records
    ]),unsafe_allow_html=True)
    for record in records:
        state = record["metrics"]["state"] if record["metrics"] else "N/A"
        with st.expander(f"液冷采集资料：{record['checked_at']} · {state}",expanded=False):
            render_current(record)
    with st.expander("液冷旧版方法资料（不是旧实测成绩）",expanded=False):
        for text in LEGACY_RULES.values(): st.write(text)
    st.caption("沿用02：按原始内容追加去重，失败不覆盖旧有效记录；从本轮起采集，不回填不存在的旧成绩。保留一年价格原始序列、年度营收/财年、来源、规则、状态和分数。历史存当前部署本地磁盘，云端重建不保证持久，请下载备份。")
    st.download_button("下载液冷历史与原始资料",json.dumps({"current":snapshot,"records":records,"legacy_methods":LEGACY_RULES},ensure_ascii=False,indent=2),
                       file_name="liquid-signal-history.json",mime="application/json",key="download_liquid_history")
