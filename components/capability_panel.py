"""Factor 02's explicit refresh and inspectable capability evidence."""
import json
from html import escape

import streamlit as st

from components.ui import evidence_table
from core import capability_gap as cap
from core import capability_cohort as cohort
import subprocess


def _invalidate_overview():
    # The existing overview has its own result cache; only invalidate after adoption.
    from core.factor_registry import load_factor_results
    load_factor_results.clear()


def render_capability_controls():
    snapshot = cap.ensure_full_baseline()
    with st.container(key="capability_controls"):
        if st.button("刷新能力对比数据", key="refresh_capability_only",
                     help="只检查LiveBench公开成绩，不调用模型考试，不清除其他三项的数据缓存。"):
            with st.spinner("锁定Git提交，读取最新一期全部测试成绩并计算两组前三..."):
                try:
                    candidate = cohort.fetch_latest_snapshot()
                    changed = cap.adopt(candidate)
                    message = "已更新全任务／三平台对比并保留历史" if changed else "检查完成，来源成绩及筛选资料没有变化，未重复归档"
                    cap.record_refresh(message)
                    if changed:
                        _invalidate_overview()
                    st.success(message)
                except (ValueError, OSError, subprocess.SubprocessError, cap.requests.RequestException) as exc:
                    cap.record_refresh(f"检查失败（{type(exc).__name__}），保留上次有效结果")
                    st.warning(f"本次未采用新结果：{str(exc)[:240]}。保留上次有效结果，不填0、不用不足三家的平均分。")
        status = cap.last_refresh()
        notes = []
        if status:
            notes.append(f"最近检查：{status[0]} · {status[1]}")
        notes.extend([
            "建议每半年复核，未设置定时任务。按钮自动读取最新评测版本、纳入全部测试项，按已核验分组选择两组三家不同平台。",
            "同代口径＝同一评测版本、同一读取截止；不是要求六个型号发布在同一天。未知平台／产品线待核验，不按名称猜国别或开放方式。",
            "价格、部署工具关注度和模型下载量自动取数，缓存1小时；下次打开或重新加载页面时，缓存过期会重新获取。能力名单改变后，价格与下载样本自动跟随。未设置后台定时任务。",
        ])
        st.markdown('<div class="capability-refresh-notes">' +
                    ''.join(f'<p>{escape(note)}</p>' for note in notes) + '</div>',
                    unsafe_allow_html=True)
    return cap.current_snapshot()


def _render_three_task_evidence(snapshot):
    metrics = snapshot["metrics"]
    rows = [(label, f"{c:.3f}", f"{o:.3f}", f"{c-o:+.3f}")
            for label, c, o in zip(cap.TASK_LABELS, snapshot["closed_scores"], snapshot["open_scores"])]
    rows.append(("三项等权均分", f"{metrics['closed_avg']:.3f}",
                 f"{metrics['open_avg']:.3f}", f"{metrics['difference_pp']:+.3f}"))
    st.markdown(evidence_table("能力代差：当前公开对比",
        ["测试任务", snapshot["closed_model"], snapshot["open_model"], "闭源－开放权重（百分点）"], rows),
        unsafe_allow_html=True)
    st.markdown(
        f"相对得分差距＝（{metrics['closed_avg']:.6f}－{metrics['open_avg']:.6f}）"
        f"÷{metrics['closed_avg']:.6f}×100%＝**{metrics['signed_gap']:+.2f}%**。"
        f"风险计分取 max(0, 相对差距)＝{metrics['risk_gap']:.2f}%。\n\n"
        f"能力分项＝clamp[60×(25－{metrics['risk_gap']:.6f})÷25, 0, 60]"
        f"＝**{metrics['score']:.2f}分**；×20%贡献 **{metrics['contribution']:.2f}分**；"
        f"能力状态 **{metrics['state']}**。计算使用未舍入原值。")
    diffs = [(label, c-o) for label, c, o in zip(
        cap.TASK_LABELS, snapshot["closed_scores"], snapshot["open_scores"])]
    closest = min(diffs, key=lambda x: abs(x[1]))
    widest = max(diffs, key=lambda x: abs(x[1]))
    direction = "领先" if metrics["signed_gap"] > 0 else "落后" if metrics["signed_gap"] < 0 else "持平"
    st.write(f"总结：本次三项均分闭源{direction}，相对差距{metrics['signed_gap']:+.2f}%。"
             f"最接近的是{closest[0]}（闭源减开放权重{closest[1]:+.3f}个百分点），"
             f"差距最大的是{widest[0]}（{widest[1]:+.3f}个百分点）。"
             "这不是国家整体能力比较，也不证明企业已经迁移。")
    st.caption(f"来源：{snapshot['source']} · 评测版本：{snapshot['release']} · 原始型号测试日期：未提供")
    st.caption(f"此快照读取时间：{snapshot['checked_at']}（不是成绩测试日期）；SHA-256：{snapshot['source_sha256']}")
    st.markdown(f"[查看官方原始结果表]({cap.SOURCE_PAGE})")
    st.info(snapshot["caveat"])


