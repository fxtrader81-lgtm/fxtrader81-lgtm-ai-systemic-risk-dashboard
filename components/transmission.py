"""Shared presentation for observed credit-to-market transmission stages."""

from __future__ import annotations

from html import escape

from components.ui import panel


def transmission_chain_panel(phase: str, nodes: tuple[bool, bool, bool, bool]) -> str:
    """Show the four observable legs of the 05–06–07 cascade at a glance."""
    labels = ("05 结构脆弱", "06 信贷压力", "07 市场确认", "风险释放")
    items = "".join(
        f'<div class="transmission-node{" active" if active else ""}">'
        f'<span>{"●" if active else "○"}</span>{escape(label)}</div>'
        for label, active in zip(labels, nodes)
    )
    return panel(
        "结构—信贷—市场传导链",
        f'<div class="transmission-chain">{items}</div>'
        f'<div class="transmission-status">当前阶段：{escape(phase)}。'
        '节点是当前状态快照；没有验证连续触发顺序，也不是股市下跌概率。</div>',
        extra_class="transmission-panel",
    )
