import unittest
from unittest.mock import patch

from core import energy_market
from energy_market_fixture import MARKET_SNAPSHOT


class EnergyMarketTests(unittest.TestCase):
    def test_four_band_boundaries(self):
        for value, expected in (
            (0, 20), (40, 20), (40.0001, 35), (60, 35),
            (60.0001, 55), (80, 55), (80.0001, 75), (100, 75),
        ):
            self.assertEqual(energy_market.score_from_position(value), expected)
        for invalid in (-1, 101, None, True, float("nan")):
            self.assertIsNone(energy_market.score_from_position(invalid))

    def test_valid_pair_uses_mean_position_and_same_day(self):
        snapshot = energy_market.make_snapshot({
            "CEG": {"current_price": 30, "week52_low": 10, "week52_high": 110,
                    "observed_on": "2026-10-21"},
            "VST": {"current_price": 50, "week52_low": 10, "week52_high": 110,
                    "observed_on": "2026-10-21"},
        })
        self.assertTrue(snapshot["available"])
        self.assertEqual(snapshot["mean_position_pct"], 30)
        self.assertEqual(snapshot["score"], 20)
        self.assertEqual(snapshot["contribution"], 3)

    def test_missing_or_mismatched_required_quote_is_na(self):
        rows = {ticker: dict(values) for ticker, values in MARKET_SNAPSHOT["rows"].items()}
        self.assertFalse(energy_market.make_snapshot({"CEG": rows["CEG"]})["available"])
        rows["VST"]["observed_on"] = "2026-10-20"
        snapshot = energy_market.make_snapshot(rows)
        self.assertFalse(snapshot["available"])
        self.assertIn("日期不一致", snapshot["missing_reason"])

    def test_overview_uses_same_provider_and_formula(self):
        from core.factor_registry import _straw4
        with patch("core.factor_registry.energy_market.load_energy_market", return_value=MARKET_SNAPSHOT):
            result = _straw4()
        self.assertTrue(result["available"])
        self.assertAlmostEqual(result["score"], 50.1)
        self.assertIn("CEG/VST", result["detail"])


if __name__ == "__main__":
    unittest.main()
