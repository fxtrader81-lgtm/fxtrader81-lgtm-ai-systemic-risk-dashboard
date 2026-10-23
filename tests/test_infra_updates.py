import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from core import infra_updates as infra

INPUTS = {"interconnection_queue_months":43,"transformer_lead_time_months":36,
          "pjm_reserve_margin_pct":16.5,"ercot_reserve_margin_pct":12.8,"updated":"2025-01"}
NOW = datetime(2026,10,20,18,tzinfo=timezone.utc)


def fixture(source, text="same"):
    content = {"source_id":source["id"],"url":source["url"],"text":text,
               "document_links":[],"parser_version":1}
    return dict(content, id=sha256(infra._json(content).encode()).hexdigest(),raw_html="<p>source</p>")


class InfraUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"infra.sqlite3"

    def test_due_success_90day_boundary_and_manual_early_check(self):
        self.assertTrue(infra.reminder(infra.history(self.path), NOW)["due"])
        self.assertEqual(infra.check_sources(self.path, fixture, NOW)["status"],"success")
        state = infra.reminder(infra.history(self.path), NOW+timedelta(days=89))
        self.assertFalse(state["due"])
        self.assertEqual(state["next_due"],NOW+timedelta(days=90))
        self.assertTrue(infra.reminder(infra.history(self.path),NOW+timedelta(days=90))["due"])
        self.assertEqual(infra.check_sources(self.path,fixture,NOW+timedelta(days=1))["status"],"success")

    def test_content_dedup_separate_attempts_and_no_baseline_mutation(self):
        original = deepcopy(INPUTS)
        infra.record_baseline(INPUTS,self.path)
        infra.record_baseline(INPUTS,self.path)
        for day in range(3): infra.check_sources(self.path,fixture,NOW+timedelta(days=day))
        records=infra.history(self.path)
        self.assertEqual(len(records["evidence"]),3)
        self.assertEqual(len(records["checks"]),3)
        self.assertEqual(len(records["baselines"]),1)
        self.assertTrue(all(r["comparison"]=="unchanged" for r in records["checks"][0]["sources"]))
        self.assertEqual(records["baselines"][0]["inputs"],original)
        self.assertEqual(INPUTS,original)
        self.assertEqual(INPUTS["updated"],"2025-01")

    def test_changed_reverted_then_unchanged_not_false_new(self):
        for value in ("A","B","A","A"):
            infra.check_sources(self.path,lambda s:fixture(s,value),NOW)
        records=infra.history(self.path)
        self.assertEqual(len(records["evidence"]),6)
        self.assertTrue(all(r["comparison"]=="unchanged" for r in records["checks"][0]["sources"]))
        self.assertTrue(all(r["comparison"]=="changed" for r in records["checks"][1]["sources"]))

    def test_partial_failure_never_advances_success_and_is_retryable(self):
        infra.check_sources(self.path,fixture,NOW)
        def fail(source):
            if source["id"]=="reserve": raise RuntimeError("private error")
            return fixture(source,"changed")
        result=infra.check_sources(self.path,fail,NOW+timedelta(days=100))
        self.assertEqual(result["status"],"failed")
        records=infra.history(self.path)
        self.assertEqual(infra.reminder(records,NOW+timedelta(days=100))["last_success"],NOW)
        self.assertTrue(infra.reminder(records,NOW+timedelta(days=100))["due"])
        self.assertNotIn("private error",json.dumps(records))
        self.assertEqual(infra.check_sources(self.path,fixture,NOW+timedelta(days=100))["status"],"success")

    def test_cross_session_state_and_concurrent_click_guard_expired_retry(self):
        with infra._connect(self.path) as conn:
            conn.execute("INSERT INTO checks(started,status) VALUES (?, 'running')",(NOW.isoformat(),))
        fetch=Mock(side_effect=fixture)
        self.assertEqual(infra.check_sources(self.path,fetch,NOW)["status"],"busy")
        fetch.assert_not_called()
        self.assertEqual(infra.check_sources(self.path,fixture,NOW+timedelta(minutes=6))["status"],"success")
        self.assertEqual(infra.history(self.path)["checks"][1]["status"],"interrupted")
        self.assertFalse(infra.reminder(infra.history(self.path),NOW+timedelta(minutes=7))["due"])

    def test_http_errors_challenge_dynamic_shell_and_wrong_evidence_not_success(self):
        for text in ("<p>loading</p>", "<p>queue verify you are human"+" x"*300+"</p>"):
            response=Mock(url=infra.SOURCES[0]["url"],content=text.encode(),text=text)
            with patch.object(infra.requests,"get",return_value=response):
                with self.assertRaises(ValueError): infra.fetch_source(infra.SOURCES[0])
        def invalid(s): return dict(fixture(s),id="bad")
        self.assertEqual(infra.check_sources(self.path,invalid,NOW)["status"],"failed")
        self.assertIsNone(infra.reminder(infra.history(self.path),NOW)["last_success"])

    def test_official_page_text_and_document_link_capture(self):
        text='<nav>noise</nav><main>'+('queue original source '*30)+'<a href="/report2026.pdf?tracking=1#page=1">Report</a></main>'
        source=dict(infra.SOURCES[0],url="https://eta-publications.lbl.gov/summary")
        response=Mock(url=source["url"],content=text.encode(),text=text)
        with patch.object(infra.requests,"get",return_value=response):
            item=infra.fetch_source(source)
        self.assertNotIn("noise",item["text"])
        self.assertEqual(item["document_links"],["https://eta-publications.lbl.gov/report2026.pdf"])
        self.assertEqual(item["raw_html"],text)

    def test_page_original_formula_unchanged(self):
        tree=ast.parse(Path("pages/straw4.py").read_text())
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="compute_infra_score")
        from core.infra_current import score_infra
        namespace={"INFRA_DATA":INPUTS,"score_infra":score_infra}
        exec(compile(ast.Module(body=[f],type_ignores=[]),"infra","exec"),namespace)
        self.assertEqual(namespace["compute_infra_score"](),69.9)

    def test_numeric_bound_and_transformer_extent_are_not_point_estimates(self):
        exact=infra.extract_numeric_evidence("queue","The median project built in 2025 took 61 months from the interconnection request to commercial operations")
        self.assertEqual(exact["months"],61)
        self.assertIsNone(exact["score_input"])
        q=infra.extract_numeric_evidence("queue","median duration from IR to COD was over 5 years for projects built in 2025")
        self.assertEqual(q["months_gt"],60)
        self.assertIsNone(q["score_input"])
        t=infra.extract_numeric_evidence("transformer","Large transformers for substations and generators have lead times growing from three to as much as four years")
        self.assertEqual(t["described_max_months"],48)
        self.assertIsNone(t["period"])
        self.assertIsNone(t["score_input"])

    def test_nerc_current_column_not_prior_reference_or_other_region(self):
        text=" ".join(f"{region} Demand, Resource, and Reserve Margins 2025 SRA 2026 SRA Net Internal Demand 100 100 Anticipated Resources 100 {capacity} Anticipated Reserve Margin 0% {margin}% Reference Margin Level 18.6%" for region,capacity,margin in [("PJM",126.2,26.2),("Texas RE-ERCOT",167.9,67.9)])
        # Report MW values are integers; use a 1000 MW denominator for exact fixtures.
        text=text.replace("Demand 100 100", "Demand 1000 1000").replace("Resources 100 126.2", "Resources 1000 1262").replace("Resources 100 167.9", "Resources 1000 1679")
        result=infra.extract_numeric_evidence("reserve",text)
        self.assertEqual([r["anticipated_margin_pct"] for r in result["rows"]],[26.2,67.9])
        self.assertIsNone(result["score_input"])
        with self.assertRaises(infra.SourceReadError):
            infra.extract_numeric_evidence("reserve",text.replace("26.2%","10%"))
        self.assertEqual(infra.extract_numeric_evidence("reserve",text.replace("2026 SRA","2027 SRA"))["kind"],"unparsed")

    def test_panel_default_collapsed_button_retry_and_export(self):
        from streamlit.testing.v1 import AppTest
        script='''from components.infra_update_panel import render_infra_updates
from test_infra_updates import INPUTS
render_infra_updates(INPUTS)
'''
        with patch.object(infra,"STORE",self.path),patch.object(infra,"fetch_source",side_effect=fixture) as fetch:
            at=AppTest.from_string(script)
            at.session_state["download_owner_authenticated"] = True
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertFalse(at.expander[0].proto.expanded)
            fetch.assert_not_called()
            self.assertEqual(len(at.button),1)
            at.button[0].click().run()
            self.assertEqual(len(at.exception),0)
            self.assertEqual(fetch.call_count,3)
            self.assertFalse(at.button[0].disabled)
            self.assertEqual(len(at.success),1)
            self.assertEqual(len(at.get("download_button")),1)
            self.assertNotIn("建议检查更新","\n".join(m.value for m in at.markdown))
            at.run()
            self.assertEqual(fetch.call_count,3)
            self.assertEqual(len(infra.history(self.path)["checks"]),1)

    def test_scoped_dark_states_and_normal_flow(self):
        css=Path("styles/pages.css").read_text().split("/* Factor 04 source management:")[1].split("/* Factor 03")[0]
        for token in ("st-key-infra_updates","stDownloadButton","stButton","details[open]",":hover, :focus, :active","focus-visible","line-height: 1.65","var(--text-soft)","var(--bg-input)"):
            self.assertIn(token,css)

    def test_full_energy_page_offline_error_state_keeps_old_score(self):
        from streamlit.testing.v1 import AppTest
        response=Mock(status_code=503)
        from energy_market_fixture import MARKET_SNAPSHOT
        with patch.object(infra,"STORE",self.path), \
             patch("core.energy_market.load_energy_market",return_value=MARKET_SNAPSHOT), \
             patch("requests.get",return_value=response):
            at=AppTest.from_file("pages/straw4.py",default_timeout=20).run()
        self.assertEqual(len(at.exception),0)
        self.assertIn("基础设施约束｜数据更新管理",[e.label for e in at.expander])
        self.assertEqual(len(infra.history(self.path)["checks"]),0)
        values="\n".join(m.value for m in at.markdown)
        self.assertIn("61mo",values)
        self.assertIn("PJM 26.2%",values)
        self.assertIn("ERCOT 67.9%",values)
        self.assertIn("48个月近似上限情景（非平均值）",values)
        self.assertAlmostEqual(at.session_state["straw_scores"]["straw4"],50.1)


if __name__=="__main__": unittest.main()
