"""Discover financing news; keep headlines separate from verified deal terms."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
import streamlit as st


PRESS_URL = "https://group.softbank/en/news/press"
NEWS_RSS_URL = "https://news.google.com/rss/search"
NEWS_REFRESH_SECONDS = 6 * 3600
NEWS_QUERY = '("AI data center" OR "AI infrastructure" OR "GPU-backed" OR "AI cloud" OR OpenAI OR Anthropic OR CoreWeave) (debt OR loan OR bond OR notes OR financing OR credit facility) when:14d'
_FINANCING_TERMS = (
    "note", "bond", "loan", "financ", "funding", "investment", "openai",
)
_PRESS_PATH = re.compile(r"^/en/news/press/(20\d{6})(?:_\d+)?/?$")
_MONEY = re.compile(r"(?:\$|USD\s?)(\d+(?:\.\d+)?)\s?(billion|million|bn|b|m)\b", re.I)
_ISSUERS = ("CoreWeave", "SoftBank", "Sharon AI", "Broadcom", "Anthropic", "OpenAI", "Oracle", "NVIDIA", "Nebius", "Crusoe", "Lambda")
_AI_CONTEXT = ("data center", "datacenter", "compute", "gpu", "chip", "openai", "anthropic", "coreweave", "nebius", "crusoe")
_DEBT_CONTEXT = ("debt", "loan", "bond", "notes", "financ", "credit", "convertible", "refinanc")
_TRANSACTION = ("prices", "priced", "closes", "closed", "secures", "secured", "raises", "raised", "lend", "lends", "loan facility", "financing facility", "financing deal", "bond offering", "notes offering", "credit facility", "agrees to provide", "offers")
_PRESSURE = ("delay", "default", "cancell", "downgrad", "force majeure", "restructur", "distress")
_COMMENTARY = ("scrutiny", "concerns", "threaten", "showing up everywhere", "surging", "face increased risk", "explainer", "opinion")


class _PressLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        url = urljoin(PRESS_URL, self._href)
        parsed = urlparse(url)
        match = _PRESS_PATH.match(parsed.path)
        title = " ".join(" ".join(self._text).split())
        if parsed.hostname == "group.softbank" and match and title:
            self.links.append({"date": match.group(1), "title": title, "url": url})
        self._href = None
        self._text = []


def parse_financing_releases(html: str) -> list[dict[str, str]]:
    parser = _PressLinks()
    parser.feed(html)
    unique: dict[str, dict[str, str]] = {}
    for item in parser.links:
        if any(term in item["title"].lower() for term in _FINANCING_TERMS):
            unique[item["url"]] = item
    return sorted(unique.values(), key=lambda item: item["date"], reverse=True)[:8]


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def load_softbank_financing_releases() -> tuple[list[dict[str, str]], str]:
    """Check the official release index at most weekly while the app is used.

    An exception is not cached, so a transient failure can be retried on the
    next visit. Discovery does not imply a new debt issue or a scored signal.
    """
    response = requests.get(PRESS_URL, timeout=8, headers={"User-Agent": "AI-risk-dashboard/1.0"})
    response.raise_for_status()
    releases = parse_financing_releases(response.text)
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return releases, checked_at


def _headline_event(title: str) -> str | None:
    """Conservative relevance screen, not verification of a reported fact."""
    lower = title.lower()
    # The referenced Tesla facility has general corporate purposes in its SEC
    # filing; this specific headline overstates a verified AI use of proceeds.
    if "tesla secures $30 billion credit facility to fund ai infrastructure" in lower:
        return None
    if not (re.search(r"\bai\b", lower) or any(term in lower for term in _AI_CONTEXT)):
        return None
    if any(term in lower for term in _COMMENTARY):
        return None
    if any(term in lower for term in _PRESSURE) and any(term in lower for term in _DEBT_CONTEXT):
        return "融资压力"
    if any(term in lower for term in _DEBT_CONTEXT) and any(term in lower for term in _TRANSACTION):
        return "融资交易"
    return None


def parse_news_rss(xml: bytes, *, now: datetime | None = None) -> list[dict[str, str]]:
    """Create labeled leads from recent headlines; never manufacture deal terms."""
    now = now or datetime.now(timezone.utc)
    root = ElementTree.fromstring(xml)
    leads: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip()
        clean_title = title.rsplit(" - ", 1)[0].strip() if source and title.endswith(" - " + source) else title
        category = _headline_event(clean_title)
        link = (item.findtext("link") or "").strip()
        if not category or not link.startswith("https://news.google.com/rss/articles/"):
            continue
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        age_days = (now - published).total_seconds() / 86400
        if not 0 <= age_days <= 21:
            continue
        issuer = next((name for name in _ISSUERS if name.lower() in clean_title.lower()), "发行人待核验")
        amount = _MONEY.search(clean_title)
        if amount:
            magnitude = float(amount.group(1)) * (10 if amount.group(2).lower() in {"billion", "bn", "b"} else 0.01)
            qualifier = "最多" if re.search(r"\b(up to|as much as)\b", lower := clean_title.lower()) else "约"
            amount_text = f"新闻标题提及{qualifier}{magnitude:g}亿美元；待原始文件核验"
        else:
            amount_text = "新闻未提供可核验规模"
        key = (issuer, amount.group(0).lower() if amount else clean_title.lower(), category)
        if key in seen:
            continue
        seen.add(key)
        leads.append({
            "date": published.strftime("%Y-%m-%d"),
            "issuer": issuer,
            "purpose": f"{category}线索：{clean_title}。与本页关注的AI融资条件有关；具体用途待核验。",
            "size": amount_text,
            "pricing": "原始合同、票息或利差未核验",
            "status": f"新闻线索 · {source or '来源未标识'} · 待原始文件核验；不计分",
            "source": link,
            "headline": clean_title,
            "verified": False,
        })
    return sorted(leads, key=lambda lead: lead["date"], reverse=True)[:8]


@st.cache_data(ttl=NEWS_REFRESH_SECONDS, show_spinner=False)
def load_financing_news() -> tuple[list[dict[str, str]], str]:
    """Search broad news on page visits, no more than once per six hours."""
    response = requests.get(
        NEWS_RSS_URL,
        params={"q": NEWS_QUERY, "hl": "en-US", "gl": "US", "ceid": "US:en"},
        timeout=8,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AI-risk-dashboard/1.0)"},
    )
    response.raise_for_status()
    if len(response.content) > 2_000_000:
        raise ValueError("News feed is unexpectedly large")
    leads = parse_news_rss(response.content)
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return leads, checked_at
