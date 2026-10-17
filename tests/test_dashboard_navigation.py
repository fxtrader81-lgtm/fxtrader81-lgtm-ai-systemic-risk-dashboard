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
    def test_status_precedes_name_and_internal_detail_link(self):
        fake = _FakeStreamlit()
        results = {
            straw_id: {"score": 10, "state": "SAFE"}
            for straw_id in FACTOR_LABELS
        }

        with patch("core.score_engine.st", fake):
            render_factor_navigation({}, results=results)

        first_status = next(i for i, call in enumerate(fake.calls)
                            if call[0] == "markdown" and "factor-native-meta" in call[1])
        first_name = next(i for i, call in enumerate(fake.calls)
                          if call[0] == "markdown" and "factor-native-name" in call[1])
        first_link = next(i for i, call in enumerate(fake.calls) if call[0] == "page_link")

        self.assertLess(first_status, first_name)
        self.assertLess(first_name, first_link)
        self.assertEqual(fake.calls[first_link][1], FACTOR_FILES["straw1"])
        self.assertEqual(len([call for call in fake.calls if call[0] == "page_link"]), 7)

    def test_dashboard_does_not_repeat_credit_transmission_panel(self):
        with open("pages/dashboard.py", encoding="utf-8") as source:
            dashboard = source.read()
        self.assertNotIn("AI信用传导｜结构暴露与市场确认", dashboard)
        self.assertNotIn('href="/factor-financing-structure"', dashboard)
        self.assertNotIn('href="/factor-credit-refinancing"', dashboard)


if __name__ == "__main__":
    unittest.main()
