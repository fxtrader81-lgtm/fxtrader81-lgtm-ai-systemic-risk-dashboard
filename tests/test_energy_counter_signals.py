from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

from core.energy_counter_signals import load_counter_signals, next_quarter
from energy_market_fixture import MARKET_SNAPSHOT


class EnergyCounterSignalTests(unittest.TestCase):
    def test_reviewed_snapshot_uses_project_stages_not_legacy_ratio(self):
        snapshot = load_counter_signals(today=date(2026, 10, 23))
        self.assertFalse(snapshot["review_due"])
        self.assertEqual(snapshot["reviewed_quarter"], "2026Q4")
        self.assertEqual(snapshot["next_review_quarter"], "2027Q1")
        self.assertIn("不计入ESRI", snapshot["score_effect"])
        self.assertEqual(len(snapshot["signals"]["overseas_ai_expansion"]["projects"]), 2)
        self.assertEqual(len(snapshot["signals"]["dedicated_power_progress"]["projects"]), 4)
        combined = str(snapshot)
        self.assertNotIn("25.7%", combined)
        self.assertNotIn("海外AI专用电力容量占比", combined)

    def test_cross_quarter_raises_manual_review_without_changing_snapshot(self):
        snapshot = load_counter_signals(today=date(2027, 1, 1))
        self.assertTrue(snapshot["review_due"])
        self.assertEqual(snapshot["current_quarter"], "2027Q1")
        self.assertIn("跨季度待人工复核", snapshot["review_status"])
        self.assertIn("不自动改写项目清单", snapshot["review_message"])
        self.assertEqual(next_quarter("2026Q4"), "2027Q1")

    def test_page_replaces_legacy_counter_claims_and_exposes_sources(self):
        from streamlit.testing.v1 import AppTest

        with patch("core.energy_market.load_energy_market", return_value=MARKET_SNAPSHOT):
            at = AppTest.from_file("pages/straw4.py", default_timeout=20)
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception), 0)
        values = "\n".join(item.value for item in at.markdown)
        self.assertIn("反证观察，不计入ESRI", values)
        self.assertIn("Counter A · 海外AI算力扩张", values)
        self.assertIn("Counter C · 专属与签约能源进展", values)
        self.assertIn("2026Q4已人工核验", values)
        self.assertNotIn("AECR=", values)
        self.assertNotIn("当前海外占比", values)
        labels = [item.label for item in at.expander]
        self.assertIn("反证模块｜2026Q4人工核验项目与来源", labels)
        downloads = [button.label for button in at.get("download_button")]
        self.assertIn("下载反证项已核验资料（JSON）", downloads)

    def test_counter_styles_keep_dark_theme_contrast(self):
        css = Path("styles/pages.css").read_text(encoding="utf-8")
        self.assertIn(".counter-review-banner", css)
        self.assertIn(".counter-review-banner-due", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(".counter-source-links a", css)
        self.assertIn(".st-key-energy_counter_evidence", css)
        self.assertIn("-webkit-text-fill-color: #e2e8f0", css)


if __name__ == "__main__":
    unittest.main()
