"""Shared presentation for observed credit-to-market transmission stages."""

from __future__ import annotations

from html import escape

from components.ui import panel


def market_phase_card(phase: dict, score: float | None, grade: str, coverage: int) -> str:
    """Explain the observed phase below the primary four-level rating."""
    phases = (
        ("quiet", "尚未出现市场传导"), ("transmitting", "有传导，但市场尚未共振"),
        ("release", "指标共振，风险释放中"), ("dissipating", "风险压力消退，市场恢复中"),
    )
    steps = "".join(
        f'<div class="market-phase-step{" active" if key == phase["key"] else ""}">{escape(label)}</div>'
        for key, label in phases
    )
    score_text = "N/A" if score is None else f"{score:.1f}/100"
    return (
        '<div class="market-phase-card">'
        '<div class="market-phase-kicker">辅助阶段解释</div>'
        f'<div class="market-phase-title">{escape(phase["label"])}</div>'
        f'<div class="market-phase-detail">{escape(phase["detail"])}</div>'
        f'<div class="market-phase-steps">{steps}</div>'
        f'<div class="market-phase-meta">对应评分 {escape(score_text)} · 四级评级 {escape(grade)} · '
        f'有效数据覆盖 {coverage}% · 阶段仅描述当前市场表现</div></div>'
    )


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
