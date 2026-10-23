"""Factor 04's optional quarterly source inspection, separate from score inputs."""
import json
from zoneinfo import ZoneInfo
import streamlit as st
from components.ui import evidence_table
from components.protected_download import protected_download_button
from core import infra_updates as updates
from core.infra_current import load_infra, score_infra


def _date(value):
    return value.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M") if value else "尚无成功检查"


def render_infra_updates(inputs):
    with st.container(key="infra_updates"):
        updates.record_baseline(inputs)
        current=load_infra()
        records = updates.history()
        timing = updates.reminder(records)
        if timing["due"]:
            st.markdown("**基础设施资料：建议检查更新** · 每90天提醒，不是后台定时任务。")
        with st.expander("基础设施约束｜数据更新管理", expanded=False):
            data=current["inputs"]
            st.write(f"主卡片共用当前输入：并网中位时长{data['interconnection_queue_months']}个月（2025年投运）；PJM {data['pjm_reserve_margin_pct']}% / ERCOT {data['ercot_reserve_margin_pct']}%（2026夏季ARM）；变压器{data['transformer_lead_time_months']}个月为用户确认的近似交付压力上限情景，不是平均值。基础设施情景分：{current['score']}。必要证据缺失时才显示N/A。")
            st.caption(current["method_note"])
            st.write(f"上次成功来源检查：{_date(timing['last_success'])}（洛杉矶时间）")
            st.write(f"建议下次检查：{_date(timing['next_due']) if timing['next_due'] else '现在可检查'}。未到期也可主动检查，不限制失败后的重试。")
            st.caption("保留90天检查提醒；已核验字段供主卡片共用，变压器按本期确认的48月近似上限情景计算。未知新字段、年份或定义变化标待核验，不自动追逐另一个上限。没有新可比数据时保留原资料期间，不改成检查日期。")
            st.caption("当前已接入LBNL 2026版报告PDF、NERC 2026夏季报告PDF和DOE研讨会原文的结构化取数；只核对这些已明确的来源，不声称已穷尽全网或自动发现未来版次。")
            if st.button("检查基础设施资料更新", key="check_infra_sources"):
                with st.spinner("正在检查三处官方资料入口…"):
                    result = updates.check_sources()
                if result["status"] == "busy":
                    st.info("已有检查正在进行，请稍后重新打开本页查看结果。")
                else:
                    from core.factor_registry import load_factor_results
                    load_factor_results.clear()
                    st.rerun()
            if records["checks"]:
                latest = records["checks"][0]
                st.write(f"最近一次尝试（UTC）：{latest['started']}")
                if latest["status"] == "success":
                    st.success("指定资料读取完成；并网/备用裕度共用来源字段，变压器采用本期确认的48月上限压力情景（非平均）。")
                elif latest["status"] == "running":
                    st.info("检查进行中；五分钟后未完成的检查允许重新尝试。")
                else:
                    st.warning("最近检查未完整成功：不顺延建议日期，可重试；保留上次核验资料及其原始期间，缺失交期不填旧值。")
                labels = {"first": "首次保存；采用状态见下表", "changed": "来源内容变化；字段重新校验", "unchanged": "本页正文及链接未变；不等于全网无新版"}
                by_id = {r["source_id"]: r for r in latest["sources"]}
                st.markdown(evidence_table("来源检查结果", ["来源", "发布节奏/口径", "本次检查"], [
                    (s["name"], s["cadence"], labels.get(by_id.get(s["id"], {}).get("comparison"),
                     by_id.get(s["id"], {}).get("reason", "读取失败，可重试") if by_id.get(s["id"], {}).get("status") == "failed" else "尚未完成")) for s in updates.SOURCES
                ]), unsafe_allow_html=True)
                lookup = {e["id"]:e for e in records["evidence"]}
                facts = [(s, lookup.get(by_id.get(s["id"],{}).get("evidence_id"),{}).get("extracted")) for s in updates.SOURCES]
                if any(f for _,f in facts):
                    st.markdown(evidence_table("本期输入证据与48月压力情景",
                        ["指标","原始数据/描述","采用边界"],[(s["name"],f["display"],
                         "已接入：2025投运IR至COD中位时长；不是数据中心接电等待" if s["id"]=="queue" and f.get("kind")=="point" else
                         "已接入：2026夏季ARM；不是参考裕度或晚间风险裕度" if s["id"]=="reserve" and f.get("kind")=="point" else
                         "48月作为近似压力上限情景，不是全国平均交期；资料观察期未明确" if s["id"]=="transformer" and current["scenario"]["evidence_valid"] else
                         f.get("review","字段待核验")) for s,f in facts if f]),unsafe_allow_html=True)
                    st.write("计算沿用原公式：并网61月映射100分；变压器48月近似上限情景映射100分；两地夏季ARM均值47.05%映射0分。基础设施情景分=100×45%+100×30%+0×25%=75分，按原整页40%权重贡献30分。这是情景评分，不是实测平均交期或缺电概率；新旧有口径断点。")
            for source in updates.SOURCES:
                st.markdown(f"[{source['name']}官方入口]({source['url']})")
            with st.expander("旧版输入与评分参考（不再用于当前计算）",expanded=False):
                st.markdown(evidence_table("旧静态输入与当前状态",["指标","旧版录入值","当前主卡片"],[
                    ("并网耗时","43个月，定义未核验","61个月，2025年投运项目IR至COD中位时长"),
                    ("变压器交期","36个月，原始来源未核验","48个月近似压力上限情景；不是平均交期"),
                    ("PJM / ERCOT裕度","16.5% / 12.8%，季节/字段未核验","26.2% / 67.9%，2026夏季ARM"),
                    ("基础设施分项",f"{score_infra(inputs)}分，原阈值WARNING；录入标记{inputs['updated']}",f"{current['score']}分（含48月上限情景）")]),unsafe_allow_html=True)
            st.caption("来源证据及采用输入版本分别去重保存，尝试日志单独保留；失败不改数据日期。旧版与本版有口径断点，不把两版分差作市场变化。")
            st.caption("记录保存在本地磁盘，跨页面/会话可读取；云端重新部署或磁盘重建不保证保留。若记录丢失，显示尚无检查而非伪造检查日期。可下载备份，暂未接入外部数据库。")
            protected_download_button("下载基础设施检查记录与原始资料", json.dumps(records, ensure_ascii=False, indent=2),
                                      file_name="infra-source-checks.json", mime="application/json", key="download_infra_checks")
