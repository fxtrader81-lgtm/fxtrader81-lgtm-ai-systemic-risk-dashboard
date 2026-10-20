from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from core import reit_pressure as reit


def row(ticker, price=95., latest=120., prior=100.):
    return {"ticker":ticker,"current_price":price,"week52_high":100.,"week52_low":50.,
            "price_date":"2026-10-19","window_start":"2025-10-20","window_end":"2026-10-19",
            "high_date":"2026-03-01","low_date":"2026-01-01",
            "annual_revenue":[{"period_end":"2025-12-31","revenue":latest},{"period_end":"2024-12-31","revenue":prior}],
            "source_url":f"https://finance.yahoo.com/quote/{ticker}/history/",
            "financial_source_url":f"https://finance.yahoo.com/quote/{ticker}/financials/",
            "reason":None,"raw":{"unchanged_evidence":"test"}}


def snapshot(missing=False):
    rows=[row("EQIX"),row("DLR",80.,105.)]
    if missing: rows[1]["annual_revenue"]=[]
    return reit.make_snapshot(rows,"2026-10-19T23:30:00+00:00")


class ReitTests(unittest.TestCase):
    def tearDown(self): reit.get_reit_snapshot.clear()

    def test_original_scores_rounding_states_and_weight(self):
        s=snapshot()
        self.assertEqual(s["rows"][0]["metrics"]["company_score"],26.25)
        self.assertEqual(s["rows"][1]["metrics"]["company_score"],58.25)
        self.assertEqual(s["metrics"]["unrounded_score"],42.25)
        self.assertEqual(s["metrics"]["score"],42)
        self.assertEqual(s["metrics"]["state"],"WATCH")
        self.assertAlmostEqual(s["metrics"]["contribution"],14.7)
        self.assertEqual(s["metrics"]["mean_drawdown"],12.5)

    def test_original_price_and_growth_boundaries(self):
        for d,p in [(0,10),(4.999,10),(5,35),(15,60),(25,80),(40,95),(100,95)]:
            self.assertEqual(reit.score_company(d,0)["price_score"],p)
        for g,p in [(-100,80),(0,80),(.1,55),(6,55),(6.1,30),(12,30),(12.1,10)]:
            self.assertEqual(reit.score_company(5,g)["growth_score"],p)
        for d,g in [(None,1),(True,1),(float("nan"),1),(-1,1),(1,float("inf"))]:
            with self.assertRaises(ValueError): reit.score_company(d,g)

    def test_missing_one_company_or_revenue_never_average_remaining_or_default(self):
        s=snapshot(missing=True)
        self.assertFalse(s["available"])
        self.assertEqual(s["coverage"],1)
        self.assertIsNone(s["metrics"])
        self.assertIsNone(s["rows"][1]["metrics"])
        with self.assertRaises(ValueError): reit.make_snapshot([row("EQIX")],"time")
        with self.assertRaises(ValueError): reit.make_snapshot([row("EQIX"),row("EQIX")],"time")

    def test_invalid_values_periods_and_dates_unavailable(self):
        for update in ({"current_price":0},{"week52_high":None},{"current_price":101},
                       {"week52_low":float("nan")},{"price_date":None},{"high_date":"2027-01-01"}):
            rows=[dict(row("EQIX"),**update),row("DLR")]
            self.assertFalse(reit.make_snapshot(rows,"time")["available"])
        for revenue in ([{"period_end":"2025-12-31","revenue":120.},{"period_end":"2025-09-30","revenue":100.}],
                        [{"period_end":"2025-12-31","revenue":120.},{"period_end":"2024-12-31","revenue":0.}]):
            s=reit.make_snapshot([dict(row("EQIX"),annual_revenue=revenue),row("DLR")],"time")
            self.assertIsNone(s["metrics"])

    def test_zero_current_annual_revenue_is_valid_negative_growth(self):
        s=reit.make_snapshot([row("EQIX",latest=0),row("DLR")],"time")
        self.assertTrue(s["available"])
        self.assertEqual(s["rows"][0]["metrics"]["rev_growth"],-100)

    def test_dedup_history_immutable_and_failure_retained_not_fallback(self):
        s=snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"reit.sqlite3"
            reit.archive(s,path)
            before=reit.history(path)
            reit.archive(dict(s,checked_at="later"),path)
            self.assertEqual(reit.history(path),before)
            failed=snapshot(missing=True)
            failed["checked_at"]="2026-10-19T23:35:00+00:00"
            reit.archive(failed,path)
            records=reit.history(path)
            self.assertIsNone(records[0]["metrics"])
            self.assertEqual(records[1],before[0])
            self.assertEqual(records[1]["rows"][0]["raw"],s["rows"][0]["raw"])

    def test_cache_and_shared_entry_do_not_refetch_or_duplicate(self):
        reit.get_reit_snapshot.clear()
        with tempfile.TemporaryDirectory() as tmp,patch.object(reit,"STORE",Path(tmp)/"reit.sqlite3"),patch.object(reit,"_fetch",side_effect=lambda t:row(t)) as fetch:
            first=reit.load_reit()
            second=reit.load_reit()
            self.assertEqual(first,second)
            self.assertEqual(fetch.call_count,2)
            self.assertEqual(len(reit.history()),1)

    def test_fetch_uses_annual_periods_adjusted_intraday_extrema_and_retains_raw(self):
        prices=pd.DataFrame({"Close":[80.,90.,95.],"High":[85.,100.,98.],"Low":[50.,85.,90.]},
                            index=pd.to_datetime(["2025-10-20","2026-03-01","2026-10-19"]))
        finance=pd.DataFrame({pd.Timestamp("2024-12-31"):[100.],pd.Timestamp("2025-12-31"):[120.]},index=["Total Revenue"])
        class Ticker:
            financials=finance
            def history(self,**kwargs):
                self.kwargs=kwargs
                return prices
        ticker=Ticker()
        with patch.object(reit.yf,"Ticker",return_value=ticker): r=reit._fetch("EQIX")
        self.assertEqual(ticker.kwargs,{"period":"1y","auto_adjust":True,"timeout":12})
        self.assertEqual(r["week52_high"],100)
        self.assertEqual(r["high_date"],"2026-03-01")
        self.assertEqual(r["price_date"],"2026-10-19")
        self.assertEqual(r["annual_revenue"][0]["revenue"],120)
        self.assertEqual(len(r["raw"]["adjusted_daily_prices"]),3)
        self.assertFalse(reit.validate_row(r))
        finance[pd.Timestamp("2025-12-31")]=float("nan")
        finance[pd.Timestamp("2023-12-31")]=90.
        with patch.object(reit.yf,"Ticker",return_value=ticker): r=reit._fetch("EQIX")
        self.assertIsNone(r["annual_revenue"][0]["revenue"])
        self.assertTrue(reit.validate_row(r))

    def test_overview_uses_same_reit_and_retains_missing_coverage_policy(self):
        from core.factor_registry import _straw3
        close=pd.DataFrame({t:[10,20,15] for t in ["VRT","SMCI","NEE","SO"]})
        with patch("core.factor_registry.load_power",return_value={"available":True,"metrics":{"score":35}}),patch("core.factor_registry._history",return_value=close),patch("core.factor_registry.load_liquid",return_value={"available":True,"metrics":{"score":50}}),patch("core.factor_registry.load_aof",return_value={"metrics":{"score":100,"aof":4.8}}),patch("core.factor_registry.load_reit",return_value=snapshot()) as load:
            result=_straw3()
            self.assertEqual(result["score"],round(25+.35*42+.25*50+.15*35,1))
            self.assertEqual(result["coverage"],100)
            load.return_value=snapshot(missing=True)
            result=_straw3()
            self.assertEqual(result["coverage"],65)
            self.assertEqual(result["score"],round((25+.25*50+.15*35)/.65,1))
            self.assertIn("不计分",result["detail"])

    def test_page_explain_history_download_and_missing_score_removed(self):
        from streamlit.testing.v1 import AppTest
        from test_power_infrastructure import snapshot as power_snapshot
        from test_liquid_signal import snapshot as liquid_snapshot
        prices=pd.DataFrame({"Close":[100.,110.,105.],"High":[102.,112.,107.],"Low":[98.,108.,103.]})
        income=pd.DataFrame({pd.Timestamp("2025-12-31"):[120.,30.],pd.Timestamp("2024-12-31"):[100.,20.]},index=["Total Revenue","Operating Income"])
        class Ticker:
            financials=income
            def history(self,**kwargs): return prices
        with patch("core.power_infrastructure.load_power",return_value=power_snapshot()),patch("core.power_infrastructure.history",return_value=[]),patch("core.liquid_signal.load_liquid",return_value=liquid_snapshot()),patch("core.liquid_signal.history",return_value=[]),patch("core.reit_pressure.load_reit",return_value=snapshot()) as load,patch("core.reit_pressure.history",return_value=[snapshot()]),patch("yfinance.Ticker",return_value=Ticker()):
            at=AppTest.from_file("pages/straw3.py",default_timeout=30).run()
            self.assertEqual(len(at.exception),0)
            self.assertIn("straw3",at.session_state["straw_scores"])
            section = next(t for t in at.tabs if t.label=="REIT")
            for title in ("本期数据与计算说明","历史记录与原始资料"):
                self.assertFalse(next(e for e in section.get("expander") if e.label==title).proto.expanded)
            self.assertIn("下载REIT历史与原始资料",[d.label for d in at.get("download_button")])
            self.assertEqual(len(at.button),0)
            text="\n".join(m.value for m in at.markdown)
            self.assertIn("42分",text)
            self.assertIn("最新收盘/日期",text)
            load.return_value=snapshot(missing=True)
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertNotIn("straw3",at.session_state["straw_scores"])
            self.assertTrue(any("完整DCOI暂不可用" in m.value for m in at.markdown))
            self.assertTrue(any("必要数据覆盖1/2" in m.value for m in at.markdown))


if __name__ == "__main__": unittest.main()
