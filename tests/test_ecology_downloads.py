import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import ecology_downloads as ecology
from core.capability_cohort import SEED


def snapshot(downloads=(1_000_000,25_000,1_000_000),missing=False):
    cap=json.loads(SEED.read_text())
    key,selection=ecology.selection_request(cap)
    rows=[]
    for item,count in zip(json.loads(selection),downloads):
        repo=ecology.model_repo(item)
        rows.append(dict(item,repo=repo,source_url="https://huggingface.co/"+repo,api_url="https://huggingface.co/api/models/"+repo,
            downloads=count,reason=None,raw={"id":repo,"author":repo.split("/")[0],"private":False,"downloads":count,"sha":"a"*40}))
    if missing: rows[0].update(downloads=None,reason="HTTP 403")
    return ecology.make_snapshot(rows,key,"2026-10-19T12:00:00+00:00")


class EcologyDownloadsTests(unittest.TestCase):
    def tearDown(self): ecology.get_selected_downloads.clear()

    def test_current_three_exact_official_model_repos(self):
        rows=snapshot()["rows"]
        self.assertEqual([r["company"] for r in rows],["DeepSeek","Alibaba","Moonshot AI"])
        self.assertEqual([r["repo"] for r in rows],["deepseek-ai/DeepSeek-V4.1-Flash","Qwen/Qwen3.8-2.4T-A95B","moonshotai/Kimi-K3"])
        self.assertEqual(snapshot()["metrics"]["total_downloads"],2025000)
        self.assertEqual(snapshot()["metrics"]["score"],65)

    def test_old_thresholds_weight_and_boundaries(self):
        for count,score,state in [(0,15,"SAFE"),(499999,15,"SAFE"),(500000,40,"WATCH"),(1999999,40,"WATCH"),
                                  (2000000,65,"WARNING"),(7999999,65,"WARNING"),(8000000,85,"CRITICAL")]:
            result=ecology.measure(count)
            self.assertEqual(result["score"],score)
            self.assertEqual(result["state"],state)
            self.assertEqual(result["contribution"],score*.15)

    def test_invalid_downloads_never_coerced_to_zero(self):
        for value in (None,True,-1,1.5,"10",float("nan")):
            with self.assertRaises(ValueError): ecology.measure(value)
            rows=copy.deepcopy(snapshot()["rows"]);rows[0]["raw"]["downloads"]=value
            result=ecology.make_snapshot(rows,"key","time")
            self.assertEqual(result["coverage"],2)
            self.assertIsNone(result["metrics"])

    def test_partial_failure_no_remaining_two_or_old_default_score(self):
        result=snapshot(missing=True)
        self.assertEqual(result["coverage"],2)
        self.assertFalse(result["available"])
        self.assertIsNone(result["metrics"])
        self.assertTrue(snapshot((0,0,0))["available"])

    def test_unknown_publisher_missing_link_and_unsafe_url_rejected(self):
        row=snapshot()["rows"][0]
        for url in (None,"http://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash", "https://evil.test/deepseek-ai/model",
                    "https://huggingface.co/other/DeepSeek-V4.1-Flash", "https://huggingface.co/deepseek-ai/model?token=x",
                    "https://huggingface.co/deepseek-ai/model/blob/main/file", "https://huggingface.co/deepseek-ai/model#file"):
            with self.assertRaises(ValueError): ecology.model_repo(dict(row,huggingface=url))
        with self.assertRaises(ValueError): ecology.model_repo(dict(row,company="Unknown"))

    def test_new_model_follows_metadata_not_old_or_similar_repo(self):
        cap=json.loads(SEED.read_text()); model=cap["selected"]["open"][0]["model"]
        metadata=ecology.parse_metadata(cap["raw_metadata"])
        metadata[model]["huggingface"]="https://huggingface.co/deepseek-ai/Reviewed-New-Model"
        with patch.object(ecology,"parse_metadata",return_value=metadata):
            _,selected=ecology.selection_request(cap)
        self.assertEqual(ecology.model_repo(json.loads(selected)[0]),"deepseek-ai/Reviewed-New-Model")

    def test_bad_model_identity_author_and_private_data_unavailable(self):
        for update in ({"id":"other/model"},{"author":"other"},{"private":True},{"private":None}):
            rows=copy.deepcopy(snapshot()["rows"]);rows[0]["raw"].update(update)
            self.assertFalse(ecology.make_snapshot(rows,"key","time")["available"])

    def test_three_distinct_platforms_required(self):
        rows=snapshot()["rows"]
        with self.assertRaises(ValueError): ecology.make_snapshot(rows[:2],"key","time")
        with self.assertRaises(ValueError): ecology.make_snapshot([rows[0]]*3,"key","time")
        cap=json.loads(SEED.read_text());cap["selected"]["open"]*=2
        with self.assertRaises(ValueError): ecology.selection_request(cap)

    def test_http_timeout_and_bad_json_are_explicit(self):
        item=snapshot()["rows"][0]
        for status in (401,403,404,429,500):
            with patch("requests.get",return_value=SimpleNamespace(status_code=status)):
                result=ecology._fetch_model(item)
            self.assertIn(str(status),result["reason"])
            self.assertIsNone(result["downloads"])
        with patch("requests.get",side_effect=ecology.requests.Timeout()):
            self.assertIn("Timeout",ecology._fetch_model(item)["reason"])
        with patch("requests.get",return_value=SimpleNamespace(status_code=200,json=lambda:[])):
            self.assertIn("不是对象",ecology._fetch_model(item)["reason"])

    def test_local_history_dedup_preserves_valid_record_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"eco.sqlite3";first=snapshot()
            ecology.archive(first,path);ecology.archive(dict(first,checked_at="2026-10-19T13:00:00+00:00"),path)
            self.assertEqual(len(ecology.history(path)),1)
            ecology.archive(snapshot(missing=True),path)
            self.assertIn(first,ecology.history(path))
            self.assertEqual(len(ecology.history(path)),2)
        self.assertEqual(len(ecology.LEGACY["detail_models"]),4)
        self.assertEqual(len(ecology.LEGACY["overview_models"]),3)
        self.assertIn("不回填",ecology.LEGACY["note"])

    def test_cohort_cache_key_changes_and_manual_refresh(self):
        cap=json.loads(SEED.read_text());rows=snapshot()["rows"]
        def fetch(item):return next(r for r in rows if r["model"]==item["model"])
        with tempfile.TemporaryDirectory() as tmp,patch.object(ecology,"STORE",Path(tmp)/"eco.sqlite3"),patch.object(ecology,"_fetch_model",side_effect=fetch) as source:
            ecology.get_selected_downloads.clear();ecology.load_ecology(cap)
            self.assertEqual(source.call_count,3)
            ecology.load_ecology(cap);self.assertEqual(source.call_count,3)
            key,selection=ecology.selection_request(cap)
            ecology.get_selected_downloads(key+"new",selection);self.assertEqual(source.call_count,6)
            ecology.get_selected_downloads.clear();ecology.load_ecology(cap);self.assertEqual(source.call_count,9)

    def test_overview_uses_same_four_component_inputs(self):
        from core.factor_registry import _straw2
        cap=json.loads(SEED.read_text())
        with patch("core.factor_registry.current_capability_snapshot",return_value=cap),patch("core.factor_registry.load_prices",return_value={"available":True,"metrics":{"score":100}}),patch("core.factor_registry.load_deployment",return_value={"available":True,"metrics":{"score":200/3}}),patch("core.factor_registry.load_ecology",return_value=snapshot()) as load:
            result=_straw2()
        load.assert_called_once_with(cap)
        expected=round(cap["metrics"]["score"]*.2+100*.35+(200/3)*.3+65*.15,1)
        self.assertEqual(result["score"],expected)
        self.assertEqual(result["coverage"],100)

    def test_page_incomplete_ecology_and_independent_refresh(self):
        from streamlit.testing.v1 import AppTest
        from core import capability_gap as cap
        from core import capability_cohort as cohort
        from test_deployment_interest import snapshot as deployment_snapshot
        price={"coverage":6,"available":True,"checked_at":"test","basis":"test","rows":[],
               "metrics":{"closed_avg":10,"open_avg":1,"ratio":10,"compression":90,"score":100,"state":"CRITICAL","contribution":35}}
        with tempfile.TemporaryDirectory() as tmp,patch.object(cap,"STORE",Path(tmp)/"cap.sqlite3"),patch.object(ecology,"STORE",Path(tmp)/"eco.sqlite3"),patch("core.model_prices.load_prices",return_value=price),patch("core.model_prices.history",return_value=[]),patch("core.deployment_interest.load_deployment",return_value=deployment_snapshot()) as deployment_load,patch("core.deployment_interest.history",return_value=[]),patch("core.model_prices.get_selected_prices.clear") as clear_price,patch("core.ecology_downloads.load_ecology",return_value=snapshot()) as load,patch.object(ecology,"get_selected_downloads") as cached,patch.object(cohort,"fetch_latest_snapshot") as fetch:
            at=AppTest.from_file("pages/straw2.py",default_timeout=30)
            at.session_state["download_owner_authenticated"] = True
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertEqual(at.session_state["straw_scores"]["straw2"],75)
            self.assertEqual([t.label for t in at.tabs],["检测逻辑","指标与历史证据","数据覆盖与来源"])
            evidence_tab=next(t for t in at.tabs if t.label=="指标与历史证据")
            evidence_expanders=[e.label for e in evidence_tab.get("expander")]
            self.assertTrue(any(label.startswith("2026Q4进行中｜") for label in evidence_expanders))
            self.assertIn("季度历史快照｜最近归档2026Q3 · 总分75.0 · CRITICAL",evidence_expanders)
            downloads=[b.label for b in at.get("download_button")]
            self.assertEqual(downloads,["下载可阅读版（HTML）","下载完整原始资料（JSON）"])
            before=cap.current_snapshot()
            self.assertNotIn("refresh_ecology_only", [b.key for b in at.button])
            at.run()
            self.assertEqual(len(at.exception),0)
            cached.clear.assert_not_called()
            fetch.assert_not_called();clear_price.assert_not_called();deployment_load.clear.assert_not_called()
            self.assertEqual(cap.current_snapshot(),before)
            load.return_value=snapshot(missing=True);at.run()
            self.assertEqual(len(at.exception),0)
            self.assertTrue(any("Ecology evidence incomplete" in m.value for m in at.markdown))
            self.assertNotIn("straw2",at.session_state["straw_scores"])
            scores=json.loads(at.get("plotly_chart")[0].proto.spec)["data"][0]["x"]
            self.assertIsNone(scores[3]);self.assertEqual(scores[1],100)


if __name__=="__main__": unittest.main()
