from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

from core.energy_quarterly import load_history, make_current_snapshot
from components.energy_quarterly_panel import build_readable_report
from core.gpu_efficiency import load_gpu_efficiency
from core.infra_current import load_infra
from core.energy_cost import load_cost
from energy_market_fixture import MARKET_SNAPSHOT


class EnergyQuarterlyTests(unittest.TestCase):
    def test_q3_is_one_page_level_previous_state_with_source_periods(self):
        records = load_history()
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["quarter"], "2026Q3")
        self.assertEqual(record["period_end"], "2026-09-30")
        self.assertEqual(record["record_type"], "backfilled_previous_page_state")
        self.assertEqual(record["score"], 47.2)
        self.assertEqual(record["display_score"], 47)
        self.assertEqual(record["state"], "WATCH")
        self.assertEqual(record["components"][3]["name"], "电力市场信号")
        self.assertTrue(all(row["observation_period"] for row in record["components"]))
        self.assertIn("不是四项数据都在9月30日发布或实测", record["caveat"])

    def test_live_values_are_q4_in_progress_and_do_not_append_history(self):
        before = load_history()
        snapshot = make_current_snapshot(
            load_infra(), load_cost(), load_gpu_efficiency(check_remote=False),
            MARKET_SNAPSHOT, today=date(2026, 10, 22),
        )
        self.assertEqual(snapshot["quarter"], "2026Q4")
        self.assertEqual(snapshot["record_type"], "current_in_progress")
        self.assertIsNone(snapshot["period_end"])
        self.assertAlmostEqual(snapshot["score"], 50.1)
        self.assertEqual(snapshot["state"], "WARNING")
        self.assertEqual(snapshot["components"][3]["name"], "电力市场信号")
        self.assertEqual(load_history(), before)

    def test_page_has_q3_unified_history_and_q4_current_only(self):
        from streamlit.testing.v1 import AppTest
        with patch("core.energy_market.load_energy_market", return_value=MARKET_SNAPSHOT):
            at = AppTest.from_file("pages/straw4.py", default_timeout=20)
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception), 0)
        labels = [item.label for item in at.expander]
        self.assertIn("2026Q4进行中｜总分50.1 · WARNING｜当前四项与计算说明", labels)
        self.assertIn("季度历史快照｜最近归档2026Q3 · 总分47.2 · WATCH", labels)
        values = "\n".join(item.value for item in at.markdown)
        self.assertIn("2026Q3 · 截止2026-09-30", values)
        self.assertIn("归档总得分47.2/100，状态WATCH（观察）", values)
        self.assertIn("总得分", values)
        self.assertIn("50.1/100", values)
        self.assertIn("电力市场信号", values)
        downloads = [button.label for button in at.get("download_button")]
        self.assertEqual(downloads.count("下载可阅读版（HTML）"), 1)
        self.assertEqual(downloads.count("下载完整原始资料（JSON）"), 1)
        self.assertNotIn("下载能源成本历史与原始资料", downloads)
        self.assertNotIn("下载GPU能效历史与原始资料", downloads)

    def test_readable_download_contains_current_history_scores_states_and_methods(self):
        current = make_current_snapshot(
            load_infra(), load_cost(), load_gpu_efficiency(check_remote=False),
            MARKET_SNAPSHOT, today=date(2026, 10, 22),
        )
        report = build_readable_report(current, load_history(), {"market_signal": "旧方法资料"})
        for text in ("<!doctype html>", "2026Q4", "50.1/100", "WARNING（警戒）",
                     "2026Q3", "47.2/100", "WATCH（观察）", "旧版方法与原始证据", "电力市场信号"):
            self.assertIn(text, report)

    def test_quarterly_sections_have_scoped_high_contrast_styles(self):
        panel = Path("components/energy_quarterly_panel.py").read_text(encoding="utf-8")
        css = Path("styles/pages.css").read_text(encoding="utf-8")
        self.assertIn('key="energy_quarterly_current"', panel)
        self.assertIn('key="energy_quarterly_history"', panel)
        self.assertIn(".st-key-energy_quarterly_current", css)
        self.assertIn(".st-key-energy_quarterly_history", css)
        self.assertIn("-webkit-text-fill-color: #e2e8f0", css)
        self.assertIn("font-size: 20px !important", css)
        self.assertIn(".energy-quarter-score-strip", css)


if __name__ == "__main__":
    unittest.main()
