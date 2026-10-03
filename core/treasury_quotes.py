"""Fresh, timestamped Treasury-yield index quotes for factor 07 KPI cards.

These Cboe/Yahoo quotes are not the FRED constant-maturity daily history and
must never be silently spliced into the historical chart or monthly score.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class TreasuryQuote:
    yield_pct: float | None = None
    observed_at: pd.Timestamp | None = None

    @property
    def label(self) -> str:
        if self.yield_pct is None or self.observed_at is None:
            return "最近报价不可用"
        return f"Yahoo/Cboe 最近报价 · {self.observed_at.tz_convert('America/New_York'):%Y-%m-%d %H:%M} ET"


def fetch_latest_treasury_quote(ticker: str) -> TreasuryQuote:
    """Request the last available minute quote on every call; never cache it.

    The last five market days cover weekends/holidays. A historical last quote
    is labelled by its own timestamp, not presented as a live market price.
    """
    if ticker not in {"^TNX", "^TYX"}:
        raise ValueError(f"Unsupported Treasury quote ticker: {ticker}")
    try:
        frame = yf.Ticker(ticker).history(
            period="5d", interval="1m", auto_adjust=False, prepost=False,
        )
        if frame.empty or "Close" not in frame:
            return TreasuryQuote()
        closes = pd.to_numeric(frame["Close"], errors="coerce").dropna()
        if closes.empty:
            return TreasuryQuote()
        observed_at = pd.Timestamp(closes.index[-1])
        if observed_at.tzinfo is None:
            return TreasuryQuote()  # Cannot give an auditable quote time.
        value = float(closes.iloc[-1])
        # Older Yahoo feed variants express the yield index as yield × 10.
        if value > 15:
            value /= 10
        if not 0 < value < 20:
            return TreasuryQuote()
        return TreasuryQuote(value, observed_at)
    except Exception:
        return TreasuryQuote()
