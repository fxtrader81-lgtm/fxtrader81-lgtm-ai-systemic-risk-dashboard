from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

from components.dashboard_quarterly_panel import build_readable_report as build_dashboard_report
from components.factor_quarterly_panel import build_readable_report as build_factor_report
from core.dashboard_quarterly import load_history as load_dashboard_history
from core.dashboard_quarterly import make_current_snapshot as make_dashboard_snapshot
from core.data_center_quarterly import load_history as load_data_center_history
from core.open_source_quarterly import load_history as load_open_source_history


def factor_result(number, score, name=None):
    return {
        "id": f"straw{number}", "name": name or f"因子{number}", "score": score,
        "state": "SAFE" if score < 25 else "WATCH" if score < 50 else "WARNING" if score < 75 else "CRITICAL",
        "available": True, "coverage": 100, "detail": f"因子{number}当前证据", "source": f"来源{number}",
    }


class QuarterlyPageTests(unittest.TestCase):
    def test_factor02_and_factor03_q3_archives_are_page_level_and_reconciled(self):
        factor02 = load_open_source_history()[0]
        factor03 = load_data_center_history()[0]
        self.assertEqual((factor02["quarter"], factor02["score"], factor02["state"]),
                         ("2026Q3", 75.0, "CRITICAL"))
        self.assertEqual((factor03["quarter"], factor03["score"], factor03["state"]),
                         ("2026Q3", 58.1, "WARNING"))
        self.assertEqual(len(factor02["components"]), 4)
        self.assertEqual(len(factor03["components"]), 4)
        self.assertEqual([row["name"] for row in factor02["components"]],
                         ["能力代差", "价格压缩", "部署动能", "生态速度"])
        self.assertEqual([row["name"] for row in factor03["components"]],
                         ["AOF机柜适配压力", "REIT估值压力", "液冷加速信号", "电力基础设施"])

    def test_factor_reports_include_current_and_q3_scores(self):
        history = load_open_source_history()
        current = dict(history[0], quarter="2026Q4", period_end=None,
                       record_type="current_in_progress", score=76.0, state="CRITICAL")
        html = build_factor_report("02", "开源商业化压缩", current, history, ["方法说明"])
        self.assertIn("2026Q4进行中", html)
        self.assertIn("76.0/100", html)
        self.assertIn("2026Q3", html)
        self.assertIn("75.0/100", html)
        self.assertIn("能力代差", html)

    def test_dashboard_q3_is_partial_and_does_not_backfill_current_values(self):
        record = load_dashboard_history()[0]
        self.assertEqual(record["quarter"], "2026Q3")
        self.assertIsNone(record["score"])
        self.assertEqual(record["state"], "N/A")
        self.assertEqual(record["coverage"], 50)
        known = {row["id"]: row["score"] for row in record["factors"]}
        self.assertEqual((known["straw2"], known["straw3"], known["straw4"]), (75.0, 58.1, 47.2))
        self.assertIsNone(known["straw1"])
        self.assertIsNone(known["straw5"])

    def test_dashboard_current_snapshot_contains_all_seven_factors(self):
        scores = [78.1, 75.0, 60.1, 50.1, 68.6, 32.0, 18.0]
        results = {f"straw{i}": factor_result(i, score) for i, score in enumerate(scores, 1)}
        system = {"score": 67.8, "state": "WARNING", "coverage": 100,
                  "phase": "常态监测", "cascade": False}
        current = make_dashboard_snapshot(results, system, today=date(2026, 10, 23))
        self.assertEqual(current["quarter"], "2026Q4")
        self.assertEqual(current["score"], 67.8)
        self.assertEqual(len(current["factors"]), 7)
        self.assertEqual([row["number"] for row in current["factors"]], ["01", "02", "03", "04", "05", "06", "07"])
        self.assertIsNone(current["factors"][5]["weight"])
        self.assertIsNone(current["factors"][6]["contribution"])
        html = build_dashboard_report(current, load_dashboard_history())
        self.assertIn("2026Q4", html)
        self.assertIn("67.8/100", html)
        self.assertIn("2026Q3", html)
        self.assertIn("结构总分：</b>N/A/100", html)

    def test_dashboard_renders_two_quarterly_menus_and_two_owner_downloads(self):
        from streamlit.testing.v1 import AppTest

        names = ["资本开支偏离", "开源商业化压缩", "数据中心资产减值", "AI能源约束",
                 "AI融资结构脆弱性", "AI信贷与再融资压力", "宏观与跨市场传导确认"]
        scores = [78.1, 75.0, 60.1, 50.1, 68.6, 32.0, 18.0]
        results = {f"straw{i}": factor_result(i, score, names[i-1]) for i, score in enumerate(scores, 1)}
        with patch("core.factor_registry.load_factor_results", return_value=results), \
             patch("core.macro_data.load_macro_stress_snapshot", side_effect=RuntimeError("offline")):
            at = AppTest.from_file("app.py", default_timeout=30)
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception), 0)
        labels = [expander.label for expander in at.expander]
        self.assertTrue(any(label.startswith("2026Q4进行中｜结构总分") for label in labels))
        self.assertIn("季度历史快照｜最近归档2026Q3 · 结构总分N/A · N/A", labels)
        self.assertEqual([button.label for button in at.get("download_button")],
                         ["下载可阅读版（HTML）", "下载完整原始资料（JSON）"])

    def test_quarterly_menus_use_shared_high_contrast_style(self):
        css = Path("styles/pages.css").read_text(encoding="utf-8")
        for key in ("dashboard_quarterly_current", "dashboard_quarterly_history",
                    "open_source_quarterly_current", "open_source_quarterly_history",
                    "data_center_quarterly_current", "data_center_quarterly_history"):
            self.assertIn(f".st-key-{key}", css)
        self.assertIn("font-size: 20px !important;", css)
        self.assertIn("color: #f8fafc !important;", css)


if __name__ == "__main__":
    unittest.main()
