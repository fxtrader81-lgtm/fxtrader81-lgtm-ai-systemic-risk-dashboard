"""Quarterly current/history presentation for the system overview."""
from __future__ import annotations

from html import escape
import json

import streamlit as st

from components.protected_download import protected_download_button
from components.ui import evidence_table, model_evidence_panel


STATE_CN = {"SAFE": "安全", "WATCH": "观察", "WARNING": "警戒", "CRITICAL": "高风险", "N/A": "数据不足"}


def _score(value):
    return "N/A" if value is None else f"{value:.1f}"


def _state(value):
    return f"{value}（{STATE_CN.get(value, value)}）"


def _score_strip(snapshot, record_status):
    return (
        '<div class="energy-quarter-score-strip">'
        f'<div><span>结构总分</span><strong>{escape(_score(snapshot.get("score")))}/100</strong></div>'
        f'<div><span>总状态</span><strong>{escape(_state(snapshot.get("state", "N/A")))}</strong></div>'
        f'<div><span>记录状态</span><strong>{escape(record_status)}</strong></div>'
        '</div>'
    )


def _factor_rows(snapshot):
    rows = []
    for row in snapshot["factors"]:
        reading = "N/A · 数据不足" if row["score"] is None else f'{row["score"]:.1f}/100 · {row["state"]}'
        weight = "传导层（不计入总分）" if row["weight"] is None else f'{row["weight"]:.0%}'
        rows.append((f'{row["number"]} · {row["name"]}', row["role"], reading,
                     f'{row["coverage"]:.0f}%', weight, row["detail"]))
    return rows


