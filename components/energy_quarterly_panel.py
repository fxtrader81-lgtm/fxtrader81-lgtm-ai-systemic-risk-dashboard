"""Unified current-quarter and archived-quarter presentation for Factor 04."""
from html import escape
import json

import streamlit as st

from components.ui import evidence_table
from components.protected_download import protected_download_button


def _score(value):
    return "N/A" if value is None else f"{value:.1f}"


STATE_CN = {"SAFE": "安全", "WATCH": "观察", "WARNING": "警戒", "CRITICAL": "危急", "N/A": "缺少数据"}


def _state(value):
    return f"{value}（{STATE_CN.get(value, value)}）"


def _score_strip(score, state, record_status):
    score_text = "N/A" if score is None else f"{score:.1f}/100"
    return (
        '<div class="energy-quarter-score-strip">'
        f'<div><span>总得分</span><strong>{escape(score_text)}</strong></div>'
        f'<div><span>状态</span><strong>{escape(_state(state))}</strong></div>'
        f'<div><span>记录状态</span><strong>{escape(record_status)}</strong></div>'
        '</div>'
    )


def _components_html(snapshot):
    rows = "".join(
        "<tr>"
        f"<td>{escape(row['name'])}</td>"
        f"<td>{escape(str(row['display_value']))}</td>"
        f"<td>{escape(_score(row['score']))}</td>"
        f"<td>{row['weight']:.0%}</td>"
        f"<td>{escape(_score(row['contribution']))}</td>"
        f"<td>{escape(str(row['observation_period']))}</td>"
        "</tr>"
        for row in snapshot["components"]
    )
    return (
        "<table><thead><tr><th>指标</th><th>当期显示</th><th>分项评分</th>"
        "<th>权重</th><th>加权贡献</th><th>数据观察期</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


_FIELD_LABELS = {
    "id": "资料版本", "quarter": "季度", "period": "资料期间", "period_end": "季度截止日",
    "captured_on": "归档日", "captured_at": "生成时间", "record_type": "记录类型",
    "method_version": "方法版本", "score": "得分", "state": "状态", "summary": "摘要",
    "caveat": "限制", "classification": "资料性质", "reviewed_on": "核验日",
    "recorded_period": "记录期间", "adopted_at": "采纳时间", "available": "是否可用",
    "method": "方法", "selection_policy": "样本规则", "aggregation_policy": "汇总规则",
    "scoring_policy": "评分规则", "missing_reason": "缺口", "source_url": "来源链接",
    "source_title": "来源名称", "observation_period": "观察期", "display_value": "显示值",
    "weight": "权重", "contribution": "加权贡献", "components": "四项指标", "raw": "原始输入",
}


def _nested_html(value):
    """Turn retained method evidence into a browser-readable document."""
    if isinstance(value, dict):
        body = "".join(
            "<tr>"
            f"<th>{escape(_FIELD_LABELS.get(str(key), str(key)))}</th>"
            f"<td>{_nested_html(item)}</td>"
            "</tr>"
            for key, item in value.items()
        )
        return f"<table class='nested'><tbody>{body}</tbody></table>"
    if isinstance(value, list):
        if not value:
            return "<span class='muted'>无记录</span>"
        return "".join(f"<div class='list-item'>{_nested_html(item)}</div>" for item in value)
    if value is None:
        return "<span class='muted'>N/A</span>"
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value)
    if text.startswith(("https://", "http://")):
        safe = escape(text, quote=True)
        return f"<a href='{safe}'>{safe}</a>"
    return escape(text)


def build_readable_report(current, records, legacy_evidence):
    current_score = "N/A" if current["score"] is None else f"{current['score']:.1f}/100"
    history_sections = []
    for record in records:
        history_sections.append(
            f"<section><h2>{escape(record['quarter'])} · 截止{escape(record['period_end'])}</h2>"
            f"<div class='score'><b>总得分：</b>{record['score']:.1f}/100　"
            f"<b>状态：</b>{escape(_state(record['state']))}</div>"
            f"<p>{escape(record['summary'])}</p>{_components_html(record)}"
            f"<p class='note'>{escape(record['caveat'])}</p></section>"
        )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>04页季度历史与方法资料</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;max-width:1180px;margin:36px auto;padding:0 24px;color:#172033;line-height:1.65}}
