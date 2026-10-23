from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from core.download_access import (
    contact_email,
    interest_stats,
    record_interest,
    verify_owner_credentials,
)
from energy_market_fixture import MARKET_SNAPSHOT


class DownloadAccessTests(unittest.TestCase):
    def test_anonymous_interest_counts_clicks_and_approximate_sessions_only(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder) / "interest.sqlite3"
            clicked = datetime(2026, 10, 23, 7, 0, tzinfo=timezone.utc)
            self.assertTrue(record_interest("history-a.json", "visitor-a", path=store, clicked_at=clicked))
            self.assertFalse(record_interest(
                "history-a.json", "visitor-a", path=store, clicked_at=clicked + timedelta(seconds=5)
            ))
            self.assertTrue(record_interest(
                "history-a.json", "visitor-a", path=store, clicked_at=clicked + timedelta(seconds=31)
            ))
            record_interest("history-b.html", "visitor-b", path=store, clicked_at=clicked)
            stats = interest_stats(path=store)
        self.assertEqual(stats["total_clicks"], 3)
        self.assertEqual(stats["approx_sessions"], 2)
        self.assertEqual(stats["by_resource"][0], {
            "resource": "history-a.json", "clicks": 2, "approx_sessions": 1,
        })
        self.assertEqual(set(stats), {
            "total_clicks", "approx_sessions", "last_clicked_at", "by_resource", "storage",
        })

    def test_owner_secret_and_contact_email_are_not_hard_coded(self):
        values = {
            "DOWNLOAD_OWNER_USERNAME": "owner",
            "DOWNLOAD_OWNER_PASSWORD": "strong-test-secret",
            "DOWNLOAD_CONTACT_EMAIL": "fxtrader81@gmail.com",
        }
        with patch.dict(os.environ, values, clear=False):
            self.assertTrue(verify_owner_credentials("owner", "strong-test-secret"))
            self.assertFalse(verify_owner_credentials("owner", "wrong"))
            self.assertEqual(contact_email(), "fxtrader81@gmail.com")

    def test_public_factor04_contains_no_download_payload(self):
        from streamlit.testing.v1 import AppTest

        with patch.dict(os.environ, {"DOWNLOAD_OWNER_PASSWORD": ""}, clear=False), \
             patch("core.energy_market.load_energy_market", return_value=MARKET_SNAPSHOT):
            at = AppTest.from_file("pages/straw4.py", default_timeout=20).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.get("download_button")), 0)
        labels = [button.label for button in at.button]
        self.assertNotIn("所有者登录", labels)
        self.assertIn("下载可阅读版（HTML）", labels)
        self.assertIn("下载完整原始资料（JSON）", labels)
        self.assertFalse(any("fxtrader81@gmail.com" in item.value for item in at.info))

    def test_owner_session_exposes_all_factor04_downloads(self):
        from streamlit.testing.v1 import AppTest

        with patch("core.energy_market.load_energy_market", return_value=MARKET_SNAPSHOT):
            at = AppTest.from_file("pages/straw4.py", default_timeout=20)
            at.session_state["download_owner_authenticated"] = True
            at.run()
        self.assertEqual(len(at.exception), 0)
        labels = [button.label for button in at.get("download_button")]
        self.assertEqual(len(labels), 4)
        self.assertIn("下载可阅读版（HTML）", labels)
        self.assertIn("下载完整原始资料（JSON）", labels)

    def test_protected_downloads_have_dark_high_contrast_states(self):
        css = Path("styles/pages.css").read_text(encoding="utf-8")
        self.assertIn('[class*="st-key-request_download_"]', css)
        self.assertIn('[class*="st-key-download_"]', css)
        self.assertIn('[data-testid="stDownloadButton"]', css)
        self.assertIn("background: var(--bg-input) !important;", css)
        self.assertIn("color: #f8fafc !important;", css)
        self.assertIn("button:is(:hover, :focus, :active)", css)
        self.assertIn("focus-visible", css)

    def test_download_dialog_does_not_prefill_owner_username(self):
        source = Path("components/protected_download.py").read_text(encoding="utf-8")
        self.assertIn('st.text_input("用户名", value="", placeholder="请输入用户名")', source)
        self.assertNotIn('value=owner_username()', source)


if __name__ == "__main__":
    unittest.main()
