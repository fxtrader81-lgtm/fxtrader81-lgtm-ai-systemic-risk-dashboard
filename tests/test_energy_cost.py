from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from core import energy_cost as cost
from energy_market_fixture import MARKET_SNAPSHOT


class EnergyCostTests(unittest.TestCase):
    def test_maintenance_light_missing_due_and_reviewed_states(self):
        from components.energy_cost_status import maintenance_status, maintenance_badge
        s = {"available": True, "reviewed_on": "2026-10-21"}
        self.assertFalse(maintenance_status(s, date(2027, 1, 18))["attention"])
        self.assertIn("2027-01-19", maintenance_status(s, date(2026, 10, 21))["detail"])
        self.assertIn("已到复核期", maintenance_status(s, date(2027, 1, 19))["label"])
        self.assertTrue(maintenance_status(dict(s, reviewed_on="bad"))["attention"])
        self.assertTrue(maintenance_status(s, date(2026, 10, 20))["attention"])
        missing = dict(s, available=False)
        self.assertIn("待补齐数据", maintenance_status(missing, date(2026, 10, 21))["label"])
        self.assertIn("cost-maintenance--attention", maintenance_badge(missing))
        self.assertIn("aria-hidden", maintenance_badge(missing))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"history.sqlite3"

    def test_reviewed_pair_conversion_formula_and_opex_classification(self):
        s = cost.load_industrial_background(self.path)
        self.assertEqual((s["us_price"], s["cn_price"], s["ratio"], s["score"]), (.05, .068, 1.36, 9))
        self.assertIn("假设", s["opex_classification"])
        self.assertIn("得州", s["rows"][0]["scope"])
        self.assertEqual(s["period"], "2025")
        self.assertNotEqual(s["period"], s["reviewed_on"])

    def test_original_formula_parity_and_invalid_values(self):
        for us in (.05, .079, .1, .2):
            for cn in (.028, .05, .068, .2):
                for opex in (0, 10, 15, 35, 100):
                    clamp = lambda x: max(0, min(100, x))
                    self.assertEqual(cost.score_cost(us, cn, opex), round(clamp((.6-cn/us)/.4*100)*.55+clamp((opex-10)/25*100)*.45, 1))
        for bad in (None, 0, -1, True, float('nan'), float('inf')):
            self.assertIsNone(cost.score_cost(bad, .068, 15))
            self.assertIsNone(cost.score_cost(.05, bad, 15))
        self.assertIsNone(cost.score_cost(.05, .068, 101))

    def test_history_dedup_original_428_and_current_9(self):
        cost.load_cost(self.path)
        before = cost.history(self.path)
        cost.load_cost(self.path)
        self.assertEqual(before, cost.history(self.path))
        self.assertEqual([r["score"] for r in before], [40, 9, None, 9, 42.8])
        self.assertIn("source_url", before[3])
        self.assertIn("adopted_at", before[0])

    def test_missing_duplicate_invalid_pair_no_fallback(self):
        config = json.loads(cost.CONFIG.read_text())
        for rows in (config["rows"][:1], [config["rows"][0]]*2, [{"country":"US","usd_mwh":None},config["rows"][1]]):
            bad = deepcopy(config)
            bad["rows"] = rows
            with patch.object(cost.json, "loads", return_value=bad):
                s = cost.load_industrial_background(self.path)
            self.assertFalse(s["available"])
            self.assertIsNone(s["score"])

    def test_page_binds_same_provider_no_eia_request_and_download_present(self):
        from streamlit.testing.v1 import AppTest
        with patch.object(cost, "STORE", self.path), \
             patch("core.energy_market.load_energy_market", return_value=MARKET_SNAPSHOT), \
             patch("requests.get") as get:
            get.return_value.status_code = 503
            at = AppTest.from_file("pages/straw4.py", default_timeout=20)
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception), 0)
        values = "\n".join(m.value for m in at.markdown)
        self.assertIn("1.36", values)  # Background only, not the current score.
        self.assertIn("中国2地区公开参考价", values)
        self.assertIn("已复核 · 人工维护", values)
        self.assertNotIn("EIA API 失败", values)
        self.assertIn("未纳入评分的地区与线索", values)
        self.assertIn("2025年工业电价背景", values)
        self.assertEqual(len(at.get("json")), 0)
        self.assertNotIn('"id"', values)
        self.assertIn("能源成本压力｜本期对比与计算说明", [e.label for e in at.expander])
        self.assertFalse(any(d.label=="下载能源成本历史与原始资料" for d in at.get("download_button")))
        self.assertTrue(any(d.label=="下载可阅读版（HTML）" for d in at.get("download_button")))
        self.assertTrue(any(d.label=="下载完整原始资料（JSON）" for d in at.get("download_button")))
        self.assertFalse(any("api.eia.gov" in str(c) for c in get.call_args_list))
        self.assertIn("straw4", at.session_state["straw_scores"])

    def test_missing_cost_clears_page_total_and_overview_no_old_price(self):
        from streamlit.testing.v1 import AppTest
        from core.factor_registry import _straw4
        missing = dict(cost.load_cost(self.path), available=False, score=None, us_price=None, ratio=None, missing_reason="固定篮子数据缺失")
        with patch.object(cost, "load_cost", return_value=missing), patch("requests.get") as get:
            get.return_value.status_code = 503
            at = AppTest.from_file("pages/straw4.py", default_timeout=20)
            at.session_state["straw_scores"] = {"straw4": 52.3}
            at.run()
        self.assertEqual(len(at.exception), 0)
        self.assertNotIn("straw4", at.session_state["straw_scores"])
        with patch("core.factor_registry.load_cost", return_value=missing), patch("core.factor_registry._history") as market:
            self.assertFalse(_straw4()["available"])
            market.assert_not_called()

    def test_clusters_keep_range_history_target_separate_no_midpoint_or_industrial_score(self):
        s = cost.load_cost(self.path)
        self.assertTrue(s["available"])
        self.assertIsNone(s["ratio"])
        self.assertEqual(s["score"], 40)
        self.assertEqual(s["background"]["ratio"], 1.36)
        rows = {r["id"]:r for r in s["prior_cluster_evidence"]["rows"]}
        self.assertEqual(rows["cn-inner-mongolia"]["price"], "0.35—0.38元/度")
        self.assertEqual(rows["cn-xinjiang-target"]["classification"], "未来目标")
        self.assertIn("历史", rows["cn-qinghai-hainan"]["classification"])
        self.assertIn("历史", rows["cn-guangxi-policy"]["classification"])
        self.assertEqual(rows["us-virginia"]["price"], "待核验")
        self.assertTrue(all(r["source_url"].startswith("https://") for r in s["rows"]))

    def test_reference_endpoints_missing_duplicates_and_no_midpoint(self):
        data = json.loads(cost.REFERENCE_CONFIG.read_text())
        s = cost.reference_comparison(data, 15)
        self.assertAlmostEqual(s["us_price"], .0786)
        self.assertAlmostEqual(s["cn_price_range"][0], .35/6.7894)
        self.assertAlmostEqual(s["cn_price_range"][1], .365/6.7894)
        self.assertIsNone(s["cn_price"])
        self.assertEqual(s["score_range"], [40, 40])
        self.assertEqual(s["state"], "WATCH")
        self.assertEqual(cost.reference_comparison(data, None)["score"], 40)
        self.assertEqual(cost.reference_comparison(data, 99)["score"], 40)
        for value in (0, -1, True, None, float("nan")):
            bad = deepcopy(data)
            bad["fx"]["cny_per_usd"] = value
            self.assertFalse(cost.reference_comparison(bad,15)["available"])
        for rows in (data["rows"][:-1], data["rows"]+[data["rows"][0]]):
            self.assertFalse(cost.reference_comparison(dict(data,rows=rows),15)["available"])
        wide = deepcopy(data)
        wide["rows"][0]["low"] = .01
        self.assertFalse(cost.reference_comparison(wide,15)["available"])

    def test_new_ratio_band_exact_boundaries_and_invalids(self):
        for ratio, expected in ((.8,("SAFE",15)),(.799999,("WATCH",40)),(.6,("WATCH",40)),(.599999,("WARNING",60)),(.4,("WARNING",60)),(.399999,("CRITICAL",85)),(1.5,("SAFE",15))):
            self.assertEqual(cost.ratio_rating(ratio),expected)
        for value in (0,-1,True,None,float("nan"),float("inf")):
            self.assertIsNone(cost.ratio_rating(value))


if __name__ == "__main__":
    unittest.main()
