"""Compact secondary explanation for the market page's four-level rating."""

from __future__ import annotations

from html import escape


def market_phase_note(phase: dict) -> str:
    current = escape(phase["label"])
    detail = escape(phase["detail"])
    return (
        '<div class="market-phase-note">'
        '<div class="market-phase-note-current">'
        f'<span class="market-phase-note-label">辅助阶段说明</span>'
        f'<strong>{current}</strong><span>{detail}</span></div>'
        '<div class="market-phase-note-scale">阶段口径：尚未出现市场传导 · 有传导，但市场尚未共振 · '
        '指标共振，风险释放中 · 风险压力消退，市场恢复中。仅描述当前市场表现。</div>'
        '</div>'
    )
