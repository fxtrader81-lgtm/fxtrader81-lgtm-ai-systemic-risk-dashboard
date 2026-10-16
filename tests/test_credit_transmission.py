"""Disclosure arithmetic must preserve missingness, period grain, and provenance."""

import unittest
from unittest.mock import patch
from datetime import date

import requests
from streamlit.testing.v1 import AppTest

from core.credit_transmission import (
    build_company_snapshot, derived_metrics, disclosure_age_label, quarterly_fact, sec_url,
)


def fact(tag, start, end, val, filed="2026-04-30", accn="0001"):
    return {"tag": tag, "start": start, "end": end, "val": val, "filed": filed, "accn": accn, "form": "10-Q"}


class CreditTransmissionTests(unittest.TestCase):
    def test_gap_and_negative_cash_flow(self):
        result = derived_metrics({
            "operating_cash_flow": -20, "cash_capex": 80, "revenue": 200,
            "debt_proceeds": 50, "debt_repayments": 15,
        })
        self.assertEqual(result["cash_capex_gap"], 100)
        self.assertEqual(result["gap_share"], 1.25)
        self.assertEqual(result["capex_coverage"], -0.25)
        self.assertEqual(result["net_debt_financing"], 35)
        self.assertEqual(result["simple_fcf"], -100)

    def test_missing_and_zero_denominators_are_not_safe_zeros(self):
        result = derived_metrics({"operating_cash_flow": 50, "cash_capex": 0, "revenue": None,
                                  "debt_proceeds": 10, "debt_repayments": None})
        self.assertIsNone(result["capex_coverage"])
        self.assertIsNone(result["gap_share"])
        self.assertIsNone(result["net_debt_financing"])
        self.assertIsNone(result["net_debt_to_capex"])
        self.assertIsNone(result["capex_intensity"])
        self.assertIsNone(derived_metrics({"operating_cash_flow": None, "cash_capex": 100})["cash_capex_gap"])

    def test_uses_direct_quarter_over_ytd_and_derives_q4(self):
        tag = "NetCashProvidedByUsedInOperatingActivities"
        rows = [
            fact(tag, "2025-01-01", "2025-09-30", 90),
            fact(tag, "2025-01-01", "2025-12-31", 140, "2026-02-10"),
            fact(tag, "2025-10-01", "2025-12-31", 48, "2026-02-10"),
        ]
        self.assertEqual(quarterly_fact(rows, "2025-12-31").value, 48)
        rows.pop()
        q4 = quarterly_fact(rows, "2025-12-31")
        self.assertEqual(q4.value, 50)
        self.assertEqual(q4.kind, "根据确认数据计算")

    def test_ytd_cannot_subtract_different_fiscal_start(self):
        tag = "PaymentsToAcquirePropertyPlantAndEquipment"
        rows = [fact(tag, "2025-07-01", "2025-12-31", 90), fact(tag, "2025-01-01", "2025-09-30", 40)]
        self.assertIsNone(quarterly_fact(rows, "2025-12-31"))

    def test_snapshot_does_not_zero_fill_or_fabricate_ai_investment(self):
        tag = "NetCashProvidedByUsedInOperatingActivities"
        payload = {"facts": {"us-gaap": {tag: {"units": {"USD": [fact(tag, "2026-01-01", "2026-03-31", 10)]}}}}}
        result = build_company_snapshot(payload, "MSFT", "2026-05-01T00:00:00+00:00")
        self.assertEqual(result["quarters"][0]["values"]["operating_cash_flow"], 10)
        self.assertIsNone(result["quarters"][0]["values"]["cash_capex"])
        self.assertIsNone(result["ttm_values"]["operating_cash_flow"])
        self.assertIsNone(result["rpo_to_revenue"])
        self.assertIn("CIK0000789019", sec_url("MSFT"))

    def test_rejects_unapproved_universe(self):
        with self.assertRaises(ValueError):
            build_company_snapshot({}, "NVDA", "now")

    def test_freshness_is_a_label_not_a_score(self):
        self.assertEqual(disclosure_age_label("2025-01-01", today=date(2025, 8, 1)), "过期提示：期末距今 212 天")
        self.assertEqual(disclosure_age_label(None), "所属期间不可得")

    def test_page_renders_verified_data_without_score(self):
        rows = {}
        periods = [("2025-01-01", "2025-03-31"), ("2025-04-01", "2025-06-30"),
                   ("2025-07-01", "2025-09-30"), ("2025-10-01", "2025-12-31")]
        for tag, amount in [
            ("RevenueFromContractWithCustomerExcludingAssessedTax", 200),
            ("NetCashProvidedByUsedInOperatingActivities", 100),
            ("PaymentsToAcquirePropertyPlantAndEquipment", 70),
            ("OperatingIncomeLoss", 50), ("NetIncomeLoss", 40),
        ]:
            rows[tag] = {"units": {"USD": [fact(tag, start, end, amount) for start, end in periods]}}
        payload = {"facts": {"us-gaap": rows}}
        with patch("components.credit_transmission_views.load_companyfacts", return_value=(payload, "2026-01-31T00:00:00+00:00")):
            page = AppTest.from_file("tests/fixtures/credit_structure_view.py", default_timeout=20).run()
            page.toggle[0].set_value(True).run()
        self.assertEqual(len(page.exception), 0)
        self.assertTrue(any("TTM至 2025-12-31" in block.value for block in page.markdown))
        self.assertTrue(any("不纳入AFVI评分" in block.value for block in page.markdown))

    def test_wrong_unit_missing_source_and_duplicate_filing_are_rejected_or_deduped(self):
        tag = "RevenueFromContractWithCustomerExcludingAssessedTax"
        old = fact(tag, "2025-01-01", "2025-03-31", 100, "2025-04-20", "old")
        restated = fact(tag, "2025-01-01", "2025-03-31", 105, "2025-06-20", "new")
        no_source = {**restated, "val": 999, "accn": None}
        payload = {"facts": {"us-gaap": {tag: {"units": {"USD": [old, restated, no_source], "EUR": [{**restated, "val": 999}]}}}}}
        result = build_company_snapshot(payload, "MSFT", "2025-07-01T00:00:00+00:00")
        self.assertEqual(result["quarters"][0]["values"]["revenue"], 105)
        self.assertEqual(result["quarters"][0]["facts"]["revenue"].accession, "new")

    def test_api_failure_is_visible_without_fabricated_financials(self):
        response = requests.Response()
        response.status_code = 403
        error = requests.HTTPError(response=response)
        with patch("components.credit_transmission_views.load_companyfacts", side_effect=error):
            page = AppTest.from_file("tests/fixtures/credit_structure_view.py", default_timeout=20).run()
            page.toggle[0].set_value(True).run()
        self.assertEqual(len(page.exception), 0)
        self.assertTrue(any("HTTP 403" in block.value for block in page.warning))
        self.assertFalse(any("资本开支融资质量｜季度" in block.value for block in page.markdown))

    def test_companyfacts_is_not_requested_until_disclosure_opens(self):
        with patch("components.credit_transmission_views.load_companyfacts") as fetch:
            page = AppTest.from_file("tests/fixtures/credit_structure_view.py", default_timeout=20).run()
        self.assertEqual(len(page.exception), 0)
        fetch.assert_not_called()

    def test_credit_view_keeps_missing_issuer_quotes_out_of_score(self):
        page = AppTest.from_file("tests/fixtures/credit_market_view.py", default_timeout=20).run()
        self.assertEqual(len(page.exception), 0)
        self.assertTrue(any("不可得" in block.value and "不计入CFRI" in block.value
                            for block in page.markdown))


if __name__ == "__main__":
    unittest.main()
