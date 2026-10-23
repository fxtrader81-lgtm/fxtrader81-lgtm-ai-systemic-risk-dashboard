"""Presentation helpers for Factor 04 counter signals."""
from __future__ import annotations

from html import escape
import json

import streamlit as st

from components.ui import evidence_table
from components.protected_download import protected_download_button


def review_banner(snapshot: dict) -> str:
    due_class = " counter-review-banner-due" if snapshot["review_due"] else ""
    return (
        f'<div class="counter-review-banner{due_class}">'
        '<span class="counter-review-dot" aria-hidden="true"></span>'
        '<div>'
        f'<b>{escape(snapshot["review_status"])}</b>'
        f'<span>{escape(snapshot["review_message"])}</span>'
        '</div></div>'
    )


def _capacity(project: dict) -> str:
    target = project.get("target_mw")
    near_term = project.get("near_term_mw")
    if target is None:
        return "N/A"
    if near_term is not None:
        return f"近期{near_term:g}MW / 目标上限{target:g}MW"
    return f"目标或项目容量{target:g}MW"


def _source_links(projects: list[dict]) -> str:
    links = []
    for project in projects:
        links.append(
            f'<a href="{escape(project["source_url"], quote=True)}" target="_blank">'
            f'{escape(project["source_name"])}</a>'
        )
        if project.get("verification_url"):
            links.append(
                f'<a href="{escape(project["verification_url"], quote=True)}" target="_blank">'
                f'{escape(project["project"])}监管核验</a>'
            )
    return '<div class="counter-source-links"><b>官方来源：</b>' + " · ".join(links) + "</div>"


def render_counter_evidence(snapshot: dict) -> None:
    label = f"反证模块｜{snapshot['reviewed_quarter']}人工核验项目与来源"
    with st.container(key="energy_counter_evidence"):
        with st.expander(label, expanded=False):
            st.write(snapshot["review_policy"])
            st.caption(snapshot["score_effect"])
            for key in ("overseas_ai_expansion", "dedicated_power_progress"):
                signal = snapshot["signals"][key]
                st.markdown(evidence_table(
                    signal["title"],
                    ["项目", "国家/公司", "容量口径", "项目阶段", "资料日期"],
                    [(
                        project["project"],
                        project.get("country") or project.get("company", "N/A"),
                        _capacity(project),
                        project["stage"],
                        project["source_date"],
                    ) for project in signal["projects"]],
                    note=snapshot["scope_policy"]["counter_a" if key == "overseas_ai_expansion" else "counter_c"],
                ), unsafe_allow_html=True)
                st.markdown(_source_links(signal["projects"]), unsafe_allow_html=True)
            protected_download_button(
                "下载反证项已核验资料（JSON）",
                json.dumps(snapshot, ensure_ascii=False, indent=2),
                file_name=f"factor04-counter-signals-{snapshot['reviewed_quarter'].lower()}.json",
                mime="application/json",
                key="download_energy_counter_signals",
            )