def _factor_table_html(snapshot):
    rows = []
    for row in snapshot["factors"]:
        reading = "N/A" if row["score"] is None else f'{row["score"]:.1f} / {row["state"]}'
        weight = "传导层" if row["weight"] is None else f'{row["weight"]:.0%}'
        rows.append(
            "<tr>"
            f"<td>{escape(row['number'])} · {escape(row['name'])}</td>"
            f"<td>{escape(row['role'])}</td><td>{escape(reading)}</td>"
            f"<td>{row['coverage']:.0f}%</td><td>{escape(weight)}</td>"
            f"<td>{escape(row['detail'])}</td></tr>"
        )
    return ("<table><thead><tr><th>因子</th><th>检测职责</th><th>评分/状态</th><th>覆盖率</th>"
            "<th>结构权重</th><th>证据摘要</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def build_readable_report(current, records):
    sections = []
    for snapshot, label in [(current, "当前季度"), *[(record, "已归档历史") for record in records]]:
        period = f"截止{snapshot['period_end']}" if snapshot.get("period_end") else "进行中"
        sections.append(
            f"<section><h2>{escape(snapshot['quarter'])} · {period} · {label}</h2>"
            f"<div class='score'><b>结构总分：</b>{escape(_score(snapshot.get('score')))}/100　"
            f"<b>总状态：</b>{escape(_state(snapshot.get('state', 'N/A')))}　"
            f"<b>覆盖率：</b>{snapshot.get('coverage', 0):.0f}%</div>"
            f"<p>{escape(snapshot['summary'])}</p>{_factor_table_html(snapshot)}"
            f"<p class='note'>{escape(snapshot['caveat'])}</p></section>"
        )
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>系统风险总览季度历史</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;max-width:1280px;margin:36px auto;padding:0 24px;color:#172033;line-height:1.65}}h1{{font-size:30px}}h2{{margin-top:34px;border-bottom:2px solid #dbe6f3;padding-bottom:8px}}.score{{font-size:20px;background:#edf5ff;border-left:5px solid #2563eb;padding:14px 18px;margin:14px 0}}table{{width:100%;border-collapse:collapse;margin:14px 0}}th,td{{border:1px solid #ccd6e4;padding:9px;text-align:left;vertical-align:top}}th{{background:#eef3f9}}.note{{color:#667085}}@media(max-width:760px){{table{{display:block;overflow-x:auto}}}}</style></head><body>
<h1>系统风险总览｜季度历史与方法资料</h1><p>每季度只保留一条整页快照；日常刷新不追加历史。</p>{''.join(sections)}
<section><h2>口径</h2><ul><li>01–05是结构层，按25%/15%/20%/15%/25%汇总。</li><li>有效结构权重低于70%时总分N/A。</li><li>06、07仅作传导确认，不计入结构总分。</li></ul></section></body></html>"""


def render_dashboard_quarterly(current, records):
    with st.container(key="dashboard_quarterly_current"):
        with st.expander(
            f"{current['quarter']}进行中｜结构总分{_score(current['score'])} · {current['state']}｜七因子当前证据",
            expanded=False,
        ):
            st.markdown(_score_strip(current, "本季度进行中 · 尚未归档"), unsafe_allow_html=True)
            st.write(current["summary"])
            st.markdown(evidence_table(
                "📋 七个风险因子的当前证据",
                ["因子", "检测职责", "当前评分/状态", "覆盖率", "结构权重", "当前证据摘要"],
                _factor_rows(current),
                "06与07是传导确认层，不进入01–05结构总分。",
            ), unsafe_allow_html=True)
            st.caption(current["caveat"])
            st.markdown(model_evidence_panel(
                sample="历史审计包含19个领先压力信号起点；其5条正例归属2008、2020和2022三轮独立下跌，不是19次独立危机。",
                validation="2017年后21个重叠联合信号月中7个月份随后出现回调，表观比例33.3%；不作为预测概率。",
                boundary="07是市场传导/跌势确认，不是未来收益预测；06早期事件代理与当前HY OAS口径不同。",
                calibration="当前切点仍是探索性规则，尚未完成按历史发布版本的独立样本外校准。",
            ), unsafe_allow_html=True)

    with st.container(key="dashboard_quarterly_history"):
        latest = records[0] if records else None
        label = (f"季度历史快照｜最近归档{latest['quarter']} · 结构总分{_score(latest['score'])} · {latest['state']}"
                 if latest else "季度历史快照｜尚无归档")
        with st.expander(label, expanded=False):
            st.write("每季度只保留一条总览快照；页面刷新、行情更新或单项检查不会生成零散历史。")
            for record in records:
                st.markdown(f"### {record['quarter']} · 截止{record['period_end']} · 季度快照")
                st.markdown(_score_strip(record, "部分补录" if record["score"] is None else "季度归档"), unsafe_allow_html=True)
                st.write(record["summary"])
                st.markdown(evidence_table(
                    f"{record['quarter']}七因子状态",
                    ["因子", "检测职责", "评分/状态", "覆盖率", "结构权重", "归档摘要"],
                    _factor_rows(record),
                ), unsafe_allow_html=True)
                if record["score"] is None:
                    st.warning("该季度结构因子归档覆盖低于70%，不倒填当前数据，总分与总状态保留N/A。")
                st.caption(record["caveat"])

            payload = {
                "schema_version": 1,
                "history_policy": "每季度一条总览页级快照；刷新只更新当前季度。",
                "current": current,
                "quarterly_history": records,
            }
            st.markdown("**下载说明**：HTML用于直接阅读；JSON保留全部七因子证据摘要、来源、权重和历史。两种下载均需验证。")
            left, right = st.columns(2)
            with left:
                protected_download_button(
                    "下载可阅读版（HTML）", build_readable_report(current, records),
                    file_name="dashboard-quarterly-history.html", mime="text/html",
                    key="download_dashboard_quarterly_history_html", use_container_width=True,
                )
            with right:
                protected_download_button(
                    "下载完整原始资料（JSON）", json.dumps(payload, ensure_ascii=False, indent=2),
                    file_name="dashboard-quarterly-history.json", mime="application/json",
                    key="download_dashboard_quarterly_history_json", use_container_width=True,
                )
            st.caption("完整总览归档从2026Q4季末开始；历史快照冻结后不随日常刷新改写。")
