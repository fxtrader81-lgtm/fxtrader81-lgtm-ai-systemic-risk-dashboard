import ast
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from core import aof


class AofTests(unittest.TestCase):
    def test_current_and_legacy_preserve_original_formula_and_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = aof.load_aof(Path(tmp)/"aof.sqlite3")
            records = aof.history(Path(tmp)/"aof.sqlite3")
        self.assertEqual(current["metrics"]["aof"], 4.8)
        self.assertEqual(current["metrics"]["score"], 100)
        self.assertEqual(current["metrics"]["state"], "CRITICAL")
        self.assertEqual(current["metrics"]["contribution"], 25)
        old = next(r for r in records if r["reference"]["kind"] == "legacy")
        self.assertEqual(old["metrics"]["aof"], 2.4)
        self.assertEqual(old["metrics"]["score"], 30)
        self.assertEqual(old["metrics"]["state"], "WATCH")
        self.assertEqual(old["metrics"]["contribution"], 7.5)
        self.assertIsNone(old["reference"]["effective_date"])
        self.assertEqual(len(old["reference"]["chart_reference"]["generations"]), 6)

    def test_original_boundaries_and_saturation(self):
        for ratio, score, state in [(1,0,"SAFE"),(1.5,0,"WATCH"),(2.4,30,"WATCH"),
                                    (2.5,33,"WARNING"),(3.5,67,"CRITICAL"),(4,100,"CRITICAL"),(4.8,100,"CRITICAL")]:
            result = aof.score_aof(ratio)
            self.assertEqual((result[0], result[3]), (score, state))

    def test_invalid_power_is_not_filled_or_scored(self):
        ref = json.loads(aof.CONFIG.read_text())["records"][-1]
        for key in ("rack_kw", "baseline_kw"):
            for value in (0,-1,None,True,"120",float("nan"),float("inf")):
                with self.assertRaises(ValueError): aof.make_snapshot(dict(ref, **{key:value}))

    def test_refresh_deduplicates_and_history_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"aof.sqlite3"
            current = aof.load_aof(path)
            before = aof.history(path)
            aof.load_aof(path)
            self.assertEqual(aof.history(path), before)
            modified = deepcopy(current)
            modified["reference"]["rack_kw"] = 150
            with self.assertRaises(ValueError): aof.archive(modified, path)
            self.assertEqual(aof.history(path), before)
            new = aof.make_snapshot(dict(current["reference"], id="reviewed-new-version", rack_kw=150))
            aof.archive(new, path)
            self.assertEqual(len(aof.history(path)),3)
            self.assertEqual(aof.history(path)[1:],before)

    def test_snapshot_does_not_alias_mutable_config(self):
        ref = json.loads(aof.CONFIG.read_text())["records"][0]
        snap = aof.make_snapshot(ref)
        ref["chart_reference"]["generations"].clear()
        self.assertEqual(len(snap["reference"]["chart_reference"]["generations"]),6)

    def test_official_source_and_project_denominator_are_separate(self):
        ref = json.loads(aof.CONFIG.read_text())["records"][-1]
        self.assertEqual(ref["source_published_date"],"2025-05-16")
        self.assertTrue(ref["source_url"].startswith("https://developer.nvidia.com/"))
        self.assertIn("项目", ref["baseline_note"])
        self.assertIn("不是", ref["baseline_note"])
        self.assertIn("口径断点", aof.LIMITATION)

    def test_overview_uses_shared_aof_only_other_groups_unchanged(self):
        from core.factor_registry import _straw3
        close=pd.DataFrame({t:[10,20,15] for t in ["EQIX","DLR","VRT","SMCI","NEE","SO"]})
        with tempfile.TemporaryDirectory() as tmp:
            snap=aof.load_aof(Path(tmp)/"aof.sqlite3")
        with patch("core.factor_registry.load_power",return_value={"available":True,"metrics":{"score":35}}),patch("core.factor_registry._history",return_value=close),patch("core.factor_registry.load_liquid",return_value={"available":True,"metrics":{"score":50}}),patch("core.factor_registry.load_reit",return_value={"available":True,"metrics":{"score":50}}),patch("core.factor_registry.load_aof",return_value=snap) as load:
            result=_straw3()
        load.assert_called_once()
        self.assertEqual(result["score"],round(.25*100+.35*50+.25*50+.15*35,1))
        self.assertIn("4.8",result["detail"])

    def test_page_current_history_export_chart_and_no_refresh_button(self):
        from streamlit.testing.v1 import AppTest
        from test_power_infrastructure import snapshot as power_snapshot
        from test_liquid_signal import snapshot as liquid_snapshot
        prices=pd.DataFrame({"Close":[100.,110.,105.],"High":[102.,112.,107.],"Low":[98.,108.,103.]})
        income=pd.DataFrame({pd.Timestamp("2025-12-31"):[120.,30.],pd.Timestamp("2024-12-31"):[100.,20.]},
                            index=["Total Revenue","Operating Income"])
        class Ticker:
            financials=income
            def history(self,**kwargs): return prices
        with tempfile.TemporaryDirectory() as tmp,patch.object(aof,"STORE",Path(tmp)/"aof.sqlite3"),patch("core.power_infrastructure.load_power",return_value=power_snapshot()),patch("core.power_infrastructure.history",return_value=[]),patch("core.liquid_signal.load_liquid",return_value=liquid_snapshot()),patch("core.liquid_signal.history",return_value=[]),patch("yfinance.Ticker",return_value=Ticker()):
            at=AppTest.from_file("pages/straw3.py",default_timeout=30)
            at.session_state["download_owner_authenticated"] = True
            at.run()
            self.assertEqual(len(at.exception),0)
            values="\n".join(m.value for m in at.markdown)
            self.assertIn("4.8x",values)
            self.assertIn("AOF 机柜适配压力",values)
            self.assertIn("不代表全市场资产已减值",values)
            self.assertEqual([t.label for t in at.tabs],["检测逻辑","指标与历史证据","数据覆盖与来源"])
            labels=[e.label for e in at.expander]
            self.assertTrue(any(label.startswith("2026Q4进行中｜") for label in labels))
            self.assertIn("季度历史快照｜最近归档2026Q3 · 总分58.1 · WARNING",labels)
            self.assertEqual([d.label for d in at.get("download_button")],
                             ["下载可阅读版（HTML）","下载完整原始资料（JSON）"])
            chart=json.loads(at.get("plotly_chart")[0].proto.spec)
            self.assertEqual(chart["data"][0]["y"],[15,25,60,80,120,200])
            self.assertEqual(chart["data"][1]["y"],[120])
            self.assertEqual(len(chart["data"][0]["x"]),6)
            self.assertIn("不将七根柱子平均",values)
            self.assertEqual(len(at.button),0)
            before=aof.history()
            at.run()
            self.assertEqual(len(at.exception),0)
            self.assertEqual(aof.history(),before)
            self.assertEqual(len(before),2)

    def test_composite_weights_are_preserved(self):
        tree=ast.parse(Path("pages/straw3.py").read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="compute_dcoi")
        namespace={}
        exec(compile(ast.Module(body=[function],type_ignores=[]),"composite-weight-check","exec"),namespace)
        for values in ((0,0,0,0),(100,100,100,100),(100,46,41,45),(1,2,3,4)):
            expected=round(sum(w*s for w,s in zip((.25,.35,.25,.15),values)),1)
            self.assertEqual(namespace["compute_dcoi"](*values),expected)

    def test_dark_expander_download_and_text_states_are_scoped(self):
        css=Path("styles/pages.css").read_text()
        block=css.split("/* Factor 03 AOF evidence")[1].split("/* Native Streamlit prose")[0]
        for text in ("st-key-aof_evidence", "stDownloadButton", "details[open]", ":hover, :focus, :active", "font-size: 20px", "var(--text-soft)", "var(--bg-input)", "focus-visible"):
            self.assertIn(text,block)


if __name__ == "__main__": unittest.main()
