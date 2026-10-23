"""Current MLPerf system-efficiency evidence and retained legacy method."""
from datetime import date
from html import escape
import json

import streamlit as st

from components.protected_download import protected_download_button

from components.ui import evidence_table


def automatic_badge(snapshot, today=None):
    today = today or date.today()
    status = snapshot.get("auto_check", {})
    failed = status.get("status") == "failed"
    due = today >= date.fromisoformat(snapshot["next_review"])
    attention = failed or due
    if failed:
        label = "自动检查失败 · 保留上次实测"
    elif due:
        label = "已到自动检查期"
    else:
        label = f"自动检查 · 下次{snapshot['next_review']}"
    detail = status.get("message", "")
    css = "cost-maintenance cost-maintenance--attention" if attention else "cost-maintenance"
    return (f'<span class="{css}" title="{escape(detail, quote=True)}">'
            f'<span class="cost-maintenance__dot" aria-hidden="true"></span>{escape(label)}</span>')


def render_gpu_efficiency_evidence(snapshot, include_history=True):
    metrics = snapshot["metrics"]
    with st.container(key="infra_updates_gpu"):
        with st.expander("AI推理系统能效对冲｜本期实测与计算说明", expanded=False):
            st.caption(snapshot["auto_check"]["message"])
            st.write(
                f"本期采用MLPerf {snapshot['baseline_release']}的{snapshot['baseline_generation']}整机功耗结果，"
                f"连接{snapshot['target_release']}的{snapshot['target_generation']}整机功耗结果。"
                f"共有{metrics['pair_count']}组通过规则的同任务、同场景、同单位、同卡数配对。"
            )
            rows = []
            for pair in snapshot["comparisons"]:
                rows.append((
                    f"{pair['model']} · {pair['scenario']}",
                    f"{pair['baseline_efficiency']:.3f} {pair['performance_units']}/W",
                    f"{pair['target_efficiency']:.3f} {pair['performance_units']}/W",
                    f"{pair['gain']:.3f}×",
                ))
            st.markdown(evidence_table(
                "三组可比整机实测",
                ["任务/场景", f"{snapshot['baseline_generation']}性能/瓦",
                 f"{snapshot['target_generation']}性能/瓦", "能效提升"],
                rows,
            ), unsafe_allow_html=True)
            st.write(
                f"三组提升倍数中位数G={metrics['generation_gain']:.4f}×；"
                f"分项=100÷G={metrics['score']:.1f}分/{metrics['state']}；"
                f"按20%权重贡献{metrics['contribution']:.1f}分。"
            )
            st.write(snapshot["selection_policy"])
            st.write(snapshot["scope"])
            st.caption(f"证据强度：{snapshot['confidence']}。{snapshot['confidence_reason']}")
            st.caption("新公式表示完成同等基准工作所剩的相对能源强度；能效提升不会在2倍时把能源风险直接归零。")
            with st.expander("逐条系统、原始结果与官方来源", expanded=False):
                source_rows = []
                for pair in snapshot["comparisons"]:
                    for side_name, side in ((snapshot["baseline_generation"], pair["baseline"]),
                                            (snapshot["target_generation"], pair["target"])):
                        source_rows.append((
                            f"{pair['model']} · {pair['scenario']} · {side_name}",
                            side["system"],
                            f"性能{side['performance_result']:g} {pair['performance_units']} / 功耗{side['power_watts']:.1f}W",
                            f"[{side['release']} · {side['submitter']}]({side['source_url']})",
                        ))
                st.markdown(evidence_table("六条原始结果", ["配对", "整机系统", "原始结果", "来源"], source_rows),
                            unsafe_allow_html=True)
            with st.expander("最新MLPerf版本检查", expanded=False):
                st.markdown(evidence_table(
                    "最近官方版本",
                    ["版本", "总记录", "数据中心实测功耗记录", "检查结果"],
                    [(f"[{row['release']}]({row['source_url']})", row["total_rows"],
                      row["datacenter_measured_power_rows"], row["result"])
                     for row in snapshot["latest_source_checks"]],
                ), unsafe_allow_html=True)
                st.caption("v6.0/v6.1没有合格实测功耗时继续沿用最近一次有效结果；检查日期更新不冒充新的观测日期。")
        if include_history:
            with st.expander("AI推理系统能效对冲｜历史记录与原始资料", expanded=False):
                st.write("旧1.75倍及Rubin 2.4倍预测完整保留，但不再用于当前评分；新旧方法有断点，分数变化不能解释为市场突然变化。")
                for record in reversed(snapshot["history"]):
                    label = (f"{record['id']} · 当前实测方法" if record["kind"] == "measured_generation_link"
                             else f"{record['id']} · 旧静态方法")
                    with st.expander(label, expanded=False):
                        st.json(record)
                protected_download_button(
                    "下载GPU能效历史与原始资料",
                    json.dumps({"current": snapshot, "records": snapshot["history"]}, ensure_ascii=False, indent=2),
                    file_name="gpu-efficiency-history.json", mime="application/json", key="download_gpu_efficiency",
                )
