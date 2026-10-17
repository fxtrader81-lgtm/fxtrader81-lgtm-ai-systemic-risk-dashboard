"""Dashboard factor navigation should keep each card ordered and internal."""

import unittest
from unittest.mock import patch

from core.score_engine import FACTOR_FILES, FACTOR_LABELS, render_factor_navigation


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FakeStreamlit:
    def __init__(self):
        self.calls = []

    def markdown(self, body, **_kwargs):
        self.calls.append(("markdown", body))

    def container(self, **kwargs):
        self.calls.append(("container", kwargs))
        return _Context()

    def columns(self, *_args, **_kwargs):
        self.calls.append(("columns", None))
        return _Context(), _Context()

    def page_link(self, page, **kwargs):
        self.calls.append(("page_link", page, kwargs))


class DashboardNavigationTests(unittest.TestCase):
    def test_name_and_internal_link_precede_status_bar(self):
        fake = _FakeStreamlit()
        results = {
            straw_id: {"score": 10, "state": "SAFE"}
            for straw_id in FACTOR_LABELS
        }

        with patch("core.score_engine.st", fake):
            render_factor_navigation({}, results=results)

        section_title = next(call[1] for call in fake.calls
                             if call[0] == "markdown" and "factor-section-title" in call[1])
        self.assertIn("各风险因子情况", section_title)
        self.assertNotIn("点击进入详情", section_title)
        first_status = next(i for i, call in enumerate(fake.calls)
                            if call[0] == "markdown" and "factor-native-meta" in call[1])
        first_name = next(i for i, call in enumerate(fake.calls)
                          if call[0] == "markdown" and "factor-native-name" in call[1])
        first_link = next(i for i, call in enumerate(fake.calls) if call[0] == "page_link")

        self.assertLess(first_name, first_link)
        self.assertLess(first_link, first_status)
        self.assertEqual(fake.calls[first_link][1], FACTOR_FILES["straw1"])
        self.assertEqual(len([call for call in fake.calls if call[0] == "page_link"]), 7)
        containers = [call for call in fake.calls if call[0] == "container"]
        self.assertEqual(containers[0][1]["key"], "factor_card_straw1")

    def test_dashboard_does_not_repeat_credit_transmission_panel(self):
        with open("pages/dashboard.py", encoding="utf-8") as source:
            dashboard = source.read()
        self.assertIn('st.tabs(["检测逻辑", "指标与历史证据", "数据覆盖与来源"])', dashboard)
        self.assertIn("总览检测逻辑", dashboard)
        self.assertIn("七个风险因子的当前证据", dashboard)
        self.assertNotIn("AI信用传导｜结构暴露与市场确认", dashboard)
        self.assertNotIn('href="/factor-financing-structure"', dashboard)
        self.assertNotIn('href="/factor-credit-refinancing"', dashboard)

    def test_sidebar_brand_precedes_navigation_and_has_prominent_kicker(self):
        with open("styles/base.css", encoding="utf-8") as source:
            css = source.read()

        self.assertIn('[data-testid="stSidebarUserContent"]', css)
        self.assertIn('[data-testid="stSidebarNav"]', css)
        self.assertRegex(
            css,
            r'\[data-testid="stSidebarUserContent"\]\s*\{\s*order:\s*1;',
        )
        self.assertRegex(
            css,
            r'\[data-testid="stSidebarNav"\]\s*\{\s*order:\s*2;',
        )
        self.assertRegex(
            css,
            r'\.nav-brand-kicker\s*\{[^}]*font-size:\s*14px;',
        )

    def test_conclusion_text_matches_methodology_text_size(self):
        with open("styles/components.css", encoding="utf-8") as source:
            component_css = source.read()
        with open("styles/pages.css", encoding="utf-8") as source:
            page_css = source.read()

        self.assertRegex(
            component_css,
            r'\.conclusion-copy\s*\{[^}]*font-size:\s*16px;',
        )
        self.assertRegex(
            component_css,
            r'\.conclusion-note,\s*\.coverage-text\s*\{[^}]*font-size:\s*16px;',
        )
        self.assertRegex(
            page_css,
            r'\.step-text,\s*\.logic-step p\s*\{[^}]*font-size:\s*16px',
        )


if __name__ == "__main__":
    unittest.main()
