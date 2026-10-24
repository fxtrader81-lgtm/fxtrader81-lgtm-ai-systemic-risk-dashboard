"""Reusable quarterly current/history presentation for factor detail pages."""
from __future__ import annotations

from html import escape
import json

import streamlit as st

from components.protected_download import protected_download_button
from components.ui import evidence_table


STATE_CN = {"SAFE": "安全", "WATCH": "观察", "WARNING": "警戒", "CRITICAL": "高风险", "N/A": "不可用"}


def _score(value):
    return "N/A" if value is None else f"{value:.1f}"


def _state(value):
    return f"{value}（{STATE_CN.get(value, value)}）"


def _record_type_label(record):
    kind = record.get("record_type", "")
    if kind.startswith("reconstructed_"):
        return "版本化复算"
    if kind.startswith("backfilled"):
        return "补录上一版页面状态"
    return "季度归档"


def _score_strip(score, state, record_status):
    return (
        '<div class="energy-quarter-score-strip">'
        f'<div><span>总得分</span><strong>{escape(_score(score))}/100</strong></div>'
        f'<div><span>状态</span><strong>{escape(_state(state))}</strong></div>'
        f'<div><span>记录状态</span><strong>{escape(record_status)}</strong></div>'
        '</div>'
    )


def _component_rows(snapshot, value_label="当期显示"):
    return [
        (row["name"], row["display_value"], _score(row["score"]), f"{row['weight']:.0%}",
         _score(row["contribution"]), row["observation_period"])
        for row in snapshot["components"]
    ], ["指标", value_label, "分项评分", "权重", "加权贡献", "数据观察期"]


def _components_html(snapshot):
    rows = "".join(
        "<tr>"
        f"<td>{escape(row['name'])}</td><td>{escape(str(row['display_value']))}</td>"
        f"<td>{escape(_score(row['score']))}</td><td>{row['weight']:.0%}</td>"
        f"<td>{escape(_score(row['contribution']))}</td><td>{escape(str(row['observation_period']))}</td>"
        "</tr>"
        for row in snapshot["components"]
    )
    return ("<table><thead><tr><th>指标</th><th>当期显示</th><th>分项评分</th><th>权重</th>"
            "<th>加权贡献</th><th>数据观察期</th></tr></thead><tbody>" + rows + "</tbody></table>")


def build_readable_report(page_number, page_title, current, records, method_summary):
    current_score = "N/A" if current["score"] is None else f"{current['score']:.1f}/100"
    history = "".join(
        f"<section><h2>{escape(record['quarter'])} · 截止{escape(record['period_end'])}</h2>"
        f"<div class='score'><b>总得分：</b>{record['score']:.1f}/100　<b>状态：</b>{escape(_state(record['state']))}</div>"
        f"<p>{escape(record['summary'])}</p>{_components_html(record)}"
        f"<p class='note'>{escape(record['caveat'])}</p></section>"
        for record in records
    )
    notes = "".join(f"<li>{escape(note)}</li>" for note in method_summary)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{escape(page_number)}页季度历史与方法资料</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;max-width:1180px;margin:36px auto;padding:0 24px;color:#172033;line-height:1.65}}
