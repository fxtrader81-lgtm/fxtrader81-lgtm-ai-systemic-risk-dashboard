"""Factor-06 scoring must preserve published SLOOS bands and missingness."""

import unittest

import pandas as pd

from core.credit_risk import compute_credit_metrics, score_lending_standards


class CreditRiskTests(unittest.TestCase):
    def test_sloos_uses_federal_reserve_qualitative_bands(self):
        self.assertEqual(score_lending_standards(5.0), 0)
        self.assertEqual(score_lending_standards(5.01), 33)
        self.assertEqual(score_lending_standards(10.0), 33)
        self.assertEqual(score_lending_standards(10.01), 67)
        self.assertEqual(score_lending_standards(20.0), 67)
        self.assertEqual(score_lending_standards(20.01), 100)

    @staticmethod
    def _market_series():
        months = pd.date_range("2026-04-30", periods=4, freq="ME")
        return (
            pd.Series([2.85, 2.85, 2.85, 3.40], index=months),
            pd.Series([2.47, 2.47, 2.47, 2.76], index=months),
            pd.Series([-0.543, -0.543, -0.543, -0.496], index=months),
        )

    def test_quarterly_sloos_completes_coverage_and_rounding_matches_grade(self):
        hy_oas, real_yield, nfci = self._market_series()
        quarters = pd.date_range("2026-01-31", periods=3, freq="3ME")
        metrics = compute_credit_metrics(
            hy_oas, real_yield, nfci,
            lending_standards=pd.Series([5.3, 8.1, 0.0], index=quarters),
        )
        self.assertEqual(metrics["lending_standards"]["score"], 0.0)
        self.assertEqual(metrics["composite"]["coverage"], 100)
        self.assertEqual(metrics["composite"]["score"], 25.0)
        self.assertEqual(metrics["composite"]["grade"], "WATCH")

    def test_missing_sloos_is_not_imputed_as_safe(self):
        hy_oas, real_yield, nfci = self._market_series()
        metrics = compute_credit_metrics(hy_oas, real_yield, nfci)
        self.assertNotIn("lending_standards", metrics)
        self.assertEqual(metrics["composite"]["coverage"], 90)


if __name__ == "__main__":
    unittest.main()
