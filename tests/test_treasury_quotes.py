"""The current Treasury cards must be fresh, timestamped and independent of FRED history."""

import unittest
from unittest.mock import patch

import pandas as pd

from core.treasury_quotes import TreasuryQuote, fetch_latest_treasury_quote


class TreasuryQuoteTests(unittest.TestCase):
    def test_latest_minute_and_timestamp_are_kept(self):
        frame = pd.DataFrame(
            {"Close": [5.200, 5.277]},
            index=pd.to_datetime(["2026-10-02 13:58", "2026-10-02 13:59"]).tz_localize("America/Chicago"),
        )
        with patch("core.treasury_quotes.yf.Ticker") as ticker:
            ticker.return_value.history.return_value = frame
            first = fetch_latest_treasury_quote("^TNX")
            second = fetch_latest_treasury_quote("^TNX")
        self.assertEqual(first.yield_pct, 5.277)
        self.assertEqual(first.observed_at, frame.index[-1])
        self.assertIn("2026-10-02 14:59 ET", first.label)
        self.assertEqual(ticker.return_value.history.call_count, 2)
        self.assertEqual(second, first)

    def test_legacy_tenfold_scale_is_normalized(self):
        frame = pd.DataFrame(
            {"Close": [56.3]},
            index=pd.to_datetime(["2026-10-02 13:59"]).tz_localize("America/Chicago"),
        )
        with patch("core.treasury_quotes.yf.Ticker") as ticker:
            ticker.return_value.history.return_value = frame
            quote = fetch_latest_treasury_quote("^TYX")
        self.assertAlmostEqual(quote.yield_pct, 5.63)

    def test_failed_or_untimed_feed_does_not_use_a_stale_daily_value(self):
        with patch("core.treasury_quotes.yf.Ticker") as ticker:
            ticker.return_value.history.return_value = pd.DataFrame()
            self.assertEqual(fetch_latest_treasury_quote("^TNX"), TreasuryQuote())
            ticker.return_value.history.return_value = pd.DataFrame(
                {"Close": [5.2]}, index=pd.to_datetime(["2026-10-02 13:59"]),
            )
            self.assertEqual(fetch_latest_treasury_quote("^TNX"), TreasuryQuote())
        self.assertEqual(TreasuryQuote().label, "最近报价不可用")

    def test_unknown_ticker_is_rejected(self):
        with self.assertRaises(ValueError):
            fetch_latest_treasury_quote("^GSPC")


if __name__ == "__main__":
    unittest.main()
