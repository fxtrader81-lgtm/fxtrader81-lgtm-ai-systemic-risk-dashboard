# =========================================================
# pages/straw1.py
# 稻草一：AI资本开支循环检测
#
# 重构说明：
#   - 指标逻辑、阈值、图表内容：完全保留
#   - CSS / fetch() / go.Figure() 基础代码：已抽离
# =========================================================

import streamlit as st
from components.ui import load_css, render_header, metric_card, render_footer, panel_open, panel_close, logic_step, threshold_row
from components.charts import build_growth_comparison_chart
from core.data_loader import fmp_income, fmp_cashflow, safe_float
from core.alert_engine import render_alert
from core.score_engine import register_score

# ---- 页面初始化 ----------------------------------------------
load_css()

col_title, col_input = st.columns([5, 1])
with col_input:
    symbol = st.text_input("股票代码", "NVDA")
with col_title:
    render_header(
        "🌾 稻草一：AI资本开支循环检测",
        "核心检测维度：资本开支扩张速度是否超过收入增长速度",
        symbol=symbol,
    )

# ---- 数据获取 ------------------------------------------------
income = fmp_income(symbol, limit=5)
cash   = fmp_cashflow(symbol, limit=5)

if isinstance(income, list) and isinstance(cash, list) and len(income) >= 2:

    cash_map = {item["date"]: item for item in cash if "date" in item}

    raw_list = []
    for inc in income:
        d_str = inc.get("date", "")
        if d_str in cash_map:
            csh = cash_map[d_str]
            try:
                y_val = int(inc.get("calendarYear", d_str[:4]))
            except Exception:
                continue
            raw_list.append({
                "year":    y_val,
                "revenue": safe_float(inc, "revenue"),
                "capex":   abs(safe_float(csh, "capitalExpenditure")),
            })

    raw_list.sort(key=lambda x: x["year"])

    final_timeline = []
    seen_years = set()
    for item in raw_list:
        if item["year"] not in seen_years:
            seen_years.add(item["year"])
            final_timeline.append(item)

    rev_growth   = (final_timeline[-1]["revenue"] - final_timeline[-2]["revenue"]) / final_timeline[-2]["revenue"]
    capex_growth = (final_timeline[-1]["capex"]   - final_timeline[-2]["capex"])   / final_timeline[-2]["capex"]
    diff         = capex_growth - rev_growth

    # ---- 状态判断 --------------------------------------------
    if diff >= 0.20:
        status, sc, si = "过热预警", "yellow", "⚠️"
        status_desc  = "当前AI资本扩张已进入<br>高波动风险阶段。"
        alert_state  = "WARNING"
        alert_title  = "结论：AI资本开支扩张速度明显高于收入增长，进入过热阶段"
        alert_body   = (f'当前资本开支增速比收入增速高出 <span class="yellow"><b>{diff*100:.2f}%</b></span>，'
                        f'企业AI基础设施投入已超出现实需求支撑。<br>'
                        f'若趋势持续，将提升未来盈利与现金流承压风险，需重点跟踪需求兑现情况。')
        risk_score   = 70
    elif diff >= 0:
        status, sc, si = "偏热", "yellow", "⚠️"
        status_desc  = "资本扩张开始领先收入增长。<br>系统进入高估值区间。"
        alert_state  = "WATCH"
        alert_title  = "结论：资本开支增速超出收入增速，进入偏热区间"
        alert_body   = (f'当前资本开支增速比收入增速高出 <span class="yellow"><b>{diff*100:.2f}%</b></span>，'
                        f'资本扩张速度开始领先，需关注需求兑现节奏。')
        risk_score   = 40
    else:
        status, sc, si = "健康", "green", "✅"
        status_desc  = "收入增长仍高于资本扩张。<br>AI需求尚能支撑投资。"
        alert_state  = "SAFE"
        alert_title  = "结论：当前AI投资处于健康扩张阶段"
        alert_body   = (f'收入增速高于资本开支增速，差值为 <span class="green"><b>{abs(diff)*100:.2f}%</b></span>，'
                        f'AI基础设施投入与现实需求匹配良好。')
        risk_score   = 15

    # 注册评分（供 Dashboard 汇总）
    register_score("straw1", risk_score)

    # ---- 四张 KPI 卡片 ----------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    ds = "+" if diff >= 0 else ""

    with c1:
        st.markdown(metric_card(
            "收入增长率 (YoY)",
            f"{rev_growth*100:.2f}%", "green", "↗",
            "AI需求仍维持高增长。<br>当前收入扩张速度保持强劲.",
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(metric_card(
            "资本开支增长率 (YoY)",
            f"{capex_growth*100:.2f}%", "red", "↗",
            "企业正在加速AI基础设施投入。<br>CapEx扩张速度持续提升.",
        ), unsafe_allow_html=True)

    with c3:
        st.markdown(metric_card(
            "增速差 (CapEx - Revenue)",
            f"{ds}{diff*100:.2f}%", "yellow", "",
            "资本扩张速度已开始超过<br>收入增长速度。",
        ), unsafe_allow_html=True)

    with c4:
        st.markdown(metric_card(
            "状态判断",
            status, sc, si, status_desc,
        ), unsafe_allow_html=True)

    # ---- Alert -----------------------------------------------
    st.markdown(render_alert(alert_state, alert_title, alert_body),
                unsafe_allow_html=True)

    # ---- 下方面板 --------------------------------------------
    lp, rp = st.columns([1, 1.5])

    with lp:
        st.markdown(
            panel_open("⚙️ 检测逻辑") +
            logic_step(1, "获取最新两个财年数据：收入、资本开支") +
            logic_step(2, "计算收入增长率 = (本期收入 - 上期收入) / 上期收入") +
            logic_step(3, "计算资本开支增长率 = (本期资本开支 - 上期资本开支) / 上期资本开支") +
            logic_step(4, "计算增速差 = 资本开支增长率 - 收入增长率") +
            logic_step(5, "根据阈值判断状态：") +
            '<div class="threshold-block">' +
            threshold_row("#ef4444", "增速差 ≥ 20%",         "过热预警（红色）", "red") +
            threshold_row("#fbbf24", "0% ≤ 增速差 &lt; 20%", "偏离预警（黄色）", "yellow") +
            threshold_row("#22c55e", "增速差 &lt; 0%",        "健康（绿色）",     "green") +
            "</div>" +
            panel_close(),
            unsafe_allow_html=True,
        )

    with rp:
        st.markdown(panel_open("📈 趋势对比（最近5年）"), unsafe_allow_html=True)

        rg_list, cg_list, cy_list = [], [], []
        for i in range(1, len(final_timeline)):
            prev = final_timeline[i - 1]
            curr = final_timeline[i]
            if prev["revenue"] > 0 and prev["capex"] > 0 and curr["year"] >= 2023:
                rg_list.append(((curr["revenue"] - prev["revenue"]) / prev["revenue"]) * 100)
                cg_list.append(((curr["capex"]   - prev["capex"])   / prev["capex"])   * 100)
                cy_list.append(curr["year"])

        fig = build_growth_comparison_chart(cy_list, rg_list, cg_list)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(panel_close(), unsafe_allow_html=True)

    render_footer(f"Financial Modeling Prep (FMP) · 当前标的：{symbol}")

else:
    st.error("API数据加载失败，请检查股票代码是否正确。")
