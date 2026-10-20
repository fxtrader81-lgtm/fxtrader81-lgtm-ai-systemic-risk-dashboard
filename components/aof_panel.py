"""AOF evidence follows factor 02's collapsed current/history pattern."""
import json
import streamlit as st
from components.ui import evidence_table


def render_current(snapshot):
    r, m = snapshot["reference"], snapshot["metrics"]
    st.markdown(evidence_table("AOF本期参考参数", ["参数", "数值", "口径与来源"], [
        ("参考机柜", r["model"], r["source_note"]),
        ("整柜功率需求", f"{r['rack_kw']:g}kW", r["source_url"] or "旧资料：原始出处未核验"),
        ("旧机房容量参考情景", f"{r['baseline_kw']:g}kW", r["baseline_note"]),
    ]), unsafe_allow_html=True)
    st.write(f"AOF＝{r['rack_kw']:g}÷{r['baseline_kw']:g}＝{m['aof']:g}倍；分项{m['score']}/100，状态{m['state']}；×25%贡献{m['contribution']:g}分。")
    st.write(snapshot["limitation"])
    st.write(snapshot["rule"]["note"])
    st.caption(f"项目启用日期：{r['effective_date'] or '原记录未提供'} · 复核日期：{r['reviewed_date']} · 官方资料发布日期：{r['source_published_date'] or '未记录'}。复核日期不等于硬件发布日期或现场实测日期。")
    if r["source_url"]:
        st.markdown(f"[查看NVIDIA官方原文]({r['source_url']})")
        st.write(f"留存原文片段：{r['source_excerpt']}")
    st.markdown(evidence_table("沿用原评分规则（未重校准）", ["AOF范围", "分数公式", "状态"], [
        ("0 < AOF < 1.5", "0", "SAFE"),
        ("1.5 ≤ AOF < 2.5", "round[(AOF−1.5)×33]", "WATCH"),
        ("2.5 ≤ AOF < 3.5", "round[33＋(AOF−2.5)×34]", "WARNING"),
        ("AOF ≥ 3.5", "round[min(100,67＋(AOF−3.5)÷0.5×33)]", "CRITICAL"),
    ]), unsafe_allow_html=True)
    st.caption("固定参数版本，不在页面刷新时自动追逐新硬件；确认新官方规格后新增版本，旧版保留。不增加刷新按钮或定时任务。")


def render_history(current, records):
    st.markdown(evidence_table("AOF历史版本与评分", ["项目启用日期", "参考方案", "功率/容量kW", "AOF", "状态", "分项分数", "25%贡献"], [
        (r["reference"]["effective_date"] or "旧版日期未记录", r["reference"]["model"],
         f"{r['reference']['rack_kw']:g}/{r['reference']['baseline_kw']:g}", f"{r['metrics']['aof']:g}倍",
         r["metrics"]["state"], r["metrics"]["score"], r["metrics"]["contribution"]) for r in records
    ]), unsafe_allow_html=True)
    st.write("旧版H100的2.4倍、WATCH、30分和7.5分贡献来自原代码复算，不是新补采的历史市场数据；旧60kW配置与25kW容量出处未核验。新版4.8倍、100分的变化来自参考方案更换，不能作同口径趋势。这里只保存AOF分项，不虚构历史DCOI整页总分。")
    for row in records:
        r = row["reference"]
        with st.expander(f"版本资料：{r['id']}", expanded=False):
            render_current(row)
            old_chart = r.get("chart_reference")
            if old_chart:
                st.write(old_chart["note"])
                st.caption("以上为首次归档时的说明，保留不改写。原六代参数现已恢复在主图中作历史示意展示，仍不参与本期AOF评分。")
                st.markdown(evidence_table("旧版GPU示意参数（仅归档）", ["世代", "下限kW", "上限kW", "旧版原标签"], [
                    (g["gen"], g["rack_kw_min"], g["rack_kw_max"], g["original_status"]) for g in old_chart["generations"]
                ]), unsafe_allow_html=True)
                st.caption(f"旧版另设改造风冷参考线{old_chart['upgraded_rack_limit_kw']}kW，未参与AOF分母。原标签不代表已证实的淘汰或市场份额。")
            st.caption(f"首次归档时间UTC：{row['archived_at']}；不是历史部署或评测日期。")
    st.caption("沿用02：按版本追加去重、不覆盖旧记录，原参数、来源、公式、分数、状态可下载。历史在当前部署本地磁盘；云端重建不保证持久，请下载备份。初始新旧两版随代码保留。")
    st.download_button("下载AOF历史与原始资料", json.dumps({"current": current, "records": records}, ensure_ascii=False, indent=2),
                       file_name="aof-reference-history.json", mime="application/json", key="download_aof_history")
