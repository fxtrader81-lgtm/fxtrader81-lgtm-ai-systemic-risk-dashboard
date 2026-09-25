"""Regression checks for factor 07's retrospective event-month semantics."""

import unittest

import pandas as pd

from core.market_event_replay import build_history_rows, event_validation_scope
from core.macro_risk import compute_macro_metrics, daily_six_month_peak_gap


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
        event = [("2020-02-28", "测试冲击", "测试描述", "金融传导")]
        daily = pd.Series([100.0, 85.0, 80.0, 70.0], index=pd.to_datetime(["2020-02-27", "2020-02-28", "2020-03-05", "2020-03-20"]))
        row = build_history_rows(self.stress, event, daily)[0]
        through_february = {key: value.iloc[:5] for key, value in self.stress.items()}
        expected = compute_macro_metrics(**through_february, sp500_daily=daily.loc[:"2020-02-28"])

        self.assertEqual(row["as_of"], "2020-02")
        self.assertEqual(row["score"], expected["composite"]["score"])
        self.assertEqual(row["state"], expected["composite"]["grade"])
        self.assertEqual(row["scope"], "机制案例；不等于独立验证样本")
        self.assertIn(row["drawdown"], row["summary"])
        self.assertIn("六个月", row["summary"])
        self.assertNotIn("phase", row)
        self.assertEqual(row["drawdown"], "-30.00%")
        self.assertEqual(row["initial_drawdown"], "-30.00%")
        self.assertEqual(row["baseline_date"], "2020-02-27")
        self.assertLess(row["score"], compute_macro_metrics(**self.stress, sp500_daily=daily)["composite"]["score"])

    def test_six_month_high_uses_daily_close_not_month_end_only(self):
        daily = pd.Series(
            [100.0, 120.0, 105.0, 90.0],
            index=pd.to_datetime(["2019-09-30", "2019-11-15", "2019-11-29", "2020-02-28"]),
        )
        self.assertAlmostEqual(daily_six_month_peak_gap(daily), -25.0)
        row = build_history_rows(self.stress, [("2020-02", "测试", "", "金融传导")], daily)[0]
        self.assertIn("标普500距近六个月高点 -25.00%", row["components"])

    def test_event_score_does_not_see_daily_closes_after_event_month(self):
        daily = pd.Series(
            [100.0, 90.0, 150.0],
            index=pd.to_datetime(["2019-12-31", "2020-02-28", "2020-03-02"]),
        )
        row = build_history_rows(self.stress, [("2020-02", "测试", "", "金融传导")], daily)[0]
        self.assertIn("标普500距近六个月高点 -10.00%", row["components"])

    def test_missing_daily_history_does_not_become_safe(self):
        metrics = compute_macro_metrics(**self.stress)
        self.assertNotIn("equity_drawdown", metrics)
        self.assertEqual(metrics["composite"]["coverage"], 80)

    def test_six_month_outcome_excludes_seventh_month(self):
        dates = pd.date_range("2020-01-31", periods=13, freq="ME")
        stress = {
            "y10": pd.Series([2.0] * 13, index=dates),
            "y3m": pd.Series([1.5] * 13, index=dates),
            "sp500": pd.Series([100.0] * 11 + [80.0, 50.0], index=dates),
            "stlfsi": pd.Series([-0.5] * 13, index=dates),
            "vix": pd.Series([15.0] * 13, index=dates),
        }
        daily = pd.Series(
            [100.0, 90.0, 110.0, 70.0, 80.0, 50.0],
            index=pd.to_datetime(["2020-06-29", "2020-06-30", "2020-07-15", "2020-07-16", "2020-12-31", "2021-01-04"]),
        )
        row = build_history_rows(stress, [("2020-06-30", "测试", "测试描述", "金融传导")], daily)[0]
        self.assertEqual(row["drawdown"], "-30.00%")

    def test_no_drop_below_event_close_is_zero_not_future_peak_drawdown(self):
        daily = pd.Series(
            [85.0, 85.0, 110.0, 90.0],
            index=pd.to_datetime(["2020-02-27", "2020-02-28", "2020-03-10", "2020-03-20"]),
        )
        row = build_history_rows(self.stress, [("2020-02-28", "测试", "", "金融传导")], daily)[0]
        self.assertEqual(row["drawdown"], "0%")
        self.assertEqual(row["initial_drawdown"], "0%")

    def test_later_decline_after_recovery_is_not_initial_event_decline(self):
        daily = pd.Series(
            [100.0, 90.0, 110.0, 70.0],
            index=pd.to_datetime(["2020-02-27", "2020-02-28", "2020-03-10", "2020-03-20"]),
        )
        row = build_history_rows(self.stress, [("2020-02-28", "测试", "", "金融传导")], daily)[0]
        self.assertEqual(row["drawdown"], "-30.00%")
        self.assertEqual(row["initial_drawdown"], "-10.00%")
        self.assertEqual(row["drawdown_days"], "21")
        self.assertEqual(row["initial_drawdown_days"], "0")
        self.assertEqual(row["recovery_date"], "2020-03-10")

    def test_september_11_baseline_is_last_pre_event_trading_day(self):
        daily = pd.Series(
            [1092.54, 1038.77, 965.80, 1040.94, 1172.51],
            index=pd.to_datetime(["2001-09-10", "2001-09-17", "2001-09-21", "2001-09-28", "2002-01-04"]),
        )
        dates = pd.date_range("2001-04-30", periods=6, freq="ME")
        stress = {key: pd.Series([float(series.iloc[0])] * 6, index=dates) for key, series in self.stress.items()}
        row = build_history_rows(stress, [("2001-09-11", "9·11", "", "外生冲击")], daily)[0]
        self.assertEqual(row["baseline_date"], "2001-09-10")
        self.assertEqual(row["drawdown"], "-11.60%")
        self.assertEqual(row["drawdown_date"], "2001-09-21")
        self.assertEqual(row["drawdown_days"], "10")

    def test_missing_daily_closes_are_unavailable(self):
        row = build_history_rows(self.stress, [("2020-02", "测试", "", "金融传导")])[0]
        self.assertEqual(row["drawdown"], "N/A")

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
