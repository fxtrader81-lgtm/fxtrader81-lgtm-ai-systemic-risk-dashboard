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
        self.assertEqual(row["drawdown_days"], "—")
        self.assertEqual(row["recovery_duration"], "未跌破基准")
        self.assertIn("没有一天收盘跌破该基准", row["summary"])

    def test_drawdown_magnitude_and_recovery_duration_are_distinct(self):
        daily = pd.Series(
            [100.0, 90.0, 70.0, 101.0],
            index=pd.to_datetime(["2020-02-27", "2020-02-28", "2020-03-05", "2020-03-12"]),
        )
        row = build_history_rows(self.stress, [("2020-02-28", "测试", "", "金融传导")], daily)[0]
        self.assertEqual(row["drawdown"], "-30.00%")
        self.assertEqual(row["drawdown_formula"], "70.00 ÷ 100.00 − 1 = -30.00%")
        self.assertEqual(row["drawdown_days"], "6")
        self.assertEqual(row["recovery_after_trough_date"], "2020-03-12")
        self.assertEqual(row["recovery_duration"], "13天")
        self.assertEqual(row["window_end_label"], "最后可用交易日")
        self.assertIn("观察日后第6个自然日", row["summary"])

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
        self.assertTrue(row["later_episode"])
        self.assertIn("后续另一段下跌", row["summary"])

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

    def test_dot_com_example_uses_fixed_pre_event_close_not_one_day_loss(self):
        daily = pd.Series(
            [1527.35, 1527.46, 1356.56, 1448.72],
            index=pd.to_datetime(["2000-03-23", "2000-03-24", "2000-04-14", "2000-09-22"]),
        )
        dates = pd.date_range("1999-10-31", periods=6, freq="ME")
        stress = {key: pd.Series([float(series.iloc[0])] * 6, index=dates) for key, series in self.stress.items()}
        row = build_history_rows(stress, [("2000-03-24", "科网泡沫见顶", "", "估值周期")], daily)[0]
        self.assertEqual(row["baseline_close"], "1,527.35")
        self.assertEqual(row["drawdown"], "-11.18%")
        self.assertEqual(row["initial_drawdown"], "-11.18%")
        self.assertEqual(row["drawdown_days"], "21")
        self.assertEqual(row["recovery_duration"], "六个月内未收复")
        self.assertEqual(row["window_end_date"], "2000-09-22")
        self.assertEqual(row["window_end_close"], "1,448.72")
        self.assertEqual(row["window_end_return"], "-5.15%")
        self.assertIn("2000-03-24为观察日", row["summary"])
        self.assertIn("2000-03-23标普500收于1,527.35点", row["summary"])
        self.assertIn("观察日后第21个自然日", row["summary"])
        self.assertIn("六个月观察期最后交易日2000-09-22收于1,448.72点", row["summary"])
        self.assertIn("仍未收复", row["summary"])
        self.assertEqual(row["first_breach_date"], "2000-04-14")

    def test_first_recovery_requires_a_prior_close_below_baseline(self):
        daily = pd.Series(
            [100.0, 110.0, 105.0, 95.0, 100.0, 112.0],
            index=pd.to_datetime(["2020-02-27", "2020-02-28", "2020-03-02", "2020-03-03", "2020-03-04", "2020-03-05"]),
        )
        row = build_history_rows(self.stress, [("2020-02-28", "测试", "", "金融传导")], daily)[0]
        self.assertEqual(row["first_breach_date"], "2020-03-03")
        self.assertEqual(row["recovery_date"], "2020-03-04")
        self.assertEqual(row["first_underwater_days"], "1个自然日后收复")
        self.assertEqual(row["initial_drawdown"], "-5.00%")
        self.assertEqual(row["new_high_date"], "2020-02-28")

    def test_recovered_baseline_does_not_imply_new_six_month_high(self):
        daily = pd.Series(
            [120.0, 100.0, 80.0, 100.0, 105.0],
            index=pd.to_datetime(["2020-01-15", "2020-02-27", "2020-02-28", "2020-03-10", "2020-04-01"]),
        )
        row = build_history_rows(self.stress, [("2020-02-28", "测试", "", "金融传导")], daily)[0]
        self.assertEqual(row["recovery_date"], "2020-03-10")
        self.assertEqual(row["new_high_date"], "—")
        self.assertIn("未超过事前六个月最高收盘", row["summary"])

    def test_four_month_delayed_first_breach_is_not_attributed(self):
        dates = pd.bdate_range("2020-02-28", "2020-07-01")
        daily = pd.Series([100.0] + [101.0] * (len(dates) - 2) + [82.0], index=dates)
        daily.loc[pd.Timestamp("2020-02-27")] = 100.0
        daily = daily.sort_index()
        row = build_history_rows(self.stress, [("2020-02-28", "测试", "", "金融传导")], daily)[0]
        self.assertEqual(row["drawdown"], "-18.00%")
        self.assertEqual(row["first_breach_date"], "2020-07-01")
        self.assertIn("较晚出现，不能直接归因", row["breach_timing"])
        self.assertEqual(row["recovery_date"], "未恢复")

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