h1{{font-size:30px}}h2{{margin-top:34px;border-bottom:2px solid #dbe6f3;padding-bottom:8px}}
.score{{font-size:20px;background:#edf5ff;border-left:5px solid #2563eb;padding:14px 18px;margin:14px 0}}
table{{width:100%;border-collapse:collapse;margin:14px 0}}th,td{{border:1px solid #ccd6e4;padding:9px;text-align:left;vertical-align:top}}th{{background:#eef3f9}}
.note{{color:#667085}}@media(max-width:760px){{body{{margin:18px auto}}table{{display:block;overflow-x:auto}}}}
</style></head><body>
<h1>{escape(page_number)} · {escape(page_title)}｜季度历史与方法资料</h1>
<p>可阅读版导出。当前季度是进行中状态；历史季度冻结后不随页面刷新改变。</p>
<section><h2>{escape(current['quarter'])}进行中</h2>
<div class="score"><b>本季总得分：</b>{escape(current_score)}　<b>状态：</b>{escape(_state(current['state']))}</div>
<p>{escape(current['summary'])}</p>{_components_html(current)}<p class="note">{escape(current['caveat'])}</p></section>
{history}
<section><h2>方法与原始资料说明</h2><ul>{notes}</ul>
<p class="note">完整逐项原始输入、旧方法和既有采集记录保存在同组JSON下载中。</p></section>
</body></html>"""


def render_current_quarter(snapshot, *, container_key):
    with st.container(key=container_key):
        label = f"{snapshot['quarter']}进行中｜总分{_score(snapshot['score'])} · {snapshot['state']}｜当前四项与计算说明"
        with st.expander(label, expanded=False):
            st.markdown(_score_strip(snapshot["score"], snapshot["state"], "本季度进行中 · 尚未归档"), unsafe_allow_html=True)
            st.write(snapshot["summary"])
            rows, headers = _component_rows(snapshot)
            st.markdown(evidence_table("本季度当前状态（尚未归档）", headers, rows), unsafe_allow_html=True)
            if snapshot["score"] is None:
                st.warning("必要分项缺失，当前季度整页总分为N/A；不补后备分、不重分配权重。")
            else:
                st.write(f"当前整页总分={snapshot['score']:.1f} / {snapshot['state']}。这是进行中状态，会随来源刷新，不写入历史。")
            st.caption(snapshot["caveat"])


def render_quarterly_history(records, current, legacy_evidence, *, container_key, page_number,
                             page_title, file_prefix, method_summary):
    with st.container(key=container_key):
        latest = records[0] if records else None
        label = (f"季度历史快照｜最近归档{latest['quarter']} · 总分{_score(latest['score'])} · {latest['state']}"
                 if latest else "季度历史快照｜尚无归档")
        with st.expander(label, expanded=False):
            st.write(f"每季度只保留一条{page_number}页面快照；页面刷新、行情更新或单项检查不会产生零散历史记录。")
            for record in records:
                record_type = _record_type_label(record)
                st.markdown(f"### {record['quarter']} · 截止{record['period_end']} · {record_type}")
                st.markdown(_score_strip(record["score"], record["state"], record_type), unsafe_allow_html=True)
                st.write(f"归档总得分{record['score']:.1f}/100，状态{_state(record['state'])}（页面整数显示{record['display_score']}）。{record['summary']}")
                rows, headers = _component_rows(record, "当期显示")
                st.markdown(evidence_table(f"{record['quarter']}四项状态", headers, rows), unsafe_allow_html=True)
                st.caption(record["caveat"])
            payload = {
                "schema_version": 1,
                "history_policy": "每季度一条页面级快照；刷新只更新当前季度，不追加历史。",
                "current": current,
                "quarterly_history": records,
                "method_summary": method_summary,
                "legacy_method_evidence": legacy_evidence,
            }
            st.markdown("**下载说明**：HTML用于直接阅读；JSON保留完整原始输入、旧方法与既有采集记录。两种下载均需验证。")
            readable = build_readable_report(page_number, page_title, current, records, method_summary)
            readable_col, raw_col = st.columns(2)
            with readable_col:
                protected_download_button(
                    "下载可阅读版（HTML）", readable,
                    file_name=f"{file_prefix}-quarterly-history.html", mime="text/html",
                    key=f"download_{file_prefix}_quarterly_history_html", use_container_width=True,
                )
            with raw_col:
                protected_download_button(
                    "下载完整原始资料（JSON）", json.dumps(payload, ensure_ascii=False, indent=2),
                    file_name=f"{file_prefix}-quarterly-history.json", mime="application/json",
                    key=f"download_{file_prefix}_quarterly_history_json", use_container_width=True,
                )
            st.caption("旧版分项资料仍随统一JSON保留，但不再分别冒充季度趋势。未来口径变化建立新方法版本，不覆盖已归档季度。")
