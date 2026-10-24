"""Quarterly page snapshots for Factor 05 (AI financing vulnerability)."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path

from core.quarterly_history import component, load_history as _load_history, quarter_for
from core.straw5_engine import STATIC_INPUTS, WEIGHTS, state_for


CONFIG = Path(__file__).resolve().parents[1] / "config/financing_quarterly_history.json"


def _display(score):
    return "N/A" if score is None else f"{score:.1f}/100"


def make_current_snapshot(analysis, today=None):
    """Build the in-progress page snapshot from the already loaded AFVI analysis."""
    today = today or date.today()
    source = analysis.get("components", {})
    term = source.get("term_mismatch", {})
    loop = source.get("capital_loop", {})
    securitization = source.get("securitization", {})
    collateral = source.get("collateral", {})
    components = [
        component(
            "term_mismatch", "期限错配", term.get("score"),
            (f"{STATIC_INPUTS['customer_contract_wal_years']:g}y合同 / "
             f"{STATIC_INPUTS['gpu_accounting_life_years']:g}y GPU / "
             f"{STATIC_INPUTS['representative_lease_years']:g}y租约"),
            f"公司披露至{STATIC_INPUTS['as_of']}；行业样本2026-07；本季待人工复核",
            {"inputs": STATIC_INPUTS, "signals": term.get("signals", [])}, WEIGHTS,
        ),
        component(
            "capital_loop", "资本闭环依赖", loop.get("score"),
            "4/4依赖渠道已观察",
            "NVIDIA 2026-Q2；Helios 2026-07；本季待人工复核",
            {"inputs": STATIC_INPUTS, "signals": loop.get("signals", [])}, WEIGHTS,
        ),
        component(
            "securitization", "证券化与契约结构", securitization.get("score"),
            (f"{STATIC_INPUTS['securitization_ard_years']:g}y预期偿还 / "
             f"{STATIC_INPUTS['securitization_final_maturity_years']:g}y法定到期"),
            "2026-07行业函件；本季待人工复核",
            {"structural_score": securitization.get("structural_score")}, WEIGHTS,
        ),
        component(
            "collateral", "抵押品脆弱度", collateral.get("score"),
            _display(collateral.get("score")),
            f"引用03页当前DCOI；AFVI读取{analysis.get('as_of', '未知')}",
            {"factor": "03", "dcoi_score": collateral.get("score")}, WEIGHTS,
        ),
    ]
    quarter = quarter_for(today)
    missing = [row["name"] for row in components if row["score"] is None]
    score = analysis.get("score")
    return {
        "id": f"financing-page-{quarter.lower()}-current",
        "quarter": quarter,
        "period_end": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "record_type": "current_in_progress",
        "method_version": "afvi-structure-v2",
        "score": score,
        "display_score": None if score is None else round(score),
        "state": analysis.get("state", state_for(score)),
        "components": components,
        "summary": (f"{quarter}进行中；前三项为慢变披露并待季度人工复核，抵押品分项随03页刷新。"
                    if not missing else f"{quarter}进行中；缺少：{'、'.join(missing)}。"),
        "caveat": "当前季度不写入历史。前三项只在新披露改变证据时调整；跨季后必须人工复核再归档。",
    }


def load_history(path=None):
    return _load_history(path or CONFIG, WEIGHTS, cutoffs=(25, 50, 75))


def load_archive_metadata(path=None):
    payload = json.loads(Path(path or CONFIG).read_text(encoding="utf-8"))
    return {
        "method_notes": payload.get("method_notes", []),
        "legacy_method_evidence": payload.get("legacy_method_evidence", {}),
    }