def render_current_evidence(snapshot, key_suffix="current"):
    if snapshot.get("formula_version") != cohort.VERSION:
        _render_three_task_evidence(snapshot)
        return
    m = snapshot["metrics"]
    n = snapshot["task_count"]
    rows = []
    for side, label in (("closed", "美国闭源"), ("open", "中国开放权重")):
        for rank, item in enumerate(snapshot["selected"][side], 1):
            rows.append((label, rank, item["company"], item["model"], f"{item['total']:.3f}", f"{n}/{n}"))
    st.markdown(evidence_table("当期入选的六家平台", ["分组", "组内名次", "平台", "完整型号／推理档位", "全部任务总分", "成绩完整性"], rows), unsafe_allow_html=True)
    closed_totals = "＋".join(f"{r['total']:.3f}" for r in snapshot["selected"]["closed"])
    open_totals = "＋".join(f"{r['total']:.3f}" for r in snapshot["selected"]["open"])
    st.markdown(f"闭源组平均总分 C＝（{closed_totals}）÷3＝**{m['closed_avg']:.3f}**。\n\n"
                f"开放权重组平均总分 O＝（{open_totals}）÷3＝**{m['open_avg']:.3f}**。\n\n"
                f"相对代差＝（C－O）÷C×100%＝**{m['signed_gap']:+.2f}%**。"
                f"风险输入=max(0,相对代差)＝{m['risk_gap']:.6f}；"
                f"能力分=clamp[60×(25－输入)÷25,0,60]＝**{m['score']:.2f}**；"
                f"20%贡献 **{m['contribution']:.2f}分**；能力状态 **{m['state']}**。计算使用未舍入数值。")
    direction = "领先" if m["signed_gap"] > 0 else "落后" if m["signed_gap"] < 0 else "持平"
    st.write(f"总结：本期{snapshot['row_count']}条模型记录、{n}项测试，按全部任务等权求和，"
             f"各平台取最高完整型号，再各选三家。闭源组平均总分{direction}，"
             f"有符号相对差距{m['signed_gap']:+.2f}%，对应{m['state']}。"
             "该结果只描述本期入选领先平台的测试差距，不是全国平均能力、商业替代率或危机概率。")
    st.caption(f"评测版本 {snapshot['release']} · 读取时间 {snapshot['checked_at']} · 型号实际测试日期未提供")
    st.caption(f"Git提交 {snapshot['revision']} · CSV SHA-256 {snapshot['source_sha256']}")
    st.markdown(f"[查看锁定提交的原始CSV]({snapshot['source_page']})")
    st.info("本项目全任务等权口径，不是LiveBench官方七类等权综合分。"+snapshot["caveat"])
    with st.expander("全部测试项与入选型号原始成绩", expanded=False):
        chosen = snapshot["selected"]["closed"] + snapshot["selected"]["open"]
        st.markdown(evidence_table("", ["测试项"]+[r["model"] for r in chosen],
            [(task, *[f"{r['scores'][task]:.3f}" for r in chosen]) for task in snapshot["tasks"]]), unsafe_allow_html=True)
        st.download_button("下载本期完整来源CSV", snapshot["raw_csv"],
            file_name=f"livebench-{snapshot['release']}-{snapshot['source_sha256'][:12]}.csv", mime="text/csv",
            key="csv_"+cohort.fingerprint(snapshot)+"_"+key_suffix)
    with st.expander("平台筛选、排除原因与分类依据", expanded=False):
        platform_rows = [(side, r["company"], r["model"], f"{r['total']:.3f}")
            for side in ("closed", "open") for r in snapshot["rankings"][side]]
        st.markdown(evidence_table("各平台最高完整型号", ["组别", "平台", "型号", "总分"], platform_rows), unsafe_allow_html=True)
        st.markdown(evidence_table("未进入分组的记录", ["型号", "原因"],
            [(r["model"], r["reason"]) for r in snapshot["excluded"]]), unsafe_allow_html=True)
        st.caption(snapshot["policy"]["note"])
        st.caption("开放权重由同一提交的modelLinks标记核对；闭源组还必须属于已核验闭源产品线。来源变更与未知平台不会自动获得分类。")
    if snapshot.get("change_notes"):
        st.markdown("**与上次记录的区别**")
        for note in snapshot["change_notes"]:
            st.write(note)


