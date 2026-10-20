import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from core import model_prices as prices
from core.capability_cohort import SEED


class ModelPriceTests(unittest.TestCase):
    def setUp(self):
        self.cap = json.loads(SEED.read_text())
        self.key, selection = prices.cohort_request(self.cap)
        self.selected = json.loads(selection)
        self.policy = json.loads(prices.POLICY.read_text())
        self.catalog = {"data": [{"id": self.policy["models"][r["model"]]["id"],
            "pricing": {"prompt": str(p/1_000_000), "completion": str(1000/1_000_000)}}
            for r,p in zip(self.selected, [10,20,30,1,2,3])]}

    def calc(self, catalog=None, selected=None):
        return prices.calculate_prices(selected or self.selected, catalog or self.catalog,
            self.policy, cohort_key=self.key, checked_at="2026-10-19T12:00:00+00:00")

    def test_three_company_equal_input_means_original_formula_output_not_scored(self):
        result = self.calc()
        m = result["metrics"]
        self.assertEqual(result["coverage"],6)
        self.assertEqual(m["closed_avg"],20)
        self.assertEqual(m["open_avg"],2)
        self.assertEqual(m["ratio"],10)
        self.assertEqual(m["compression"],90)
        self.assertEqual(m["score"],100)
        self.assertEqual(m["state"],"CRITICAL")
        changed=copy.deepcopy(self.catalog)
        changed["data"][0]["pricing"]["completion"]="999"
        self.assertEqual(self.calc(changed)["metrics"],m)

    def test_missing_no_partial_means_and_no_related_variant_substitution(self):
        catalog=copy.deepcopy(self.catalog)
        catalog["data"][0]["id"] += ":batch"
        result=self.calc(catalog)
        self.assertFalse(result["available"])
        self.assertEqual(result["coverage"],5)
        self.assertIsNone(result["metrics"])

    def test_unknown_new_model_no_fuzzy_matching(self):
        selected=copy.deepcopy(self.selected)
        selected[0]["model"] += "-new"
        self.assertFalse(self.calc(selected=selected)["available"])

    def test_qwen_alias_requires_exact_source_evidence(self):
        selected=copy.deepcopy(self.selected)
        next(r for r in selected if r["model"]=="qwen3.8-max")["evidence"]["huggingface"]="wrong"
        self.assertFalse(self.calc(selected=selected)["available"])

    def test_invalid_prices_and_duplicates_not_zero(self):
        for value in [None, "", "nan", "inf", "-1", True]:
            catalog=copy.deepcopy(self.catalog)
            catalog["data"][0]["pricing"]["prompt"]=value
            self.assertFalse(self.calc(catalog)["available"])
        catalog=copy.deepcopy(self.catalog)
        catalog["data"].append(catalog["data"][0])
        self.assertFalse(self.calc(catalog)["available"])

    def test_output_missing_still_input_complete_and_zero_is_valid(self):
        catalog=copy.deepcopy(self.catalog)
        catalog["data"][3]["pricing"]={"prompt":"0"}
        result=self.calc(catalog)
        self.assertTrue(result["available"])
        self.assertIsNone(result["rows"][3]["output_per_m"])
        self.assertEqual(result["rows"][3]["input_per_m"],0)

    def test_all_zero_closed_denominator_unavailable(self):
        catalog=copy.deepcopy(self.catalog)
        for row in catalog["data"][:3]: row["pricing"]["prompt"]="0"
        self.assertFalse(self.calc(catalog)["available"])

    def test_original_ratio_boundary_and_score_saturation_preserved(self):
        for ratio, state in [(71,"SAFE"),(70,"WATCH"),(46,"WATCH"),(45,"WARNING"),(26,"WARNING"),(25,"CRITICAL")]:
            catalog=copy.deepcopy(self.catalog)
            for r in catalog["data"][:3]: r["pricing"]["prompt"]="0.0001"
            for r in catalog["data"][3:]: r["pricing"]["prompt"]=str(ratio/1_000_000)
            self.assertEqual(self.calc(catalog)["metrics"]["state"],state)

    def test_immutable_history_dedup_and_no_overwrite_after_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"prices.sqlite3"
            first=self.calc(); prices.archive(first,path)
            again=dict(first,checked_at="2026-10-19T13:00:00+00:00"); prices.archive(again,path)
            self.assertEqual(len(prices.history(path)),1)
            failed=prices.calculate_prices(self.selected,{},self.policy,cohort_key=self.key,checked_at="2026-10-19T14:00:00+00:00",error="offline")
            prices.archive(failed,path)
            self.assertEqual(len(prices.history(path)),2)
            self.assertIn(first,prices.history(path))

    def test_fetch_errors_explicit_and_one_hour_cache_bound_to_cohort(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(prices,"STORE",Path(tmp)/"p.sqlite3"), patch("requests.get",side_effect=prices.requests.RequestException("offline")) as fetch:
            prices.get_selected_prices.clear()
            key,selected=prices.cohort_request(self.cap)
            policy=prices.POLICY.read_text()
            result=prices.get_selected_prices(key,selected,policy)
            self.assertFalse(result["available"])
            self.assertEqual(result["coverage"],0)
            prices.get_selected_prices(key,selected,policy)
            self.assertEqual(fetch.call_count,1)
            prices.get_selected_prices(key+"new",selected,policy)
            self.assertEqual(fetch.call_count,2)
            prices.get_selected_prices.clear()

    def test_page_complete_and_missing_prices_refresh_without_model_tests(self):
        from streamlit.testing.v1 import AppTest
        from core import capability_gap as cap
        from core import capability_cohort as cohort
        def response(url, **kwargs):
            if "github" in url:
                from core.deployment_interest import REPOS
                repo = url.split("/repos/")[1]
                rid = next(rid for _, name, rid in REPOS if name == repo)
                data = {"id": rid, "full_name": repo, "stargazers_count": 60000, "forks_count": 100, "watchers_count": 100}
            else:
                repo = url.split("/api/models/")[1]
                data = {"id": repo, "author": repo.split("/")[0], "private": False, "downloads": 300000, "likes": 100}
            return SimpleNamespace(status_code=200, json=lambda: data, raise_for_status=lambda: None)
        full=self.calc()
        missing_catalog=copy.deepcopy(self.catalog)
        missing_catalog["data"].pop()
        missing=self.calc(missing_catalog)
        with tempfile.TemporaryDirectory() as tmp, patch.object(cap,"STORE",Path(tmp)/"cap.sqlite3"), patch.object(prices,"STORE",Path(tmp)/"price.sqlite3"), patch("core.deployment_interest.STORE",Path(tmp)/"deployment.sqlite3"), patch("core.ecology_downloads.STORE",Path(tmp)/"ecology.sqlite3"), patch("requests.get",side_effect=response), patch("core.model_prices.load_prices",return_value=full) as load, patch.object(cohort,"fetch_latest_snapshot") as capability_fetch:
            from core.deployment_interest import load_deployment
            from core.ecology_downloads import get_selected_downloads
            load_deployment.clear()
            get_selected_downloads.clear()
            at=AppTest.from_file("pages/straw2.py",default_timeout=30).run()
            self.assertEqual(len(at.exception),0)
            self.assertTrue(any("10.0%" in m.value for m in at.markdown))
            labels = [e.label for e in at.expander]
            self.assertIn("价格压缩", [t.label for t in at.tabs])
            self.assertIn("本期数据与计算说明", labels)
            self.assertIn("历史记录与原始资料", labels)
            self.assertNotIn("价格压缩｜本期价格、计算说明与历史", labels)
            self.assertNotIn("已保存的价格采集记录", labels)
            for e in at.expander:
                if e.label in ("本期数据与计算说明", "历史记录与原始资料"):
                    self.assertFalse(e.proto.expanded)
            self.assertTrue(any(b.label=="下载本期价格与历史原始资料" for b in at.get("download_button")))
            before=cap.current_snapshot()
            self.assertNotIn("refresh_price_only", [b.key for b in at.button])
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertEqual(cap.current_snapshot(),before)
            capability_fetch.assert_not_called()
            load.return_value=missing
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertTrue(any('Price evidence incomplete' in m.value and 'N/A' in m.value for m in at.markdown))
            self.assertNotIn("straw2",at.session_state["straw_scores"])
            self.assertIsNone(json.loads(at.get("plotly_chart")[0].proto.spec)["data"][0]["x"][1])


if __name__ == "__main__":
    unittest.main()
