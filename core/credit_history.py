"""Current-vintage proxy replay for selected historical credit events.

The rows are illustrative cases, not a point-in-time forecast evaluation.
FRED's current HY OAS history is short, so older dates fall back to a visibly
different BAA−10Y proxy through the shared credit model.
"""

from __future__ import annotations

import pandas as pd

from core.credit_risk import compute_credit_metrics


def as_of(series: pd.Series, month: str, lead_months: int) -> pd.Series:
    if series is None or series.empty:
        return pd.Series(dtype=float)
    cutoff = pd.Period(month, freq="M") - lead_months
    indexed = series.copy()
    indexed.index = pd.to_datetime(indexed.index).to_period("M")
    return indexed[indexed.index <= cutoff]


def build_credit_history_rows(series: dict[str, pd.Series], events: list[tuple[str, str, str]]) -> list[dict]:
    rows = []
    for month, event, description in events:
        def reading(lead_months: int) -> dict:
            return compute_credit_metrics(
                as_of(series["hy_oas"], month, lead_months),
                as_of(series["real_yield"], month, lead_months),
                as_of(series["nfci"], month, lead_months),
                baa_spread=as_of(series["baa10y"], month, lead_months),
            )

        metrics = reading(3)
        earlier = reading(6)["composite"]
        composite = metrics["composite"]
        credit = metrics.get("credit_spread")
        rows.append({
            "month": month,
            "event": event,
            "description": description,
            "score": composite["score"],
            "state": composite["grade"],
            "earlier_score": earlier["score"],
            "earlier_state": earlier["grade"],
            "coverage": composite["coverage"],
            "credit": "N/A" if not credit else f"{credit['value']:.0f}bp · {credit.get('proxy', '')}",
            "real": "N/A" if "real_rate" not in metrics else f"{metrics['real_rate']['value']:.2f}%",
            "nfci": "N/A" if "financial_conditions" not in metrics else f"{metrics['financial_conditions']['value']:+.2f}",
        })
    return rows
