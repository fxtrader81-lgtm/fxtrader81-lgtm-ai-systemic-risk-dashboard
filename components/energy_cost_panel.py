import json
import streamlit as st
from components.ui import evidence_table
from core.energy_cost import history
from components.energy_cost_status import maintenance_status
from components.protected_download import protected_download_button


def _value(value, suffix=""):
    """Format stored values for people; raw values remain in the download."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "是" if value else "否"
    return f"{value:g}{suffix}" if isinstance(value, (int, float)) else str(value)


def _render_prior_cluster_evidence(evidence):
    st.write(f"核验日：{evidence.get('reviewed_on', '未记录')}。{evidence.get('method', '')}")
    st.warning(evidence.get("missing_reason", "该批资料未纳入本期评分。"))
    rows = evidence.get("rows", [])
    st.markdown(evidence_table(
        "未纳入评分的地区与线索",
        ["地区/线索", "公开价格", "资料期间", "资料性质", "本期处理"],
        [(r.get("region", "N/A"), r.get("price", "N/A"), r.get("period", "N/A"),
          r.get("classification", "N/A"), r.get("adoption", "N/A")) for r in rows],
        note="这些资料用于保留调查轨迹，不会混入本期固定地区篮子的计算。",
    ), unsafe_allow_html=True)
    st.markdown("**来源与核验说明**")
    for row in rows:
        st.markdown(f"- [{row.get('region', '资料来源')}]({row.get('source_url', '#')})：{row.get('evidence', '未记录证据摘要')}（{row.get('access', '核验状态未记录')}）")
    st.caption(evidence.get("aggregation_policy", ""))


def _render_industrial_background(background):
    rows = background.get("rows", [])
    st.markdown(evidence_table(
        "2025年工业电价背景",
        ["国家/地区", "价格（美元/MWh）", "折合美元/kWh", "口径"],
        [("美国" if r.get("country") == "US" else "中国", _value(r.get("usd_mwh")),
          f"{r.get('usd_mwh') / 1000:.3f}" if isinstance(r.get("usd_mwh"), (int, float)) else "N/A",
          r.get("scope", "N/A")) for r in rows],
        note="仅作背景参考，不计入本期能源成本评分。",
    ), unsafe_allow_html=True)
    st.write(f"资料期间：{background.get('period', '未记录')}；来源更新：{background.get('source_updated', '未记录')}；本地核验：{background.get('reviewed_on', '未记录')}。")
    st.write(f"采集方式：{background.get('capture_method', '未记录')} ")
    st.write(f"口径限制：{background.get('caveat', '未记录')} ")
    st.write(f"复核安排：{background.get('refresh_policy', '未记录')} ")
    st.write(f"电力占OpEx {_value(background.get('opex_pct'), '%')}：{background.get('opex_classification', '未记录')}。")


def _render_history_record(record):
    summary = [
        ("资料版本", record.get("id", "N/A")),
        ("资料期间", record.get("period", record.get("recorded_period", "未记录"))),
        ("本地采纳时间", record.get("adopted_at", "未记录")),
        ("是否可评分", _value(record.get("available")) if "available" in record else "旧记录"),
        ("分项得分", _value(record.get("score"))),
        ("价格比", _value(record.get("ratio"))),
    ]
    st.markdown(evidence_table("记录摘要", ["项目", "内容"], summary), unsafe_allow_html=True)
    for key, label in (
        ("classification", "资料性质"), ("method", "方法"),
        ("selection_policy", "样本规则"), ("aggregation_policy", "汇总规则"),
        ("scoring_policy", "评分规则"), ("missing_reason", "缺口"),
        ("caveat", "限制"),
    ):
        if record.get(key):
            st.write(f"{label}：{record[key]}")

    rows = record.get("rows", [])
    if rows and any("region" in row for row in rows):
        st.markdown(evidence_table(
            "本记录样本",
            ["地区/样本", "价格", "资料期间", "分类"],
            [(r.get("region", r.get("country", "N/A")), r.get("price", "N/A"),
              r.get("period", "N/A"), r.get("classification", "N/A")) for r in rows],
        ), unsafe_allow_html=True)
    elif rows:
        st.markdown(evidence_table(
            "本记录样本",
            ["国家/地区", "价格（美元/MWh）", "口径"],
            [("美国" if r.get("country") == "US" else "中国" if r.get("country") == "CN" else r.get("country", "N/A"),
              _value(r.get("usd_mwh")), r.get("scope", "N/A")) for r in rows],
        ), unsafe_allow_html=True)

    links = []
    if record.get("source_url"):
        links.append((record.get("source_title", "主资料来源"), record["source_url"]))
    links.extend((r.get("region", "样本来源"), r["source_url"]) for r in rows if r.get("source_url"))
    if links:
        st.markdown("**资料来源**")
        for label, url in links:
            st.markdown(f"- [{label}]({url})")


def render_cost_evidence(snapshot, include_history=True):
    # Reuse the reviewed dark expander/button styling of the infrastructure panel.
    with st.container(key="infra_updates_cost"):
        with st.expander("能源成本压力｜本期对比与计算说明", expanded=False):
            st.caption(maintenance_status(snapshot)["detail"])
            for country, title in (("CN", "中国固定地区参考价（2地区）"), ("US", "美国固定地区工业代理（4州）")):
                st.markdown(evidence_table(title, ["地区/样本", "公开价格", "资料期间", "分类与采用状态"],
                    [(r["region"], r["price"], r["period"], r["classification"])
                     for r in snapshot["rows"] if r["country"] == country]), unsafe_allow_html=True)
            st.write(snapshot["method"])
            st.write(snapshot["selection_policy"])
            st.caption("中国目前只有2个地区：中位数等于两者均值，不能宣称已获得大样本的抗异常值能力；地区代表性仍有限。")
            st.write(snapshot["caveat"])
            st.write(snapshot["aggregation_policy"])
            if snapshot.get("ratio_range"):
                cn, us, ratios, scores = (snapshot[k] for k in ("cn_price_range", "us_price_range", "ratio_range", "score_range"))
                fx_value = snapshot["fx"]["cny_per_usd"]
                st.write(f"中国中位数区间：{cn[0]*fx_value:.3f}—{cn[1]*fx_value:.3f}元/kWh，换算{cn[0]:.6f}—{cn[1]:.6f}美元/kWh；美国中位数区间：{us[0]:.6f}—{us[1]:.6f}美元/kWh（偶数样本取排序后中间两项均值）。")
                st.write(f"中国÷美国参考电价比：{ratios[0]:.4f}—{ratios[1]:.4f}；四档映射得分：{scores[0]:g}—{scores[1]:g}分。区间是报价端点敏感性，不是统计置信区间。")
            if snapshot["available"]:
                st.write(f"两端同为{snapshot['state']} / {snapshot['score']:g}分，沿原25%权重贡献{snapshot['score']*.25:g}分；不取报价中点，不平均两个得分。这只说明对本期报价区间稳健，不说明对地区选择或费用差异稳健。")
            else:
                st.write(snapshot["missing_reason"] + "；不补旧分、不重分配权重。")
            fx = snapshot["fx"]
            st.markdown(f"汇率：{fx['date']}，1美元={fx['cny_per_usd']}元人民币。[官方来源]({fx['source_url']})；{fx['basis']}。")
            st.write(f"资料核验日：{snapshot['reviewed_on']}，不是价格数据日；各条期间单独列示。")
            st.write(f"电力占OpEx {snapshot['opex_pct']}%：{snapshot['opex_classification']}。")
            st.write(snapshot["scoring_policy"])
            st.caption("15%费用占比仅保留作假设说明，不再改变本期档位或分数。临界值属于较低风险档：0.80为SAFE，0.60为WATCH，0.40为WARNING。")
            with st.expander("逐条来源、证据与核验限制", expanded=False):
                for r in snapshot["rows"]:
                    st.markdown(f"[{r['region']}]({r['source_url']})")
                    st.write(r["classification"] + "；" + r["period"])
                st.caption("伊吾官方答复本轮搜索索引再次核实0.35，正文直接读取超时；内蒙古及EIA正文可读。")
            with st.expander("未纳入本期：旧地区、目标价与财报线索", expanded=False):
                _render_prior_cluster_evidence(snapshot["prior_cluster_evidence"])
            with st.expander("IEA工业电价｜背景参考（不计本期评分）", expanded=False):
                background = snapshot["background"]
                st.write("2025年工业代理：美国0.050、中国0.068美元/kWh，价格比1.36。美国取得州；不是数据中心实际价格，不再用于本期成本评分。旧方法曾映射9分，不能当成本期新成绩。")
                st.markdown(f"[IEA原图及样本说明]({background['source_url']})")
                _render_industrial_background(background)
            st.caption("本期为核验录入的地区资料，不自动发现或采集新价格；不新增刷新按钮/后台任务。")
        if include_history:
            with st.expander("能源成本压力｜历史记录与原始资料", expanded=False):
                records = history()
                st.write("保留旧静态42.8分、IEA方法9分、集群待配对N/A、地区中位数旧公式9分及新四档方法40分。新旧有方法断点，不解释为电价突然变化；不伪造历史完整ESRI。")
                for r in records:
                    with st.expander(f"{r['id']} · 分项{r['score'] if r.get('score') is not None else 'N/A'}", expanded=False):
                        _render_history_record(r)
                st.caption("本地记录追加去重保存；云端磁盘重建可能丢失，可下载备份。")
                protected_download_button("下载能源成本历史与原始资料", json.dumps(records, ensure_ascii=False, indent=2),
                                          file_name="energy-cost-history.json", mime="application/json", key="download_energy_cost")
