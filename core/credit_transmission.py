"""Issuer-level disclosure extraction for the unscored credit-transmission view.

SEC companyfacts contains entity-wide standardized facts, not every custom,
segment, or AI-specific disclosure.  Missing fields remain missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import os
from typing import Any

import requests
import streamlit as st


ISSUERS = {
    "MSFT": ("Microsoft", 789019),
    "AMZN": ("Amazon", 1018724),
    "GOOGL": ("Alphabet", 1652044),
    "META": ("Meta", 1326801),
    "ORCL": ("Oracle", 1341439),
}

SEC_API = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
TAGS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "cash_capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
    "operating_income": ("OperatingIncomeLoss",),
    "pretax_income": (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
    ),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "interest_expense": ("InterestExpense", "InterestExpenseNonOperating"),
    "debt_proceeds": ("ProceedsFromIssuanceOfLongTermDebt", "ProceedsFromIssuanceOfDebt"),
    "debt_repayments": ("RepaymentsOfLongTermDebt", "RepaymentsOfDebt"),
    "rpo": ("RevenueRemainingPerformanceObligation",),
    "finance_lease_additions": ("RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability",),
}
FLOW_FIELDS = tuple(key for key in TAGS if key != "rpo")


@dataclass(frozen=True)
class Fact:
    value: float
    end: str
    filed: str
    accession: str
    tags: tuple[str, ...]
    kind: str = "公司确认披露"
    method: str = "SEC XBRL 原值"


def sec_url(symbol: str) -> str:
    return SEC_API.format(cik=ISSUERS[symbol][1])


@st.cache_data(ttl=86400, show_spinner=False)
def load_companyfacts(symbol: str) -> tuple[dict[str, Any], str]:
    """Fetch one issuer on demand; cached facts are labelled by retrieval time."""
    if symbol not in ISSUERS:
        raise ValueError("Unsupported issuer")
    agent = os.getenv("SEC_USER_AGENT") or (
        "ComputeDollarRiskDashboard/1.0 "
        "(+https://github.com/fxtrader81-lgtm/fxtrader81-lgtm-ai-systemic-risk-dashboard)"
    )
    response = requests.get(
        sec_url(symbol), headers={"User-Agent": agent, "Accept": "application/json"}, timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("facts"), dict):
        raise ValueError("SEC companyfacts response is invalid")
    return payload, datetime.now(timezone.utc).isoformat(timespec="seconds")


def _raw_facts(payload: dict, tags: tuple[str, ...]) -> list[dict]:
    gaap = payload.get("facts", {}).get("us-gaap", {})
    candidates = []
    for tag in tags:  # one taxonomy concept per metric; never add aliases together
        units = gaap.get(tag, {}).get("units", {})
        records = units.get("USD", [])
        valid = [
            {**row, "tag": tag} for row in records
            if row.get("form") in {"10-Q", "10-K"}
            and isinstance(row.get("val"), (int, float))
            and isinstance(row.get("end"), str)
            and isinstance(row.get("filed"), str)
            and isinstance(row.get("accn"), str)
        ]
        if valid:
            candidates.append(valid)
    # Prefer the concept with the newest observation, then the configured
    # precedence. An obsolete first-choice tag must not hide a current alias.
    return max(candidates, key=lambda rows: max(row["end"] for row in rows)) if candidates else []


def _days(row: dict) -> int | None:
    try:
        return (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days + 1
    except (KeyError, ValueError, TypeError):
        return None


def _latest(rows: list[dict]) -> dict | None:
    return max(rows, key=lambda row: (row["filed"], row["accn"])) if rows else None


def _make_fact(row: dict, *, value: float | None = None, prior: dict | None = None) -> Fact:
    if prior is None:
        return Fact(float(row["val"] if value is None else value), row["end"], row["filed"], row["accn"], (row["tag"],))
    return Fact(
        float(value), row["end"], max(row["filed"], prior["filed"]), row["accn"],
        (row["tag"],), "根据确认数据计算", "本期累计值－上期累计值；两个申报期的差额",
    )


def quarterly_fact(rows: list[dict], end: str) -> Fact | None:
    """Prefer reported quarter; derive YTD-only cash flows only with same FY start."""
    at_end = [row for row in rows if row["end"] == end and _days(row) is not None]
    direct = _latest([row for row in at_end if 65 <= _days(row) <= 120])
    if direct:
        return _make_fact(direct)
    cumulative = _latest([row for row in at_end if 121 <= _days(row) <= 385])
    if cumulative is None:
        return None
    previous = _latest([
        row for row in rows
        if row.get("start") == cumulative.get("start")
        and row["end"] < end
        and 65 <= (date.fromisoformat(end) - date.fromisoformat(row["end"])).days <= 120
        and _days(row) is not None
        and _days(row) < _days(cumulative)
    ])
    if previous is None:
        return None
    return _make_fact(cumulative, value=cumulative["val"] - previous["val"], prior=previous)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def derived_metrics(values: dict[str, float | None]) -> dict[str, float | None]:
    """Never turn absent filings into zero; financing is not attributed to AI."""
    ocf, capex, revenue = (values.get(key) for key in ("operating_cash_flow", "cash_capex", "revenue"))
    issued, repaid = values.get("debt_proceeds"), values.get("debt_repayments")
    gap = max(capex - ocf, 0) if capex is not None and ocf is not None else None
    net_debt = issued - repaid if issued is not None and repaid is not None else None
    return {
        "capex_coverage": _ratio(ocf, capex),
        "cash_capex_gap": gap,
        "gap_share": _ratio(gap, capex),
        "net_debt_financing": net_debt,
        "net_debt_to_capex": _ratio(net_debt, capex),
        "capex_intensity": _ratio(capex, revenue),
        "simple_fcf": ocf - capex if ocf is not None and capex is not None else None,
    }


def _ttm(quarters: list[dict], field: str) -> float | None:
    if len(quarters) < 4:
        return None
    four = quarters[:4]
    ends = [date.fromisoformat(row["end"]) for row in four]
    if any(not 65 <= (ends[i] - ends[i + 1]).days <= 120 for i in range(3)):
        return None
    values = [row["values"].get(field) for row in four]
    return sum(values) if all(value is not None for value in values) else None


def disclosure_age_label(end: str | None, *, today: date | None = None) -> str:
    """Operational freshness label, never a credit-risk threshold."""
    if not end:
        return "所属期间不可得"
    age = ((today or date.today()) - date.fromisoformat(end)).days
    return f"过期提示：期末距今 {age} 天" if age > 180 else f"期末距今 {age} 天"


def build_company_snapshot(payload: dict, symbol: str, retrieved_at: str) -> dict:
    """Produce comparable quarter/TTM observations and explicit coverage."""
    if symbol not in ISSUERS:
        raise ValueError("Unsupported issuer")
    source = sec_url(symbol)
    records = {key: _raw_facts(payload, tags) for key, tags in TAGS.items()}
    candidate_ends = sorted({
        row["end"] for key in ("revenue", "operating_cash_flow", "cash_capex")
        for row in records[key] if _days(row) is not None
    }, reverse=True)
    quarters = []
    for end in candidate_ends:
        if len(quarters) >= 8:
            break
        facts = {key: quarterly_fact(records[key], end) for key in FLOW_FIELDS}
        if not any(facts[key] for key in ("revenue", "operating_cash_flow", "cash_capex")):
            continue
        values = {key: fact.value if fact else None for key, fact in facts.items()}
        quarters.append({"end": end, "facts": facts, "values": values, "derived": derived_metrics(values)})
    ttm_values = {key: _ttm(quarters, key) for key in FLOW_FIELDS}
    instant_rpo = _latest([row for row in records["rpo"] if "start" not in row])
    rpo = _make_fact(instant_rpo) if instant_rpo else None
    return {
        "symbol": symbol, "company": ISSUERS[symbol][0], "source": source,
        "retrieved_at": retrieved_at, "quarters": quarters,
        "ttm_end": quarters[0]["end"] if quarters else None,
        "ttm_values": ttm_values, "ttm_derived": derived_metrics(ttm_values),
        "rpo": rpo,
        "rpo_to_revenue": _ratio(rpo.value, ttm_values["revenue"]) if rpo and quarters and rpo.end == quarters[0]["end"] else None,
    }
