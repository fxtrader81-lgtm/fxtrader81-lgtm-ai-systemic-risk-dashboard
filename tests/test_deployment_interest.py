import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import deployment_interest as deployment


def snapshot(stars=(100000, 150000, 160000), missing=False):
    rows = [{"name": name, "repo": repo, "expected_id": rid, "id": rid,
             "full_name": repo, "stars": count, "reason": None,
             "source_url": "https://github.com/"+repo,
             "api_url": "https://api.github.com/repos/"+repo}
            for (name, repo, rid), count in zip(deployment.REPOS, stars)]
    if missing:
        rows[1].update(stars=None, reason="HTTP 403")
    return deployment.make_snapshot(rows, "2026-10-19T12:00:00+00:00")


class DeploymentInterestTests(unittest.TestCase):
    def tearDown(self):
        deployment.load_deployment.clear()

    def test_original_thresholds_scores_and_weight(self):
        for stars, proxy, score, state in [
                (0,30,100/18,"SAFE"),(149999,30,100/18,"SAFE"),
                (150000,80,100/3,"WATCH"),(299999,80,100/3,"WATCH"),
                (300000,140,200/3,"WARNING"),(499999,140,200/3,"WARNING"),
                (500000,220,100,"CRITICAL")]:
            m=deployment.measure(stars)
            self.assertEqual(m["proxy_value"],proxy)
            self.assertAlmostEqual(m["score"],score)
            self.assertEqual(m["state"],state)
            self.assertAlmostEqual(m["contribution"],score*.3)

    def test_invalid_counts_not_coerced_to_zero(self):
        for value in (None,True,-1,1.2,"10",float("nan")):
            with self.assertRaises(ValueError): deployment.measure(value)

    def test_fixed_three_and_canonical_migration_no_duplicate_count(self):
        self.assertEqual(len(deployment.REPOS),3)
        self.assertEqual(len({r[2] for r in deployment.REPOS}),3)
        self.assertIn(("llama.cpp","ggml-org/llama.cpp",612354784),deployment.REPOS)
        result=snapshot()
        self.assertEqual(result["metrics"]["total_stars"],410000)
        self.assertEqual(result["coverage"],3)
        self.assertNotIn("lmstudio",str(result["rows"]))

    def test_partial_does_not_score_remaining_repos(self):
        result=snapshot(missing=True)
        self.assertFalse(result["available"])
        self.assertEqual(result["coverage"],2)
        self.assertIsNone(result["metrics"])

    def test_schema_count_missing_invalid_and_identity_failure(self):
        original=snapshot()["rows"]
        for update in [{"stars":None},{"stars":True},{"stars":-1},{"stars":1.2},
                       {"id":0},{"id":True},{"full_name":"other/repo"},{"full_name":None}]:
            rows=copy.deepcopy(original);rows[0].update(update)
            result=deployment.make_snapshot(rows,"time")
            self.assertIsNone(result["metrics"])
            self.assertIsNone(result["rows"][0]["stars"])

    def test_changed_or_duplicate_sample_rejected(self):
        rows=snapshot()["rows"]
        with self.assertRaises(ValueError): deployment.make_snapshot(rows[:2],"time")
        with self.assertRaises(ValueError): deployment.make_snapshot([rows[0]]*3,"time")

    def test_zero_counts_valid_and_no_growth_scoring(self):
        result=snapshot((0,0,0))
        self.assertTrue(result["available"])
        self.assertEqual(result["metrics"]["proxy_value"],30)
        self.assertNotIn("growth_pct",result["metrics"])
        self.assertIn("真实增长率",result["limitation"])

    def test_http_failure_has_status_and_no_fake_stars(self):
        for status in (403,404,429,500):
            response=SimpleNamespace(status_code=status)
            with patch("requests.get",return_value=response):
                row=deployment._fetch_repo(deployment.REPOS[0])
            self.assertIn(str(status),row["reason"])
            self.assertIsNone(row["stars"])

    def test_timeout_and_malformed_json_explained(self):
        for error in (deployment.requests.Timeout(),ValueError()):
            with patch("requests.get",side_effect=error):
                row=deployment._fetch_repo(deployment.REPOS[0])
            self.assertIn("读取失败",row["reason"])

    def test_history_append_dedup_failure_keeps_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"history.sqlite3"
            original=snapshot();deployment.archive(original,path)
            deployment.archive(dict(original,checked_at="2026-10-19T13:00:00+00:00"),path)
            self.assertEqual(len(deployment.history(path)),1)
            deployment.archive(snapshot(missing=True),path)
            self.assertEqual(len(deployment.history(path)),2)
            self.assertIn(original,deployment.history(path))

    def test_fetch_cache_and_refetch_only_on_clear(self):
        rows=snapshot()["rows"]
        def fetch(spec): return next(r for r in rows if r["repo"]==spec[1])
        with tempfile.TemporaryDirectory() as tmp, patch.object(deployment,"STORE",Path(tmp)/"history.sqlite3"), patch.object(deployment,"_fetch_repo",side_effect=fetch) as source:
            deployment.load_deployment.clear()
            result=deployment.load_deployment()
            self.assertEqual(source.call_count,3)
            self.assertEqual(result["coverage"],3)
            deployment.load_deployment()
            self.assertEqual(source.call_count,3)
            deployment.load_deployment.clear()
            deployment.load_deployment()
            self.assertEqual(source.call_count,6)

    def test_overview_uses_same_deployment_score(self):
        from core.factor_registry import _straw2
        with patch("core.factor_registry.current_capability_snapshot",return_value={"release":"test","metrics":{"score":50}}), patch("core.factor_registry.load_prices",return_value={"available":False}), patch("core.factor_registry.load_deployment",return_value=snapshot()), patch("core.factor_registry.load_ecology",return_value={"available":False}):
            result=_straw2()
        self.assertEqual(result["coverage"],50)
        self.assertEqual(result["score"],60)

    def test_page_missing_deployment_and_independent_refresh_preserve_other_data(self):
        from streamlit.testing.v1 import AppTest
        from core import capability_gap as cap
        from core import capability_cohort as cohort
        full=snapshot()
        def response(url, **kwargs):
            repo=url.split("/api/models/")[1]
            return SimpleNamespace(status_code=200,json=lambda:{"id":repo,"author":repo.split("/")[0],"private":False,"downloads":300000,"likes":100})
        price={"coverage":6,"available":True,"checked_at":"test","basis":"test", "rows":[],
               "metrics":{"closed_avg":10,"open_avg":1,"ratio":10,"compression":90,"score":100,"state":"CRITICAL","contribution":35}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(cap,"STORE",Path(tmp)/"cap.sqlite3"), patch.object(deployment,"STORE",Path(tmp)/"deployment.sqlite3"), patch("core.ecology_downloads.STORE",Path(tmp)/"ecology.sqlite3"), patch("core.model_prices.load_prices",return_value=price), patch("core.model_prices.get_selected_prices.clear") as clear_prices, patch("core.model_prices.history",return_value=[]), patch("requests.get",side_effect=response), patch.object(deployment,"load_deployment",return_value=full) as load, patch.object(cohort,"fetch_latest_snapshot") as capability_fetch:
            from core.ecology_downloads import get_selected_downloads
            get_selected_downloads.clear()
            at=AppTest.from_file("pages/straw2.py",default_timeout=30).run()
            self.assertEqual(len(at.exception),0)
            self.assertEqual(at.session_state["straw_scores"]["straw2"],71.3)
            labels=[e.label for e in at.expander]
            self.assertIn("部署动能",[t.label for t in at.tabs])
            for title in ("本期数据与计算说明","历史记录与原始资料"):
                self.assertIn(title,labels)
                self.assertFalse(next(e for e in at.expander if e.label==title).proto.expanded)
            before=cap.current_snapshot()
            self.assertNotIn("refresh_deployment_only", [b.key for b in at.button])
            at.run()
            self.assertEqual(len(at.exception),0)
            capability_fetch.assert_not_called()
            clear_prices.assert_not_called()
            self.assertEqual(cap.current_snapshot(),before)
            load.return_value=snapshot(missing=True)
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertTrue(any('Deployment evidence incomplete' in m.value for m in at.markdown))
            self.assertNotIn("straw2",at.session_state["straw_scores"])
            values=json.loads(at.get("plotly_chart")[0].proto.spec)["data"][0]["x"]
            self.assertIsNone(values[2])
            self.assertEqual(values[1],100)


if __name__ == "__main__": unittest.main()
