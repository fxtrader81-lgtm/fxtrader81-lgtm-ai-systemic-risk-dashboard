"""Factor 05 — structural AI financing vulnerability model.

Market pricing belongs to factor 06. This model intentionally contains only
slow-moving, filing-based structure and linked collateral vulnerability.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


WEIGHTS = {
    "term_mismatch": 0.35,
    "capital_loop": 0.25,
    "securitization": 0.20,
    "collateral": 0.20,
}

STATIC_INPUTS = {
    "customer_contract_wal_years": 4.0,
    "gpu_accounting_life_years": 6.0,
    "representative_lease_years": 15.0,
    "securitization_ard_years": 5.0,
    "securitization_final_maturity_years": 27.5,
    "nvidia_stack_dependency": True,
    "equity_supplier_overlap": True,
    "capacity_backstop": True,
    "credit_support_or_extended_terms": True,
    "as_of": "2026-Q2",
}

SOURCES = [
    {
        "item": "CoreWeave 客户合同、GPU寿命与资产级融资",
        "period": "FY2025 / 2026 filing",
        "cadence": "季度",
        "url": "https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm",
        "note": "合同通常2–5年（加权约4年）；设备会计寿命6年；资产级债务由take-or-pay合同支持。",
    },
    {
        "item": "NVIDIA 投资与信用支持",
        "period": "2026-Q2",
        "cadence": "季度",
        "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm",
        "note": "延长付款、信用支持/担保及容量购买承诺；不等同于任何单一项目已全部触发。",
    },
    {
        "item": "Helios 租约与剩余容量兜底",
        "period": "2026-07",
        "cadence": "事件驱动",
        "url": "https://www.sec.gov/Archives/edgar/data/1859392/000185939226000068/launch8-kexhibit99172226.htm",
        "note": "15年基础租约；NVIDIA持股并对剩余容量提供上限约63亿美元的购买安排。",
    },
    {
        "item": "数据中心证券化期限结构（行业样本）",
        "period": "2026-07",
        "cadence": "年度复核",
        "url": "https://www.sec.gov/files/corpfin/no-action/dcs-interp-letter-072326.pdf",
        "note": "行业函件描述约5年预期偿还、25–30年法定最终到期；它不是SEC规则或风险认定。",
    },
]


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def state_for(score: float | None) -> str:
    if score is None:
        return "N/A"
    if score < 25:
        return "SAFE"
    if score < 50:
        return "WATCH"
    if score < 75:
        return "WARNING"
    return "CRITICAL"


def term_mismatch_score(inputs: dict = STATIC_INPUTS) -> tuple[float, list[dict]]:
    contract = inputs["customer_contract_wal_years"]
    gpu_life = inputs["gpu_accounting_life_years"]
    lease = inputs["representative_lease_years"]
    ard = inputs["securitization_ard_years"]
    final = inputs["securitization_final_maturity_years"]
    signals = [
        {"name": "合同覆盖GPU寿命缺口", "weight": 0.45, "score": clamp((gpu_life - contract) / contract * 100)},
        {"name": "客户合同与设施租约错配", "weight": 0.35, "score": clamp((lease - contract) / lease * 100)},
        {"name": "预期偿还与法定到期尾部", "weight": 0.20, "score": clamp((final - ard) / final * 100)},
    ]
    score = sum(row["weight"] * row["score"] for row in signals)
    return round(score, 1), signals


def capital_loop_score(inputs: dict = STATIC_INPUTS) -> tuple[float, list[dict]]:
    # Scores express the intensity of a documented dependency channel, not a
    # claim that the full contingent exposure has already crystallised.
    signals = [
        {"name": "单一GPU技术栈依赖", "weight": 0.35, "score": 100 if inputs["nvidia_stack_dependency"] else 0},
        {"name": "股东与供应商角色重叠", "weight": 0.30, "score": 80 if inputs["equity_supplier_overlap"] else 0},
        {"name": "剩余容量兜底/购买安排", "weight": 0.20, "score": 85 if inputs["capacity_backstop"] else 0},
        {"name": "延长付款或信用支持", "weight": 0.15, "score": 70 if inputs["credit_support_or_extended_terms"] else 0},
    ]
    score = sum(row["weight"] * row["score"] for row in signals)
    return round(score, 1), signals


@st.cache_data(ttl=3600, show_spinner=False)
def load_straw5_analysis(dcoi_score: float | None) -> dict:
    term_score, term_signals = term_mismatch_score()
    loop_score, loop_signals = capital_loop_score()
    structural_score = 62.0

    weighted_parts = [
        (0.35, term_score, "term_mismatch"),
        (0.25, loop_score, "capital_loop"),
        (0.20, structural_score, "securitization_structure"),
    ]
    if dcoi_score is not None:
        weighted_parts.append((0.20, clamp(dcoi_score), "collateral"))

    coverage = sum(weight for weight, _, _ in weighted_parts)
    raw_score = sum(weight * score for weight, score, _ in weighted_parts) / coverage if coverage else None
    score = round(raw_score, 1) if raw_score is not None and coverage >= 0.50 else None
    confidence = "NORMAL" if coverage >= 0.75 else "LOW CONFIDENCE" if coverage >= 0.50 else "INSUFFICIENT"

    return {
        "score": score,
        "state": state_for(score),
        "coverage": round(coverage * 100),
        "confidence": confidence,
        "components": {
            "term_mismatch": {"score": term_score, "weight": 0.35, "available": True, "signals": term_signals},
            "capital_loop": {"score": loop_score, "weight": 0.25, "available": True, "signals": loop_signals},
            "securitization": {
                "score": structural_score,
                "weight": 0.20,
                "available": True,
                "structural_score": structural_score,
            },
            "collateral": {"score": dcoi_score, "weight": 0.20, "available": dcoi_score is not None},
        },
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
