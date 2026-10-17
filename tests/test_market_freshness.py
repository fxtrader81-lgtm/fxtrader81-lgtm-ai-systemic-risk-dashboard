import unittest
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd

from core.market_freshness import (
    expected_close_date,
    download_yahoo,
    fetch_sina_china_close,
    merge_recent,
    repair_china_if_stale,
    repair_if_stale,
    stale_sessions,
)


class MarketFreshnessTests(unittest.TestCase):
    def test_us_before_and_after_close(self):
        before = datetime(2026, 10, 16, 15, 0, tzinfo=ZoneInfo("America/New_York"))
        after = datetime(2026, 10, 16, 17, 0, tzinfo=ZoneInfo("America/New_York"))
        self.assertEqual(expected_close_date("US", before), pd.Timestamp("2026-10-15"))
        self.assertEqual(expected_close_date("US", after), pd.Timestamp("2026-10-16"))

    def test_weekend_uses_friday(self):
        sunday = datetime(2026, 10, 18, 20, 0, tzinfo=ZoneInfo("America/New_York"))
        self.assertEqual(expected_close_date("US", sunday), pd.Timestamp("2026-10-16"))

    def test_china_session_and_lag(self):
        now = datetime(2026, 10, 16, 16, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        prior = pd.Series([1.0], index=pd.to_datetime(["2026-10-15"]))
        self.assertEqual(stale_sessions(prior, "CN", now), 1)
        self.assertIsNone(stale_sessions(pd.Series(dtype=float), "CN", now))

    def test_recent_updates_overlap_without_losing_old_history(self):
        history = pd.Series([100.0], index=pd.to_datetime(["2026-10-15"]))
        recent = pd.Series([101.0, 102.0], index=pd.to_datetime(["2026-10-15", "2026-10-16"]))
        merged = merge_recent(history, recent)
        self.assertEqual(merged.loc["2026-10-15"], 101.0)
        self.assertEqual(merged.loc["2026-10-16"], 102.0)

    def test_stale_history_tries_recent_feed(self):
        history = pd.Series([100.0], index=pd.to_datetime(["2026-10-01"]))
        recent = pd.Series([102.0], index=pd.to_datetime(["2026-10-16"]))
        with patch("core.market_freshness.fetch_recent_yahoo", return_value=recent):
            merged, supplemented = repair_if_stale(history, "^GSPC", "US")
        self.assertTrue(supplemented)
        self.assertEqual(merged.index.max(), pd.Timestamp("2026-10-16"))

    def test_yahoo_requests_are_serialized(self):
        guard = Lock()
        active = 0
        maximum = 0

        def fake_download(*args, **kwargs):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            sleep(0.01)
            with guard:
                active -= 1
            return args[0]

        with patch("core.market_freshness.yf.download", side_effect=fake_download):
            with ThreadPoolExecutor(max_workers=4) as pool:
                values = list(pool.map(download_yahoo, ["^GSPC", "^IXIC", "000001.SS", "399001.SZ"]))
        self.assertEqual(values, ["^GSPC", "^IXIC", "000001.SS", "399001.SZ"])
        self.assertEqual(maximum, 1)

    def test_dated_sina_close_fills_missing_china_session(self):
        fields = ["上证指数", "3723.79", "3707.48", "3716.2842"] + ["0"] * 26
        fields += ["2026-10-16", "15:35:27", "00"]
        payload = ('var hq_str_sh000001="' + ",".join(fields) + '";').encode("gbk")
        now = datetime(2026, 10, 17, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        history = pd.Series([3707.48], index=pd.to_datetime(["2026-10-15"]))
        with patch("core.market_freshness.requests.get") as get:
            get.return_value.content = payload
            close = fetch_sina_china_close("000001.SS", now)
        self.assertAlmostEqual(close.loc["2026-10-16"], 3716.2842)
        with patch("core.market_freshness.fetch_recent_yahoo", return_value=pd.Series(dtype=float)), \
             patch("core.market_freshness.fetch_sina_china_close", return_value=close):
            merged = repair_china_if_stale(history, "000001.SS")
        self.assertEqual(merged.index.max(), pd.Timestamp("2026-10-16"))

    def test_china_quote_is_not_taken_before_close(self):
        fields = ["深证成指", "0", "0", "11802.459"] + ["0"] * 26
        fields += ["2026-10-16", "14:59:00", "00"]
        payload = ('var hq_str_sz399001="' + ",".join(fields) + '";').encode("gbk")
        now = datetime(2026, 10, 17, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        with patch("core.market_freshness.requests.get") as get:
            get.return_value.content = payload
            self.assertTrue(fetch_sina_china_close("399001.SZ", now).empty)
        fields[31] = "15:00:03"
        payload = ('var hq_str_sz399001="' + ",".join(fields) + '";').encode("gbk")
        before_close = datetime(2026, 10, 16, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        with patch("core.market_freshness.requests.get") as get:
            get.return_value.content = payload
            self.assertTrue(fetch_sina_china_close("399001.SZ", before_close).empty)


if __name__ == "__main__":
    unittest.main()
