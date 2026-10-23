from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core import power_infrastructure as power
from test_reit_pressure import row, snapshot as reit_snapshot
from test_liquid_signal import snapshot as liquid_snapshot


def snapshot(missing=False):
    rows=[row("NEE"),row("SO",80.,105.)]
    if missing: rows[1]["annual_revenue"]=[]
    return power.make_snapshot(rows,"2026-10-20T18:00:00+00:00")


class PowerInfrastructureTests(unittest.TestCase):
    def tearDown(self): power.get_power_snapshot.clear()

    def test_original_growth60_price40_round_state_and_weight(self):
        s=snapshot()
        self.assertEqual([r["metrics"]["company_score"] for r in s["rows"]],[76,41])
        self.assertEqual(s["metrics"]["unrounded_score"],58.5)
        self.assertEqual(s["metrics"]["score"],58)
        self.assertEqual(s["metrics"]["state"],"WARNING")
        self.assertAlmostEqual(s["metrics"]["contribution"],8.7)

    def test_original_growth_and_price_boundaries(self):
        for g,score in [(-100,15),(0,15),(2.99,15),(3,35),(7.99,35),(8,60),(14.99,60),(15,80)]:
            self.assertEqual(power.score_company(g,0)["growth_score"],score)
        for p,score in [(0,15),(25,15),(25.01,30),(50,30),(50.01,50),(75,50),(75.01,70),(100,70)]:
            self.assertEqual(power.score_company(0,p)["price_score"],score)

    def test_complete_original_formula_parity_and_distinct_state_cutoffs(self):
        for g in [-20,0,2,3,7,8,14,15,100]:
            for p in [0,25,30,50,60,75,90,100]:
                gs=15 if g<3 else 35 if g<8 else 60 if g<15 else 80
                ps=70 if p>75 else 50 if p>50 else 30 if p>25 else 15
                self.assertEqual(power.score_company(g,p)["company_score"],gs*.6+ps*.4)
        for score,state in [(24.9,"SAFE"),(25,"WATCH"),(44.9,"WATCH"),(45,"WARNING"),(64.9,"WARNING"),(65,"CRITICAL")]:
            with patch.object(power,"score_company",return_value={"growth_score":0,"price_score":0,"company_score":score}):
                self.assertEqual(snapshot()["metrics"]["state"],state)

    def test_missing_one_company_or_revenue_never_fills30_or50(self):
        s=snapshot(missing=True)
        self.assertEqual(s["coverage"],1)
        self.assertIsNone(s["metrics"])
        self.assertFalse(s["available"])
        with self.assertRaises(ValueError): power.make_snapshot([row("NEE")],"time")
        with self.assertRaises(ValueError): power.make_snapshot([row("NEE"),row("NEE")],"time")

    def test_invalid_price_range_and_inputs_remain_unavailable(self):
        for update in ({"current_price":None},{"week52_low":100.,"week52_high":100.,"current_price":100.},
                       {"week52_high":float("nan")},{"price_date":None}):
            self.assertIsNone(power.make_snapshot([dict(row("NEE"),**update),row("SO")],"time")["metrics"])
        for g,p in [(None,0),(True,0),(0,None),(0,float("nan")),(0,101),(0,-1)]:
            with self.assertRaises(ValueError): power.score_company(g,p)

    def test_no_old_annual_substitution_no_quarterly_conversion(self):
        r=row("NEE")
        before=deepcopy(r)
        power.make_snapshot([r,row("SO")],"time")
        self.assertEqual(r,before)
        r["annual_revenue"][0]["revenue"]=None
        self.assertIsNone(power.make_snapshot([r,row("SO")],"time")["metrics"])
        r=row("NEE");r["annual_revenue"][1]["period_end"]="2025-09-30"
        self.assertIsNone(power.make_snapshot([r,row("SO")],"time")["metrics"])

    def test_total_revenue_proxy_and_legacy_methods_preserved(self):
        s=snapshot()
        self.assertIn("公司总营收",s["limitation"])
        self.assertIn("电网剩余容量",s["limitation"])
        self.assertIn("不能直接证明",s["limitation"])
        self.assertIn("减15",power.LEGACY_RULES["overview"])
        self.assertIn("返回30分",power.LEGACY_RULES["detail"])

    def test_cache_dedup_immutable_history_and_failure_not_fallback(self):
        power.get_power_snapshot.clear()
        with tempfile.TemporaryDirectory() as tmp,patch.object(power,"STORE",Path(tmp)/"power.sqlite3"),patch.object(power,"fetch_financial_row",side_effect=lambda t:row(t)) as fetch:
            current=power.load_power()
            before=power.history()
            self.assertEqual(power.load_power(),current)
            self.assertEqual(fetch.call_count,2)
            self.assertEqual(power.history(),before)
            fail=snapshot(missing=True);fail["checked_at"]="2099-01-01T00:00:00+00:00"
            power.archive(fail)
            self.assertIsNone(power.history()[0]["metrics"])
            self.assertEqual(power.history()[1],before[0])

    def test_overview_shared_score_and_missing_coverage_policy(self):
        from core.factor_registry import _straw3
        with patch("core.factor_registry.load_aof",return_value={"metrics":{"score":100,"aof":4.8}}),patch("core.factor_registry.load_reit",return_value=reit_snapshot()),patch("core.factor_registry.load_liquid",return_value=liquid_snapshot()),patch("core.factor_registry.load_power",return_value=snapshot()) as load:
            result=_straw3()
            self.assertEqual(result["score"],round(25+.35*42+.25*34+.15*58,1))
            self.assertEqual(result["coverage"],100)
            load.return_value=snapshot(missing=True)
            result=_straw3()
            self.assertEqual(result["coverage"],85)
            self.assertEqual(result["score"],round((25+.35*42+.25*34)/.85,1))
            self.assertIn("电力数据不完整，不计分",result["detail"])

    def test_full_page_score_matches_overview_and_missing_clears_old_total(self):
        from streamlit.testing.v1 import AppTest
        from core.factor_registry import _straw3
        with patch("core.reit_pressure.load_reit",return_value=reit_snapshot()),patch("core.reit_pressure.history",return_value=[]),patch("core.liquid_signal.load_liquid",return_value=liquid_snapshot()),patch("core.liquid_signal.history",return_value=[]),patch("core.power_infrastructure.load_power",return_value=snapshot()) as load,patch("core.power_infrastructure.history",return_value=[snapshot()]):
            at=AppTest.from_file("pages/straw3.py",default_timeout=30)
            at.session_state["download_owner_authenticated"] = True
            at.run()
            self.assertEqual(len(at.exception),0)
            expected=round(25+.35*42+.25*34+.15*58,1)
            self.assertEqual(at.session_state["straw_scores"]["straw3"],expected)
            text="\n".join(m.value for m in at.markdown)
            self.assertIn("分项58分",text)
            self.assertIn("非实际用电量或电网容量",text)
            self.assertIn("电力分项均分 < 25 · SAFE",text)
            evidence = next(t for t in at.tabs if t.label=="指标与历史证据")
            self.assertEqual([t.label for t in at.tabs],["检测逻辑","指标与历史证据","数据覆盖与来源"])
            evidence_expanders=[e.label for e in evidence.get("expander")]
            self.assertTrue(any(label.startswith("2026Q4进行中｜") for label in evidence_expanders))
            self.assertIn("季度历史快照｜最近归档2026Q3 · 总分58.1 · WARNING",evidence_expanders)
            downloads=[d.label for d in at.get("download_button")]
            self.assertEqual(downloads,["下载可阅读版（HTML）","下载完整原始资料（JSON）"])
            self.assertEqual(len(at.button),0)
            chart=json.loads(at.get("plotly_chart")[0].proto.spec)
            self.assertEqual(chart["data"][0]["y"],[15,25,60,80,120,200])
            self.assertEqual(chart["data"][1]["y"],[120])
            load.return_value=snapshot(missing=True)
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertNotIn("straw3",at.session_state["straw_scores"])
            self.assertTrue(any("电力相关企业必要数据不完整" in m.value for m in at.markdown))
            self.assertTrue(any("必要数据覆盖1/2" in m.value for m in at.markdown))


if __name__ == "__main__": unittest.main()
