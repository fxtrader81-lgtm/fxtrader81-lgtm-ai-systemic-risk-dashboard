from datetime import date
import unittest
from unittest.mock import patch

from core.gpu_efficiency import (
    automatic_update,
    canonicalize_summary,
    load_gpu_efficiency,
    measured_datacenter_rows,
    score_from_gain,
)
from energy_market_fixture import MARKET_SNAPSHOT


class GPUEfficiencyTests(unittest.TestCase):
    def test_current_measured_snapshot_and_legacy_history(self):
        snapshot = load_gpu_efficiency()
        metrics = snapshot["metrics"]
        self.assertTrue(snapshot["available"])
        self.assertEqual((snapshot["baseline_generation"], snapshot["target_generation"]), ("H100", "B200"))
        self.assertEqual(metrics["pair_count"], 3)
        self.assertAlmostEqual(metrics["generation_gain"], 2.814792493, places=6)
        self.assertEqual(metrics["score"], 35.5)
        self.assertEqual(metrics["state"], "WATCH")
        self.assertEqual(metrics["contribution"], 7.1)
        self.assertEqual(snapshot["next_review"], "2027-01-20")
        self.assertEqual(score_from_gain(metrics["generation_gain"]), 35.5)
        legacy = next(row for row in snapshot["history"] if row["kind"] == "legacy_method")
        self.assertEqual(legacy["score"], 27.8)
        self.assertEqual(legacy["status"], "historical_only")
        self.assertEqual([row["datacenter_measured_power_rows"] for row in snapshot["latest_source_checks"]], [0, 0])

    def test_tdp_or_design_power_is_never_treated_as_measured_power(self):
        payload = [{
            "SystemType": "datacenter", "has_power": False,
            "Organization": "Example", "SystemName": "Example B300",
            "accelerator_model_name": "B300", "accelerators_per_node": 8,
            "Model": "llama", "Scenario": "Offline", "Result": 100,
            "Units": "Tokens/s", "design_power_watts": 1200,
        }]
        row = canonicalize_summary(payload)[0]
        self.assertIsNone(row["power_watts"])
        self.assertEqual(measured_datacenter_rows(payload), [])

    def test_automatic_check_is_due_based_and_preserves_last_valid_result(self):
        snapshot = load_gpu_efficiency()
        with patch("core.gpu_efficiency._fetch_json") as fetch:
            unchanged = automatic_update(snapshot, today=date(2026, 10, 22))
        fetch.assert_not_called()
        self.assertEqual(unchanged["metrics"], snapshot["metrics"])

        with patch("core.gpu_efficiency._fetch_json", return_value=[]):
            checked = automatic_update(snapshot, today=date(2027, 4, 20))
        self.assertEqual(checked["auto_check"]["status"], "checked_no_new_release")
        self.assertEqual(checked["metrics"], snapshot["metrics"])

    def test_page_uses_collapsed_four_item_logic_and_gpu_evidence(self):
        from streamlit.testing.v1 import AppTest

        with patch("core.energy_market.load_energy_market", return_value=MARKET_SNAPSHOT), patch("requests.get") as get:
            get.return_value.status_code = 503
            at = AppTest.from_file("pages/straw4.py", default_timeout=20)
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception), 0)
        labels = [item.label for item in at.expander]
        for expected in (
            "1　基础设施约束（×0.40）", "2　能源成本压力（×0.25）",
            "3　AI推理系统能效对冲（×0.20）", "4　电力市场信号（×0.15）",
        ):
            item = next(expander for expander in at.expander if expander.label == expected)
            self.assertFalse(item.proto.expanded)
        self.assertEqual(labels.count("评分规则"), 0)
        self.assertIn("AI推理系统能效对冲｜本期实测与计算说明", labels)
        self.assertFalse(any(button.label == "下载GPU能效历史与原始资料"
                             for button in at.get("download_button")))
        self.assertTrue(any(button.label == "下载可阅读版（HTML）"
                            for button in at.get("download_button")))
        self.assertTrue(any(button.label == "下载完整原始资料（JSON）"
                            for button in at.get("download_button")))
        self.assertAlmostEqual(at.session_state["straw_scores"]["straw4"], 50.1)

    def test_detection_logic_uses_scoped_dark_expander_styles(self):
        from pathlib import Path

        page = Path("pages/straw4.py").read_text(encoding="utf-8")
        css = Path("styles/pages.css").read_text(encoding="utf-8")
        self.assertIn('key="energy_detection_logic"', page)
        self.assertIn(".st-key-energy_detection_logic", css)
        self.assertIn("details[open] > summary", css)
        self.assertIn("-webkit-text-fill-color: #f8fafc", css)


if __name__ == "__main__":
    unittest.main()
