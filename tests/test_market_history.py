"""Regression checks for factor 07's retrospective event-month semantics."""

import unittest

import pandas as pd

from core.market_history import build_history_rows, event_validation_scope
from core.macro_risk import compute_macro_metrics


class MarketHistoryTests(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2019-10-31", periods=6, freq="ME")
        self.stress = {
            "y10": pd.Series([2.0, 2.0, 2.0, 2.0, 2.0, 2.0], index=dates),
            "y3m": pd.Series([1.5] * 6, index=dates),
            "sp500": pd.Series([100.0, 101.0, 102.0, 103.0, 85.0, 80.0], index=dates),
            "stlfsi": pd.Series([-0.5, -0.5, -0.5, -0.5, 0.8, 1.0], index=dates),
            "vix": pd.Series([15.0, 15.0, 15.0, 15.0, 40.0, 45.0], index=dates),
        }

    def test_event_month_score_includes_event_month_not_later_month(self):
        event = [("2020-02", "测试冲击", "测试描述", "金融传导")]
        row = build_history_rows(self.stress, event)[0]
        through_february = {key: value.iloc[:5] for key, value in self.stress.items()}
        expected = compute_macro_metrics(**through_february)

        self.assertEqual(row["as_of"], "2020-02")
        self.assertEqual(row["score"], expected["composite"]["score"])
        self.assertEqual(row["state"], expected["composite"]["grade"])
        self.assertEqual(row["scope"], "机制案例；不等于独立验证样本")
        self.assertIn(row["drawdown"], row["summary"])
        self.assertIn("6个月", row["summary"])
        self.assertIn("phase", row)
        self.assertLess(row["score"], compute_macro_metrics(**self.stress)["composite"]["score"])

    def test_six_month_outcome_excludes_seventh_month(self):
        dates = pd.date_range("2020-01-31", periods=13, freq="ME")
        stress = {
            "y10": pd.Series([2.0] * 13, index=dates),
            "y3m": pd.Series([1.5] * 13, index=dates),
            "sp500": pd.Series([100.0] * 11 + [80.0, 50.0], index=dates),
            "stlfsi": pd.Series([-0.5] * 13, index=dates),
            "vix": pd.Series([15.0] * 13, index=dates),
        }
        row = build_history_rows(stress, [("2020-06", "测试", "测试描述", "金融传导")])[0]
        self.assertEqual(row["drawdown"], "-20%")

    def test_external_shock_and_bottom_are_not_validation_samples(self):
        self.assertIn("模型边界", event_validation_scope("外生冲击"))
        self.assertIn("不纳入", event_validation_scope("周期底部"))

    def test_missing_source_is_unavailable_not_safe(self):
        missing = {key: pd.Series(dtype=float) for key in self.stress}
        row = build_history_rows(missing, [("2020-02", "测试", "", "金融传导")])[0]
        self.assertIsNone(row["score"])
        self.assertEqual(row["state"], "N/A")


if __name__ == "__main__":
    unittest.main()
