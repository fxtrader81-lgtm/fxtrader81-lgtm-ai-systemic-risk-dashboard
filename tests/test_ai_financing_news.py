"""Official release discovery only creates review leads, not scored deals."""

import unittest
from datetime import datetime, timezone

from core.ai_financing_news import parse_financing_releases, parse_news_rss


class FinancingNewsTests(unittest.TestCase):
    def test_keeps_financing_titles_from_official_press_index(self):
        html = '''
        <a href="/en/news/press/20261001">Execution of Follow-on <b>Investment</b> in OpenAI</a>
        <a href="/en/news/press/20260924">Issuance of Foreign Currency-Denominated Senior Notes</a>
        <a href="/en/news/press/20260930">Completion of Acquisition of DigitalBridge</a>
        <a href="https://elsewhere.example/en/news/press/20261002">New Notes</a>
        <a href="/en/news/press/20260924">Issuance of Foreign Currency-Denominated Senior Notes</a>
        '''
        releases = parse_financing_releases(html)
        self.assertEqual([item["date"] for item in releases], ["20261001", "20260924"])
        self.assertEqual(len(releases), 2)
        self.assertEqual(releases[0]["url"], "https://group.softbank/en/news/press/20261001")

    def test_news_headlines_are_unverified_leads_not_deals(self):
        feed = b'''<rss><channel>
        <item><title>CoreWeave prices $3.7 billion AI convertible notes - Example News</title>
        <link>https://news.google.com/rss/articles/example1</link>
        <pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate><source>Example News</source></item>
        <item><title>CoreWeave prices $3.7 billion AI convertible notes - Example News</title>
        <link>https://news.google.com/rss/articles/example1</link>
        <pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate><source>Example News</source></item>
        <item><title>AI debt financing concerns are rising - Opinion</title>
        <link>https://news.google.com/rss/articles/example2</link>
        <pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate><source>Opinion</source></item>
        <item><title>OpenAI secures $1 billion loan - Example</title>
        <link>https://evil.example/article</link>
        <pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate><source>Example</source></item>
        </channel></rss>'''
        leads = parse_news_rss(feed, now=datetime(2026, 10, 8, tzinfo=timezone.utc))
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["issuer"], "CoreWeave")
        self.assertIn("37亿美元", leads[0]["size"])
        self.assertFalse(leads[0]["verified"])
        self.assertIn("待原始文件核验", leads[0]["status"])

    def test_stale_news_is_not_shown(self):
        feed = b'''<rss><channel><item><title>CoreWeave raises $1 billion AI debt - Example</title>
        <link>https://news.google.com/rss/articles/old</link>
        <pubDate>Mon, 01 Sep 2026 12:00:00 GMT</pubDate><source>Example</source>
        </item></channel></rss>'''
        self.assertEqual(parse_news_rss(feed, now=datetime(2026, 10, 8, tzinfo=timezone.utc)), [])

    def test_rejects_known_misleading_use_of_proceeds_headline(self):
        feed = b'''<rss><channel><item>
        <title>Tesla Secures $30 Billion Credit Facility to Fund AI Infrastructure Expansion</title>
        <link>https://news.google.com/rss/articles/tesla</link>
        <pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate>
        </item></channel></rss>'''
        self.assertEqual(parse_news_rss(feed, now=datetime(2026, 10, 8, tzinfo=timezone.utc)), [])


if __name__ == "__main__":
    unittest.main()
