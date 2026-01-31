"""RSS feed fetcher and morning briefing formatter.

Uses only Python stdlib — no external dependencies.
"""
from __future__ import annotations

import html
import logging
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

log = logging.getLogger(__name__)

DEFAULT_FEEDS = [
    ("Hacker News", "https://news.ycombinator.com/rss"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
]

_USER_AGENT = "Homestead/1.0 (RSS reader)"
_TIMEOUT = 10


@dataclass
class FeedItem:
    title: str
    link: str
    summary: str
    source: str


def fetch_rss(url: str, source: str = "", limit: int = 5) -> list[FeedItem]:
    """Fetch and parse an RSS feed. Returns up to *limit* items."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = resp.read()
    except Exception as exc:
        log.warning("Failed to fetch RSS from %s: %s", url, exc)
        return []

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        log.warning("Failed to parse RSS from %s: %s", url, exc)
        return []

    items: list[FeedItem] = []
    # Standard RSS 2.0: channel/item
    for item in root.iter("item"):
        if len(items) >= limit:
            break
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        # Strip HTML tags from description
        summary = _strip_html(desc)[:200]
        if title:
            items.append(FeedItem(title=title, link=link, summary=summary, source=source))

    # Atom feeds: entry
    if not items:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.iter("entry"):
            if not items or len(items) >= limit:
                if len(items) >= limit:
                    break
            title = (entry.findtext("title") or entry.findtext("atom:title", namespaces=ns) or "").strip()
            link_el = entry.find("link")
            link = link_el.get("href", "") if link_el is not None else ""
            summary_el = entry.findtext("summary") or entry.findtext("atom:summary", namespaces=ns) or ""
            summary = _strip_html(summary_el.strip())[:200]
            if title:
                items.append(FeedItem(title=title, link=link, summary=summary, source=source))

    return items


def get_briefing(
    feeds: list[tuple[str, str]] | None = None,
    items_per_feed: int = 5,
) -> str:
    """Fetch multiple feeds and format as Telegram HTML."""
    feeds = feeds or DEFAULT_FEEDS
    all_items: list[FeedItem] = []

    for name, url in feeds:
        items = fetch_rss(url, source=name, limit=items_per_feed)
        all_items.extend(items)

    if not all_items:
        return "<b>Morning Briefing</b>\n\nNo news available right now."

    lines = ["<b>Morning Briefing</b>", ""]
    current_source = ""
    for item in all_items:
        if item.source != current_source:
            current_source = item.source
            lines.append(f"\n<b>{html.escape(current_source)}</b>")
        title = html.escape(item.title)
        if item.link:
            lines.append(f"  • <a href=\"{item.link}\">{title}</a>")
        else:
            lines.append(f"  • {title}")
        if item.summary:
            lines.append(f"    <i>{html.escape(item.summary[:100])}</i>")

    return "\n".join(lines)


def _strip_html(text: str) -> str:
    """Naive HTML tag stripper."""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    clean = html.unescape(clean)
    return clean.strip()
