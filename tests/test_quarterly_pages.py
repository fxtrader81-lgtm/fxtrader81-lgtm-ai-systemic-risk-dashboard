from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from components.dashboard_quarterly_panel import build_readable_report as build_dashboard_report
from components.factor_quarterly_panel import build_readable_report as build_factor_report
from core.dashboard_quarterly import load_history as load_dashboard_history
from core.dashboard_quarterly import make_current_snapshot as make_dashboard_snapshot
from core.data_center_quarterly import load_history as load_data_center_history
from core.credit_quarterly import load_history as load_credit_history
from core.financing_quarterly import load_history as load_financing_history
from core.financing_quarterly import make_current_snapshot as make_financing_snapshot
from core.open_source_quarterly import load_history as load_open_source_history
from core.straw5_engine import load_straw5_analysis


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

    def test_factor05_q3_is_versioned_reconstruction_and_reconciled(self):
        record = load_financing_history()[0]
        self.assertEqual((record["quarter"], record["score"], record["state"]),
                         ("2026Q3", 68.2, "WARNING"))
        self.assertTrue(record["record_type"].startswith("reconstructed_"))
        self.assertEqual(record["method_version"], "afvi-structure-v2@6cbefbc")
        self.assertEqual([row["score"] for row in record["components"]],
                         [64.5, 86.5, 62.0, 58.1])
        self.assertIn("不是9月30日自动保存", record["caveat"])

    def test_factor05_current_uses_live_factor03_collateral(self):
        analysis = load_straw5_analysis(62.9)
        current = make_financing_snapshot(analysis, today=date(2026, 10, 23))
        self.assertEqual((current["quarter"], current["score"], current["state"]),
                         ("2026Q4", 69.2, "WARNING"))
        components = {row["id"]: row for row in current["components"]}
        self.assertEqual(components["collateral"]["score"], 62.9)
        self.assertIn("本季待人工复核", components["term_mismatch"]["observation_period"])

    def test_factor06_q3_is_versioned_reconstruction_and_reconciled(self):
        record = load_credit_history()[0]
        self.assertEqual((record["quarter"], record["score"], record["state"]),
                         ("2026Q3", 20.1, "SAFE"))
        self.assertTrue(record["record_type"].startswith("reconstructed_"))
        self.assertEqual([row["score"] for row in record["components"]],
                         [0.0, 67.0, 0.0, 0.0])
        self.assertIn("不是9月30日自动保存", record["caveat"])

    def test_dashboard_q3_uses_factor05_versioned_reconstruction(self):
        record = load_dashboard_history()[0]
        self.assertEqual(record["quarter"], "2026Q3")
        self.assertEqual(record["score"], 62.7)
        self.assertEqual(record["state"], "WARNING")
        self.assertEqual(record["coverage"], 75)
        known = {row["id"]: row["score"] for row in record["factors"]}
        self.assertEqual((known["straw2"], known["straw3"], known["straw4"]), (75.0, 58.1, 47.2))
        self.assertIsNone(known["straw1"])
        self.assertEqual(known["straw5"], 68.2)
        self.assertEqual(known["straw6"], 20.1)

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
        self.assertIn("结构总分：</b>62.7/100", html)
        self.assertIn("部分补录 · 含05/06版本化复算", html)

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
        self.assertIn("季度历史快照｜最近归档2026Q3 · 结构总分62.7 · WARNING", labels)
        self.assertEqual([button.label for button in at.get("download_button")],
                         ["下载可阅读版（HTML）", "下载完整原始资料（JSON）"])

    def test_quarterly_menus_use_shared_high_contrast_style(self):
        css = Path("styles/pages.css").read_text(encoding="utf-8")
        for key in ("dashboard_quarterly_current", "dashboard_quarterly_history",
                    "open_source_quarterly_current", "open_source_quarterly_history",
                    "data_center_quarterly_current", "data_center_quarterly_history",
                    "financing_quarterly_current", "financing_quarterly_history"):
            self.assertIn(f".st-key-{key}", css)
        for key in ("credit_quarterly_current", "credit_quarterly_history"):
            self.assertIn(f".st-key-{key}", css)
        self.assertIn("font-size: 20px !important;", css)
        self.assertIn("color: #f8fafc !important;", css)

    def test_factor05_page_renders_quarterly_menus_and_protected_downloads(self):
        from streamlit.testing.v1 import AppTest

        results = {
            "straw3": {"score": 62.9, "state": "WARNING", "available": True},
            "straw6": {"score": 35.0, "state": "WATCH", "available": True},
            "straw7": {"score": 20.0, "state": "SAFE", "available": True},
        }
        with patch("core.factor_registry.load_factor_results", return_value=results):
            at = AppTest.from_file("pages/straw5.py", default_timeout=30)
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception), 0)
        labels = [expander.label for expander in at.expander]
        self.assertTrue(any(label.startswith("2026Q4进行中｜总分69.2 · WARNING") for label in labels))
        self.assertIn("季度历史快照｜最近归档2026Q3 · 总分68.2 · WARNING", labels)
        self.assertEqual([button.label for button in at.get("download_button")],
                         ["下载可阅读版（HTML）", "下载完整原始资料（JSON）"])
        text = "\n".join(block.value for block in at.markdown)
        self.assertIn("季度复核·人工确认", text)
        self.assertIn("版本化复算", text)

    def test_factor06_page_renders_q3_history_and_protected_downloads(self):
        from streamlit.testing.v1 import AppTest

        months = pd.date_range("2026-04-30", periods=4, freq="ME")
        quarters = pd.date_range("2026-01-31", periods=3, freq="3ME")
        series = {
            "hy_oas": pd.Series([2.85, 2.85, 2.85, 3.40], index=months),
            "baa10y": pd.Series([1.5, 1.5, 1.5, 1.5], index=months),
            "real_yield": pd.Series([2.47, 2.47, 2.47, 2.76], index=months),
            "nfci": pd.Series([-0.543, -0.543, -0.543, -0.496], index=months),
            "sloos": pd.Series([5.3, 8.1, 0.0], index=quarters),
        }
        with patch("core.macro_data.load_credit_stress_snapshot", return_value=(series, "测试FRED")), \
             patch("core.ai_financing_news.load_financing_news", return_value=([], None)), \
             patch("core.ai_financing_news.load_softbank_financing_releases", return_value=([], None)):
            at = AppTest.from_file("pages/straw6.py", default_timeout=30)
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception), 0)
        labels = [expander.label for expander in at.expander]
        self.assertIn("2026Q4进行中｜总分25.0 · WATCH｜当前四项与计算说明", labels)
        self.assertIn("季度历史快照｜最近归档2026Q3 · 总分20.1 · SAFE", labels)
        self.assertEqual([button.label for button in at.get("download_button")],
                         ["下载可阅读版（HTML）", "下载完整原始资料（JSON）"])

    def test_factor06_page_tolerates_cached_snapshot_without_sloos(self):
        from streamlit.testing.v1 import AppTest

        months = pd.date_range("2026-04-30", periods=4, freq="ME")
        cached_old_schema = {
            "hy_oas": pd.Series([2.85, 2.85, 2.85, 3.40], index=months),
            "baa10y": pd.Series([1.5, 1.5, 1.5, 1.5], index=months),
            "real_yield": pd.Series([2.47, 2.47, 2.47, 2.76], index=months),
            "nfci": pd.Series([-0.543, -0.543, -0.543, -0.496], index=months),
        }
        with patch("core.macro_data.load_credit_stress_snapshot",
                   return_value=(cached_old_schema, "旧缓存测试源")), \
             patch("core.ai_financing_news.load_financing_news", return_value=([], None)), \
             patch("core.ai_financing_news.load_softbank_financing_releases", return_value=([], None)):
            at = AppTest.from_file("pages/straw6.py", default_timeout=30)
            at.run()

        self.assertEqual(len(at.exception), 0)
        labels = [expander.label for expander in at.expander]
        self.assertTrue(any(label.startswith("2026Q4进行中｜总分27.7 · WATCH") for label in labels))
        text = "\n".join(block.value for block in at.markdown)
        self.assertIn("数据缺失，不按SAFE处理", text)


if __name__ == "__main__":
    unittest.main()