def render_capability_history(label="能力代差｜历史记录与原始资料"):
    old = cap.baseline()["legacy"]
    old_metrics = cap.measure(old["closed_scores"], old["open_scores"], legacy=True)
    with st.container(key="capability_history"):
        with st.expander(label, expanded=False):
            st.markdown("#### 旧版资料：2025-01录入")
            st.markdown(evidence_table("", ["原测试", old["closed_model"], old["open_model"]],
                [(t, c, o) for t, c, o in zip(old["tasks"], old["closed_scores"], old["open_scores"])]),
                unsafe_allow_html=True)
            st.write(f"原均分：{old_metrics['closed_avg']:.4f} vs {old_metrics['open_avg']:.4f}；"
                     f"闭源减开源＝{old_metrics['difference_pp']:+.4f}个百分点，旧规则取非负后为0。"
                     "原能力状态 CRITICAL；原能力分项60分；按20%权重贡献12分。")
            st.write("旧公式：差距=max(0, 闭源均分－开源均分)；"
                     "能力分=clamp[60×(25－差距)÷25, 0, 60]。"
                     "旧阈值实际单位为百分点：>12 SAFE，6<差距≤12 WATCH，"
                     "2<差距≤6 WARNING，≤2 CRITICAL。原页面的%标注不准确。")
            st.write("历史总结：按旧录入值，DeepSeek-V3三项均分略高于GPT-4o，"
                     "所以闭源正向领先记为0，触发旧能力项CRITICAL；不代表当时整体02必然CRITICAL。")
            st.caption(old["note"])
            st.markdown("#### 已保存的各方法记录")
            st.caption("与旧版考试和公式不同，分数不可直接当作同口径时间序列。相同成绩重复检查不新增记录。")
            records = cap.history()
            st.markdown(evidence_table("", ["快照读取时间（UTC）", "闭源 / 开放权重", "相对差距", "能力状态", "能力分", "20%贡献"],
                [(s["checked_at"], s["closed_model"]+" / "+s["open_model"],
                  f"{s['metrics']['signed_gap']:+.2f}%", s["metrics"]["state"],
                  f"{s['metrics']['score']:.2f}", f"{s['metrics']['contribution']:.2f}") for s in records]),
                unsafe_allow_html=True)
            for index, record in enumerate(records):
                with st.expander(f"记录{index + 1}：{record['closed_model']} / {record['open_model']} · {record['checked_at']}", expanded=False):
                    render_current_evidence(record, key_suffix=f"history_{index}")
            st.download_button("下载能力历史原始资料", json.dumps({"legacy": old, "records": records},
                ensure_ascii=False, indent=2), file_name="capability-history.json", mime="application/json")
            st.caption("历史保存在当前部署的本地文件中；重启同一目录可保留，但云端重建或清理临时磁盘可能丢失新增记录，请下载备份。")