h1{{font-size:30px}}h2{{margin-top:34px;border-bottom:2px solid #dbe6f3;padding-bottom:8px}}
.score{{font-size:20px;background:#edf5ff;border-left:5px solid #2563eb;padding:14px 18px;margin:14px 0}}
table{{width:100%;border-collapse:collapse;margin:14px 0}}th,td{{border:1px solid #ccd6e4;padding:9px;text-align:left;vertical-align:top}}th{{background:#eef3f9}}
table.nested th{{width:180px}}.list-item{{margin:10px 0;padding:10px;border:1px solid #d9e2ef;border-radius:8px}}.note,.muted{{color:#667085}}
details{{margin:16px 0;border:1px solid #ccd6e4;border-radius:8px;padding:12px}}summary{{cursor:pointer;font-size:18px;font-weight:700}}
a{{color:#145fc1;overflow-wrap:anywhere}}@media(max-width:760px){{body{{margin:18px auto}}table{{display:block;overflow-x:auto}}}}
</style></head><body>
<h1>04 · AI能源约束｜季度历史与方法资料</h1>
<p>可阅读版导出。当前季度是进行中状态；历史季度冻结后不随页面刷新改变。</p>
<section><h2>{escape(current['quarter'])}进行中</h2>
<div class="score"><b>本季总得分：</b>{escape(current_score)}　<b>状态：</b>{escape(_state(current['state']))}</div>
<p>{escape(current['summary'])}</p>{_components_html(current)}<p class="note">{escape(current['caveat'])}</p></section>
{''.join(history_sections)}
<section><h2>旧版方法与原始证据</h2><p class="note">以下资料用于追溯旧口径，不冒充季度实测趋势。</p>
<details><summary>展开完整方法资料</summary>{_nested_html(legacy_evidence)}</details></section>
</body></html>"""


def render_current_quarter(snapshot):
    with st.container(key="energy_quarterly_current"):
        label = f"{snapshot['quarter']}进行中｜总分{_score(snapshot['score'])} · {snapshot['state']}｜当前四项与计算说明"
        with st.expander(label, expanded=False):
            st.markdown(_score_strip(snapshot["score"], snapshot["state"], "本季度进行中 · 尚未归档"), unsafe_allow_html=True)
            st.write(snapshot["summary"])
            st.markdown(evidence_table(
                "本季度当前状态（尚未归档）",
                ["指标", "当前值", "分项评分", "权重", "加权贡献", "数据观察期"],
                [(row["name"], row["display_value"], _score(row["score"]),
                  f"{row['weight']:.0%}", _score(row["contribution"]), row["observation_period"])
                 for row in snapshot["components"]],
            ), unsafe_allow_html=True)
            if snapshot["score"] is None:
                st.warning("必要分项缺失，当前季度完整ESRI为N/A；不补后备分、不重分配权重。")
            else:
                st.write(f"当前ESRI={snapshot['score']:.1f} / {snapshot['state']}。这是进行中状态，会随来源刷新，不写入历史。")
            st.caption(snapshot["caveat"])


def render_quarterly_history(records, current, legacy_evidence):
    with st.container(key="energy_quarterly_history"):
        latest = records[0] if records else None
        label = (f"季度历史快照｜最近归档{latest['quarter']} · 总分{_score(latest['score'])} · {latest['state']}"
                 if latest else "季度历史快照｜尚无归档")
        with st.expander(label, expanded=False):
            st.write("每季度只保留一条04页面快照；不因行情刷新、来源检查或单项复核产生零散历史记录。")
            for record in records:
                record_type = "补录基准" if record["record_type"].startswith("backfilled") else "季度归档"
                st.markdown(f"### {record['quarter']} · 截止{record['period_end']} · {record_type}")
                st.markdown(_score_strip(record["score"], record["state"], record_type), unsafe_allow_html=True)
                st.write(f"归档总得分{record['score']:.1f}/100，状态{_state(record['state'])}（页面整数显示{record['display_score']}）。{record['summary']}")
                st.markdown(evidence_table(
                    f"{record['quarter']}四项状态",
                    ["指标", "当期显示", "分项评分", "权重", "加权贡献", "原始观察期"],
                    [(row["name"], row["display_value"], _score(row["score"]),
                      f"{row['weight']:.0%}", _score(row["contribution"]), row["observation_period"])
                     for row in record["components"]],
                ), unsafe_allow_html=True)
                st.caption(record["caveat"])
            payload = {
                "schema_version": 1,
                "history_policy": "每季度一条页面级快照；刷新只更新当前季度，不追加历史。",
                "current": current,
                "quarterly_history": records,
                "legacy_method_evidence": legacy_evidence,
            }
            st.markdown("**下载说明**：优先下载HTML可阅读版，双击后会用浏览器打开；JSON是完整原始备份，供程序读取或用文本编辑器打开。")
            readable = build_readable_report(current, records, legacy_evidence)
            readable_col, raw_col = st.columns(2)
            with readable_col:
                protected_download_button(
                    "下载可阅读版（HTML）",
                    readable,
                    file_name="factor04-energy-quarterly-history.html",
                    mime="text/html",
                    key="download_energy_quarterly_history_html",
                    use_container_width=True,
                )
            with raw_col:
                protected_download_button(
                    "下载完整原始资料（JSON）",
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    file_name="factor04-energy-quarterly-history.json",
                    mime="application/json",
                    key="download_energy_quarterly_history_json",
                    use_container_width=True,
                )
            st.caption("旧版分项资料仍随统一下载保留，但不再分别冒充季度趋势。未来口径变化建立新方法版本，不覆盖已归档季度。")
