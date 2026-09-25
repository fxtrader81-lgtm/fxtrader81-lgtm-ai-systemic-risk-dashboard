"""Historical credit proxy replay must not use post-cutoff values."""

import unittest

import pandas as pd

from core.credit_history import as_of, build_credit_history_rows


class CreditHistoryTests(unittest.TestCase):
    def test_cutoff_is_three_or_six_months_before_event(self):
        dates = pd.date_range("2019-01-31", periods=12, freq="ME")
        values = pd.Series(range(12), index=dates)
        self.assertEqual(as_of(values, "2019-12", 3).iloc[-1], 8)
        self.assertEqual(as_of(values, "2019-12", 6).iloc[-1], 5)

    def test_old_period_uses_labelled_baa_proxy_not_missing_hy(self):
        dates = pd.date_range("2019-01-31", periods=12, freq="ME")
        series = {
            "hy_oas": pd.Series(dtype=float),
            "baa10y": pd.Series([2.0] * 12, index=dates),
            "real_yield": pd.Series([1.0] * 12, index=dates),
            "nfci": pd.Series([-0.5] * 12, index=dates),
        }
        row = build_credit_history_rows(series, [("2019-12", "测试", "说明")])[0]
        self.assertIn("BAA10Y长期代理", row["credit"])
        self.assertEqual(row["state"], "SAFE")
        self.assertEqual(row["earlier_state"], "SAFE")

    def test_sparse_old_period_remains_unavailable(self):
        blank = pd.Series(dtype=float)
        series = {key: blank for key in ("hy_oas", "baa10y", "real_yield", "nfci")}
        row = build_credit_history_rows(series, [("1998-08", "测试", "说明")])[0]
        self.assertEqual(row["state"], "N/A")
        self.assertIsNone(row["score"])


if __name__ == "__main__":
    unittest.main()
