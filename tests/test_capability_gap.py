"""Approved capability-only changes, fixed public inputs and safe manual refresh."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from core import capability_gap as cap


def sample_snapshot():
    item = cap.baseline()
    item.pop("legacy")
    return item


def catalog():
    item = sample_snapshot()
    return {"models": {
        item["closed_model"]: {"side": "closed", "scores": item["closed_scores"]},
        item["open_model"]: {"side": "open", "scores": item["open_scores"]}},
        "checked_at": "2026-10-18T09:00:00+00:00", "source_sha256": "test-fixture"}


class CapabilityMathTests(unittest.TestCase):
    def test_reviewed_comparison_relative_denominator_and_contribution(self):
        item = sample_snapshot()
        m = cap.measure(item["closed_scores"], item["open_scores"])
        self.assertAlmostEqual(m["closed_avg"], 87.78033333333333)
        self.assertAlmostEqual(m["open_avg"], 80.51433333333334)
        self.assertAlmostEqual(m["difference_pp"], 7.266)
        self.assertAlmostEqual(m["signed_gap"], 7.266 / m["closed_avg"] * 100)
        self.assertEqual(m["state"], "WATCH")
        self.assertAlmostEqual(m["score"], (25 - m["risk_gap"]) / 25 * 60)
        self.assertAlmostEqual(m["contribution"], m["score"] * .2)

    def test_sign_and_risk_floor(self):
        m = cap.measure([80]*3, [88]*3)
        self.assertEqual(m["signed_gap"], -10)
        self.assertEqual(m["risk_gap"], 0)
        self.assertEqual(m["score"], 60)
        self.assertEqual(m["state"], "CRITICAL")

    def test_state_boundaries_and_safe_score_floor(self):
        for gap, state in [(0, "CRITICAL"), (2, "CRITICAL"), (2.01, "WARNING"),
                           (6, "WARNING"), (6.01, "WATCH"), (12, "WATCH"), (12.01, "SAFE")]:
            self.assertEqual(cap.gap_state(gap), state)
        self.assertEqual(cap.measure([100]*3, [50]*3)["score"], 0)

    def test_missing_and_invalid_are_never_zero(self):
        for a, b in [([0]*3, [1]*3), ([1, 2], [1]*3), ([100]*3, [None]*3),
                     ([100]*3, [float("nan")]*3), ([100]*3, [101]*3), ([True]*3, [1]*3)]:
            with self.assertRaises((ValueError, TypeError)):
                cap.measure(a, b)

    def test_archive_keeps_old_units_score_and_state(self):
        old = cap.baseline()["legacy"]
        m = cap.measure(old["closed_scores"], old["open_scores"], legacy=True)
        self.assertAlmostEqual(m["difference_pp"], -0.2666666666667)
        self.assertEqual(m["score"], 60)
        self.assertEqual(m["state"], "CRITICAL")
        self.assertEqual(m["contribution"], 12)
        self.assertEqual(old["recorded_period"], "2025-01")


class CapabilitySourceTests(unittest.TestCase):
    def test_fixed_fields_and_complete_candidates(self):
        text = "model,math_comp,code_generation,logic_with_navigation\n" \
               "gpt-6.1-sol-max,97.059,80.282,86\n" \
               "deepseek-v4.1-flash-max,96.078,77.465,68\n" \
               "gpt-7,99,,98\n"
        parsed = cap.parse_catalog(text)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed["gpt-6.1-sol-max"]["scores"], [97.059, 80.282, 86])

    def test_changed_tasks_duplicate_and_bad_numbers_rejected(self):
        for text in ["model,MATH,HumanEval,MMLU\ngpt-6,90,90,90\n",
                     "model,math_comp,code_generation,logic_with_navigation\ngpt-6,90,90,90\ngpt-6,90,90,90\n",
                     "model,math_comp,code_generation,logic_with_navigation\ngpt-6,nan,90,90\n"]:
            with self.assertRaises(ValueError):
                cap.parse_catalog(text)

    def test_directions_and_no_automatic_substitution(self):
        data = catalog()
        with self.assertRaises(ValueError):
            cap.make_snapshot(data, "deepseek-v4.1-flash-max", "gpt-6.1-sol-max")
        with self.assertRaises(ValueError):
            cap.make_snapshot(data, "gpt-7", "deepseek-v4.1-flash-max")


class CapabilityStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "history.sqlite3"

    def test_read_is_offline_and_initial_history_is_deduplicated(self):
        with patch.object(cap, "fetch_catalog", side_effect=AssertionError("No network")):
            a = cap.current_snapshot(self.db)
            b = cap.current_snapshot(self.db)
        self.assertEqual(a, b)
        self.assertEqual(len(cap.history(self.db)), 1)
        self.assertFalse(cap.adopt(sample_snapshot(), self.db))

    def test_changed_values_and_models_preserve_previous_records(self):
        original = cap.current_snapshot(self.db)
        new = catalog()
        new["models"]["gpt-6.1-sol-max"]["scores"][0] = 98
        updated = cap.make_snapshot(new, original["closed_model"], original["open_model"])
        self.assertTrue(cap.adopt(updated, self.db))
        self.assertEqual(len(cap.history(self.db)), 2)
        self.assertEqual(cap.current_snapshot(self.db)["closed_scores"][0], 98)
        self.assertIn(original, cap.history(self.db))
        self.assertFalse(cap.adopt(updated, self.db))

    def test_failed_refresh_and_invalid_adoption_preserve_active(self):
        original = cap.current_snapshot(self.db)
        item = copy.deepcopy(original)
        item["open_scores"][0] = None
        with self.assertRaises(TypeError):
            cap.adopt(item, self.db)
        item = copy.deepcopy(original)
        item["tasks"] = ["MMLU", "HumanEval", "MATH"]
        with self.assertRaises(ValueError):
            cap.adopt(item, self.db)
        cap.record_refresh("检查失败，保留上次结果", self.db)
        self.assertEqual(cap.current_snapshot(self.db), original)
        self.assertIn("失败", cap.last_refresh(self.db)[1])


class CapabilityScopeTests(unittest.TestCase):
    def test_refresh_notes_compact_spacing_preserves_font_size(self):
        css = Path("styles/pages.css").read_text()
        self.assertNotIn('gap: 0.35rem !important;', css)
        self.assertIn('.capability-refresh-notes {\n  display: block;', css)
        self.assertIn('margin: 0 0 8px !important;\n  line-height: 1.65 !important;', css)
        source = Path("components/capability_panel.py").read_text()
        self.assertIn('escape(note)', source)
        self.assertIn('class="capability-refresh-notes"', source)

    def test_native_evidence_prose_uses_readable_dark_theme_tokens(self):
        css = Path("styles/pages.css").read_text()
        scope = ":is(.st-key-capability_controls, .st-key-capability_evidence, .st-key-capability_history)"
        self.assertIn(scope + '\n  [data-testid="stMarkdownContainer"] :is(p, li, strong, em, h1, h2, h3, h4, h5, h6) {\n  color: var(--text-soft) !important;', css)
        self.assertIn('[data-testid="stCaptionContainer"] :is(p, strong, em) {\n  color: var(--text-dim) !important;', css)
        self.assertIn('[data-testid="stMarkdownContainer"] a {\n  color: var(--blue) !important;', css)
        self.assertIn('[data-testid="stExpander"] summary :is(p, span) {\n  font-size: 20px !important;\n  font-weight: 700 !important;', css)

    def test_native_controls_pair_dark_surfaces_with_light_text_in_all_states(self):
        css = Path("styles/pages.css").read_text()
        self.assertIn(':is([data-testid="stButton"], [data-testid="stDownloadButton"]) button {\n  background: var(--bg-input) !important;\n  color: var(--text-soft) !important;', css)
        self.assertIn('button:is(:hover, :focus, :active) {\n  background: var(--bg-panel-2) !important;\n  color: var(--text-soft) !important;', css)
        self.assertIn('[data-testid="stExpander"] summary {\n  background: var(--bg-panel) !important;', css)
        self.assertIn('[data-testid="stExpander"] summary:is(:hover, :focus, :active)', css)
        self.assertIn('details[open] > summary {\n  background: var(--bg-panel-2) !important;', css)
        self.assertIn(':is(button, summary):focus-visible {\n  outline: 2px solid var(--blue) !important;', css)

    def test_overview_reads_same_capability_component(self):
        from core.factor_registry import _straw2
        snapshot = sample_snapshot()
        snapshot["metrics"] = cap.measure(snapshot["closed_scores"], snapshot["open_scores"])
        def get_json(url):
            if "openrouter" in url:
                return {"data": [
                    {"id": "openai/gpt-4o", "pricing": {"prompt": "0.00001"}},
                    {"id": "deepseek/deepseek-chat", "pricing": {"prompt": "0.000001"}}]}
            raise RuntimeError("offline")
        with patch("core.factor_registry.current_capability_snapshot", return_value=snapshot), \
             patch("core.factor_registry.load_prices", return_value={"available": True, "metrics": {"score": 100}}), \
             patch("core.factor_registry.load_deployment", return_value={"available": False}), \
             patch("core.factor_registry.load_ecology", return_value={"available": False}), \
             patch("core.factor_registry._get_json", side_effect=get_json):
            result = _straw2()
        self.assertTrue(result["available"])
        self.assertEqual(result["coverage"], 55)
        self.assertEqual(result["score"], round((snapshot["metrics"]["score"]*.2 + 100*.35)/.55, 1))

    def test_only_capability_argument_changes_in_original_total_formula(self):
        source = Path("pages/straw2.py").read_text()
        tree = ast.parse(source)
        func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_osci")
        namespace = {}
        exec(compile(ast.Module(body=[func], type_ignores=[]), "test", "exec"), namespace)
        snapshot = sample_snapshot()
        m = cap.measure(snapshot["closed_scores"], snapshot["open_scores"])
        result = namespace["compute_osci"](m["risk_gap"], 40, 80, 65)
        self.assertAlmostEqual(result[1], m["score"])
        self.assertEqual(result[2], 60)
        self.assertAlmostEqual(result[3], 100/3)
        self.assertEqual(result[4], 65)
        self.assertEqual(result[0], round(m["score"]*.2 + 60*.35 + 100/3*.3 + 65*.15, 1))


class CapabilityPageTests(unittest.TestCase):
    def test_explicit_refresh_history_and_failure_keep_last_good(self):
        from streamlit.testing.v1 import AppTest
        from core import capability_cohort as cohort
        import json
        full = json.loads(cohort.SEED.read_text())
        def response(url, **kwargs):
            if "openrouter" in url:
                data = {"data": [
                    {"id": "openai/gpt-4o", "pricing": {"prompt": "0.00001"}},
                    {"id": "deepseek/deepseek-chat", "pricing": {"prompt": "0.000001"}}]}
            elif "github.com/repos" in url:
                from core.deployment_interest import REPOS
                repo = url.split("/repos/")[1]
                rid = next(rid for _, name, rid in REPOS if name == repo)
                data = {"id": rid, "full_name": repo, "stargazers_count": 60000, "forks_count": 100, "watchers_count": 100}
            else:
                repo = url.split("/api/models/")[1]
                data = {"id": repo, "author": repo.split("/")[0], "private": False, "downloads": 300000, "likes": 100}
            return SimpleNamespace(status_code=200, json=lambda: data, raise_for_status=lambda: None)
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(cap, "STORE", Path(tmp)/"history.sqlite3"), \
             patch("core.model_prices.STORE", Path(tmp)/"prices.sqlite3"), \
             patch("core.deployment_interest.STORE", Path(tmp)/"deployment.sqlite3"), \
             patch("core.ecology_downloads.STORE", Path(tmp)/"ecology.sqlite3"), \
             patch("requests.get", side_effect=response), \
             patch.object(cohort, "fetch_latest_snapshot", return_value=full) as fetch:
            from core.deployment_interest import load_deployment
            from core.ecology_downloads import get_selected_downloads
            load_deployment.clear()
            get_selected_downloads.clear()
            at = AppTest.from_file("pages/straw2.py", default_timeout=30).run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(fetch.call_count, 0)
            self.assertEqual([b.key for b in at.button], [
                "refresh_capability_only",
                "request_download_factor02-open-source_quarterly_history_html",
                "request_download_factor02-open-source_quarterly_history_json",
            ])
            notes = [m.value for m in at.markdown if '<div class="capability-refresh-notes">' in m.value]
            self.assertEqual(len(notes), 1)
            self.assertGreaterEqual(notes[0].count('<p>'), 3)
            labels = [e.label for e in at.expander]
            self.assertTrue(any(label.startswith("2026Q4进行中｜") for label in labels))
            self.assertIn("季度历史快照｜最近归档2026Q3 · 总分75.0 · CRITICAL", labels)
            self.assertEqual(len(cap.history()), 2)
            at.button(key="refresh_capability_only").click().run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(len(cap.history()), 2)
            line = next(line for line in full['raw_csv'].splitlines() if line.startswith('gpt-6-astra-max,'))
            parts = line.split(',')
            parts[1] = str(float(parts[1]) - .5)
            changed = cohort.make_full_snapshot(full['raw_csv'].replace(line, ','.join(parts)),
                full['raw_metadata'], full['categories'], revision=full['revision'],
                release=full['release'], checked_at='2026-10-18T11:00:00+00:00')
            fetch.return_value = changed
            at.button(key="refresh_capability_only").click().run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(len(cap.history()), 3)
            before = cap.current_snapshot()
            fetch.side_effect = ValueError("changed source")
            at.button(key="refresh_capability_only").click().run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(cap.current_snapshot(), before)
            self.assertEqual(len(cap.history()), 3)


if __name__ == "__main__":
    unittest.main()
