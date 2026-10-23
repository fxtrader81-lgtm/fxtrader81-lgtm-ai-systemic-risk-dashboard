from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from core import liquid_signal as liquid
from test_reit_pressure import row, snapshot as reit_snapshot


def snapshot(missing=False):
    rows=[row("VRT"),row("SMCI",80.,105.)]
    if missing: rows[1]["annual_revenue"]=[]
    return liquid.make_snapshot(rows,"2026-10-20T18:00:00+00:00")


class LiquidSignalTests(unittest.TestCase):
    def tearDown(self): liquid.get_liquid_snapshot.clear()

    def test_original_growth65_price35_round_state_weight(self):
        s=snapshot()
        self.assertEqual([r["metrics"]["company_score"] for r in s["rows"]],[47.5,20.5])
        self.assertEqual(s["metrics"]["score"],34)
        self.assertEqual(s["metrics"]["state"],"WATCH")
        self.assertEqual(s["metrics"]["contribution"],8.5)
        self.assertAlmostEqual(s["metrics"]["mean_growth"],12.5)

    def test_all_original_growth_and_price_boundaries(self):
        for g,score in [(-100,10),(0,10),(9.99,10),(10,30),(29.99,30),(30,55),(60,75),(100,90)]:
            self.assertEqual(liquid.score_company(g,0)["growth_score"],score)
        for p,score in [(0,20),(40,20),(40.01,40),(60,40),(60.01,60),(80,60),(80.01,80),(100,80)]:
            self.assertEqual(liquid.score_company(0,p)["price_score"],score)

    def test_original_formula_parity_across_complete_sample_grid(self):
        for g in [-50,0,9,10,20,30,59,60,99,100,150]:
            for p in [0,40,50,60,70,80,90,100]:
                gs=10 if g<10 else 30 if g<30 else 55 if g<60 else 75 if g<100 else 90
                ps=80 if p>80 else 60 if p>60 else 40 if p>40 else 20
                self.assertEqual(liquid.score_company(g,p)["company_score"],gs*.65+ps*.35)

    def test_state_uses_unrounded_mean_even_when_display_rounds_up(self):
        s=liquid.make_snapshot([row("VRT",80.,140.),row("SMCI",80.,140.)],"time")
        self.assertEqual(s["metrics"]["unrounded_score"],49.75)
        self.assertEqual(s["metrics"]["score"],50)
        self.assertEqual(s["metrics"]["state"],"WATCH")

    def test_missing_one_company_or_annual_period_does_not_score_remaining(self):
        s=snapshot(missing=True)
        self.assertEqual(s["coverage"],1)
        self.assertFalse(s["available"])
        self.assertIsNone(s["metrics"])
        self.assertIsNone(s["rows"][1]["metrics"])
        with self.assertRaises(ValueError): liquid.make_snapshot([row("VRT")],"time")
        with self.assertRaises(ValueError): liquid.make_snapshot([row("VRT"),row("VRT")],"time")

    def test_invalid_range_and_values_no_default_position50(self):
        for update in ({"current_price":None},{"current_price":100.,"week52_low":100.,"week52_high":100.},
                       {"week52_high":float("nan")},{"price_date":None}):
            s=liquid.make_snapshot([dict(row("VRT"),**update),row("SMCI")],"time")
            self.assertIsNone(s["metrics"])
        for g,p in [(None,0),(True,0),(0,None),(0,float("nan")),(0,101),(0,-1)]:
            with self.assertRaises(ValueError): liquid.score_company(g,p)

    def test_source_scope_total_company_revenue_not_liquid_segment(self):
        s=snapshot()
        self.assertIn("公司总营收",s["limitation"])
        self.assertIn("不是液冷业务单独收入",s["limitation"])
        self.assertIn("加速度",s["limitation"])
        self.assertIn("口径不同",liquid.LEGACY_RULES["overview"])
        self.assertTrue(all(r["business_source_url"].startswith("https://") for r in s["rows"]))

    def test_reuses_verified_date_and_latest_annual_fetch_without_mutation(self):
        original=row("VRT")
        before=deepcopy(original)
        liquid.make_snapshot([original,row("SMCI")],"time")
        self.assertEqual(original,before)
        latest_bad=row("VRT")
        latest_bad["annual_revenue"][0]["revenue"]=None
        self.assertIsNone(liquid.make_snapshot([latest_bad,row("SMCI")],"time")["metrics"])
        quarterly=row("VRT")
        quarterly["annual_revenue"][1]["period_end"]="2025-09-30"
        self.assertIsNone(liquid.make_snapshot([quarterly,row("SMCI")],"time")["metrics"])

    def test_cache_separate_history_dedup_and_failure_retention(self):
        liquid.get_liquid_snapshot.clear()
        with tempfile.TemporaryDirectory() as tmp,patch.object(liquid,"STORE",Path(tmp)/"liquid.sqlite3"),patch.object(liquid,"fetch_financial_row",side_effect=lambda t:row(t)) as fetch:
            s=liquid.load_liquid()
            before=liquid.history()
            self.assertEqual(liquid.load_liquid(),s)
            self.assertEqual(fetch.call_count,2)
            self.assertEqual(liquid.history(),before)
            failed=snapshot(missing=True)
            failed["checked_at"]="2026-10-20T23:00:00+00:00"
            liquid.archive(failed)
            records=liquid.history()
            self.assertIsNone(records[0]["metrics"])
            self.assertEqual(records[1],before[0])
            self.assertFalse((Path(tmp)/"reit.sqlite3").exists())

    def test_overview_uses_shared_score_and_keeps_missing_coverage_policy(self):
        from core.factor_registry import _straw3
        close=pd.DataFrame({t:[10,20,15] for t in ("NEE","SO")})
        with patch("core.factor_registry.load_power",return_value={"available":True,"metrics":{"score":35}}),patch("core.factor_registry._history",return_value=close),patch("core.factor_registry.load_aof",return_value={"metrics":{"score":100,"aof":4.8}}),patch("core.factor_registry.load_reit",return_value=reit_snapshot()),patch("core.factor_registry.load_liquid",return_value=snapshot()) as load:
            s=_straw3()
            self.assertEqual(s["score"],round(25+.35*42+.25*34+.15*35,1))
            self.assertEqual(s["coverage"],100)
            load.return_value=snapshot(missing=True)
            s=_straw3()
            self.assertEqual(s["coverage"],75)
            self.assertEqual(s["score"],round((25+.35*42+.15*35)/.75,1))

    def test_page_current_history_download_missing_clears_total_and_preserves_chart(self):
        from streamlit.testing.v1 import AppTest
        from test_power_infrastructure import snapshot as power_snapshot
        prices=pd.DataFrame({"Close":[100.,110.,105.],"High":[102.,112.,107.],"Low":[98.,108.,103.]})
        income=pd.DataFrame({pd.Timestamp("2025-12-31"):[120.,30.],pd.Timestamp("2024-12-31"):[100.,20.]},index=["Total Revenue","Operating Income"])
        class Ticker:
            financials=income
            def history(self,**kwargs): return prices
        with patch("core.reit_pressure.load_reit",return_value=reit_snapshot()),patch("core.reit_pressure.history",return_value=[]),patch("core.power_infrastructure.load_power",return_value=power_snapshot()),patch("core.power_infrastructure.history",return_value=[]),patch("core.liquid_signal.load_liquid",return_value=snapshot()) as load,patch("core.liquid_signal.history",return_value=[snapshot()]),patch("yfinance.Ticker",return_value=Ticker()):
            at=AppTest.from_file("pages/straw3.py",default_timeout=30)
            at.session_state["download_owner_authenticated"] = True
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertIn("straw3",at.session_state["straw_scores"])
            text="\n".join(m.value for m in at.markdown)
            self.assertIn("分项34分",text)
            self.assertIn("非液冷业务收入",text)
            self.assertEqual([t.label for t in at.tabs],["检测逻辑","指标与历史证据","数据覆盖与来源"])
            labels=[e.label for e in at.expander]
            self.assertTrue(any(label.startswith("2026Q4进行中｜") for label in labels))
            self.assertIn("季度历史快照｜最近归档2026Q3 · 总分58.1 · WARNING",labels)
            self.assertEqual([d.label for d in at.get("download_button")],
                             ["下载可阅读版（HTML）","下载完整原始资料（JSON）"])
            self.assertEqual(len(at.button),0)
            chart=json.loads(at.get("plotly_chart")[0].proto.spec)
            self.assertEqual(chart["data"][0]["y"],[15,25,60,80,120,200])
            self.assertEqual(chart["data"][1]["y"],[120])
            load.return_value=snapshot(missing=True)
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertNotIn("straw3",at.session_state["straw_scores"])
            text="\n".join(m.value for m in at.markdown)
            self.assertIn("液冷相关企业必要数据不完整",text)
            self.assertIn("必要数据覆盖1/2",text)


if __name__ == "__main__": unittest.main()
