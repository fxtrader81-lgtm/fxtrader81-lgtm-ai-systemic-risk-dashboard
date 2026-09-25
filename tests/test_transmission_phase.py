"""Phase wording must describe observed data without promising prediction."""

import unittest

import pandas as pd

from core.transmission_phase import market_phase, market_phase_from_series, system_phase


class TransmissionPhaseTests(unittest.TestCase):
    def test_distinct_market_stages(self):
        self.assertEqual(market_phase("SAFE")["key"], "quiet")
        self.assertEqual(market_phase("WATCH")["key"], "transmitting")
        self.assertEqual(market_phase("WARNING")["key"], "release")
        self.assertEqual(market_phase("N/A")["key"], "unavailable")

    def test_dissipation_requires_prior_stress_and_multiple_improvements(self):
        phase = market_phase("SAFE", prior_grades=["WARNING"], equity_momentum=1.0,
                             vix_change=-5.0, stress=-0.1)
        self.assertEqual(phase["key"], "dissipating")
        self.assertEqual(market_phase("SAFE", prior_grades=["SAFE"], equity_momentum=1.0,
                                      vix_change=-5.0, stress=-0.1)["key"], "quiet")
        self.assertEqual(market_phase("SAFE", prior_grades=["WARNING"], equity_momentum=-1.0,
                                      vix_change=-5.0, stress=-0.1)["key"], "quiet")

    def test_cascade_chain_needs_structure_credit_and_market(self):
        result = system_phase("WARNING", "WARNING", market_phase("WATCH"))
        self.assertEqual(result["nodes"], (True, True, True, False))
        self.assertIn("CASCADE", result["label"])
        self.assertNotIn("CASCADE", system_phase("WARNING", "SAFE", market_phase("WATCH"))["label"])

    def test_market_history_uses_prior_completed_months(self):
        dates = pd.date_range("2020-01-31", periods=8, freq="ME")
        series = {
            "y10": pd.Series([2.0] * 8, index=dates),
            "y3m": pd.Series([1.0] * 8, index=dates),
            "sp500": pd.Series([100, 100, 100, 70, 70, 70, 80, 100], index=dates),
            "stlfsi": pd.Series([-0.5] * 3 + [1.0] * 3 + [-0.5] * 2, index=dates),
            "vix": pd.Series([15] * 3 + [40] * 3 + [20, 15], index=dates),
        }
        self.assertEqual(market_phase_from_series(series)["key"], "dissipating")


if __name__ == "__main__":
    unittest.main()
