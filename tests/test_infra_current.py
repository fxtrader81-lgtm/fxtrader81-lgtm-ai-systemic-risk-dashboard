from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from core import infra_updates as updates
from core.infra_current import load_infra, score_infra
from energy_market_fixture import MARKET_SNAPSHOT


class InfraCurrentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"infra.sqlite3"

    def test_verified_inputs_approved_48_scenario_is_not_a_mean(self):
        s=load_infra(self.path)
        self.assertEqual(s["inputs"]["interconnection_queue_months"],61)
        self.assertEqual(s["inputs"]["pjm_reserve_margin_pct"],26.2)
        self.assertEqual(s["inputs"]["ercot_reserve_margin_pct"],67.9)
        self.assertEqual(s["inputs"]["transformer_lead_time_months"],48)
        self.assertEqual(s["score"],75)
        self.assertTrue(s["available"])
        self.assertEqual(s["scenario"]["kind"],"upper_bound_stress_scenario")
        self.assertIn("不是平均交期",s["method_note"])
        self.assertIsNone(s["facts"]["transformer"]["period"])
        self.assertIn("口径断点",s["method_note"])
        before=updates.history(self.path)["input_versions"]
        load_infra(self.path)
        self.assertEqual(updates.history(self.path)["input_versions"],before)

    def test_original_formula_parity_missing_or_invalid_never_imputed(self):
        for q in (12,24,43,61):
            for t in (12,24,36,48):
                for a,b in ((16.5,12.8),(26.2,67.9),(0,0)):
                    inputs=dict(interconnection_queue_months=q,transformer_lead_time_months=t,pjm_reserve_margin_pct=a,ercot_reserve_margin_pct=b)
                    clamp=lambda x:max(0,min(100,x))
                    self.assertEqual(score_infra(inputs),round(clamp((q-12)/36*100)*.45+clamp((t-12)/36*100)*.30+clamp((20-(a+b)/2)/12*100)*.25,1))
                    for key in inputs:
                        self.assertIsNone(score_infra(dict(inputs,**{key:None})))
                        self.assertIsNone(score_infra(dict(inputs,**{key:float('nan')})))

    def test_overview_missing_uses_same_provider_no_old_score(self):
        from core.factor_registry import _straw4
        with patch("core.factor_registry.load_infra",return_value={"available":False}),patch("core.factor_registry._history") as fetch:
            result=_straw4()
        self.assertIsNone(result["score"])
        fetch.assert_not_called()

    def test_new_unparsed_facts_do_not_reuse_seed_and_failure_keeps_period(self):
        record={"id":"new-report","source_id":"queue","url":"official", "extracted":{"kind":"unparsed"}}
        checks={"checks":[{"sources":[{"source_id":"queue","status":"ok","evidence_id":"new-report"}]}],"evidence":[record]}
        with patch.object(updates,"history",return_value=checks):
            self.assertIsNone(load_infra(self.path)["inputs"]["interconnection_queue_months"])
        checks["checks"][0]["sources"][0]["status"]="failed"
        with patch.object(updates,"history",return_value=checks):
            s=load_infra(self.path)
        self.assertEqual(s["inputs"]["interconnection_queue_months"],61)
        self.assertEqual(s["facts"]["queue"]["period"],"2025")

    def test_page_restored_scenario_bar_total_and_history_old_inputs(self):
        from streamlit.testing.v1 import AppTest
        with patch.object(updates,"STORE",self.path), \
             patch("core.energy_market.load_energy_market",return_value=MARKET_SNAPSHOT), \
             patch("requests.get") as get:
            get.return_value.status_code=503
            at=AppTest.from_file("pages/straw4.py",default_timeout=20)
            at.session_state["straw_scores"]={"straw4":46.6}
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception),0)
        values="\n".join(m.value for m in at.markdown)
        self.assertIn("61mo",values)
        self.assertIn("夏季预期备用裕度（2026）：PJM 26.2% · ERCOT 67.9%",values)
        self.assertIn("48个月近似上限情景（非平均值）",values)
        self.assertIn("基础设施情景分：75/100",values)
        self.assertAlmostEqual(at.session_state["straw_scores"]["straw4"],50.1)
        fig=json.loads(at.get("plotly_chart")[0].proto.spec)
        self.assertEqual(fig["data"][0]["x"][0],75)
        self.assertTrue(fig["layout"].get("shapes"))
        records=updates.history(self.path)
        self.assertEqual(records["baselines"][0]["inputs"]["interconnection_queue_months"],43)
        self.assertEqual(records["baselines"][0]["inputs"]["transformer_lead_time_months"],36)
        self.assertEqual(records["input_versions"][0]["inputs"]["interconnection_queue_months"],61)
        exports=[d for d in at.get("download_button") if d.label=="下载基础设施检查记录与原始资料"]
        self.assertEqual(len(exports),1)

    def test_unknown_or_changed_extent_does_not_silently_change_scenario(self):
        for extracted in ({"kind":"unparsed"},{"kind":"qualitative_upper_extent","described_max_months":60}):
            checks={"checks":[{"sources":[{"source_id":"transformer","status":"ok","evidence_id":"new"}]}],
                    "evidence":[{"id":"new","source_id":"transformer","url":"official","extracted":extracted}]}
            with patch.object(updates,"history",return_value=checks):
                s=load_infra(self.path)
            self.assertIsNone(s["score"])
            self.assertIsNone(s["inputs"]["transformer_lead_time_months"])

    def test_overview_scenario_shared_75_and_existing_other_formulas(self):
        from core.factor_registry import _straw4
        import pandas as pd
        with patch("core.factor_registry.load_infra",return_value=load_infra(self.path)), \
             patch("core.factor_registry.load_cost",return_value={"available":True,"score":9}), \
             patch("core.factor_registry.energy_market.load_energy_market",return_value=MARKET_SNAPSHOT):
            result=_straw4()
        cost=9
        efficiency=35.5
        self.assertAlmostEqual(result["score"],round(.4*75+.25*cost+.2*efficiency+.15*20,1))


if __name__=="__main__":unittest.main()
