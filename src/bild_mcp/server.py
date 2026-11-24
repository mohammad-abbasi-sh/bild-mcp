"""MCP server: unofficial read-only access to BILD (bild.de) —
Germany's largest tabloid / digital news brand — via its official
RSS feeds (home feed, one feed per section) and article pages
(full text from the server-rendered <article> paragraphs; BILD
pages carry no JSON-LD articleBody). No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for BILD (bild.de) — Germany's
largest tabloid and digital news brand — via its official RSS feeds
(no key, no login) and article pages. The home feed (99 items,
newest first, with teaser, categories, image and the BILDplus
flag), news by section (politik, sport, unterhaltung, digital,
auto, reise, geld — 100 items each), keyword search across all
feeds, video stories (items with an embedded video stream),
BILDplus stories, and full article text (the server-rendered
<article> paragraphs — BILD pages carry no JSON-LD articleBody).
BILDplus articles expose only a 2-paragraph teaser: they are
reported as paywalled=true with the teaser only, never fabricated
text.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · \
https://mabbasi.ir — Germany MCP factory.\
"""


_SOURCE = "www.bild.de"
_DISCLAIMER = "Unofficial read-only data from BILD's public RSS feeds and article pages; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("bild-mcp", instructions=INSTRUCTIONS)


def _feed(url: str, limit: int) -> dict:
    """Fetch one BILD RSS 2.0 feed and return its items, newest first, capped."""
    parsed = _dom.parse_rss(_http.fetch_feed(url))
    items = parsed["items"][:limit]
    return {
        "feed_title": parsed["feed_title"],
        "total_results": parsed["count"],
        "count": len(items),
        "items": items,
    }


def _all_items() -> list:
    """All items of the home feed plus every section feed, de-duplicated
    by link and sorted newest first."""
    all_items: list[dict] = []
    for url in _dom._ALL_FEEDS:
        parsed = _dom.parse_rss(_http.fetch_feed(url))
        all_items.extend(parsed["items"])
    return _dom.dedupe_sort(all_items)


@mcp.tool()
def bild_headlines(limit: int = 10) -> str:
    """Top BILD headlines (official RSS home feed, ~99 items), newest
first. limit: 1..150 (default 10). Every item carries a title, a
per-article link for bild_get_article, a teaser (description), the
BILDplus flag (premium), the category list, an image URL, a
has_video flag and publish time."""
    try:
        lim = _dom.validate_limit(limit)
        out = _feed(_dom.HEADLINES_FEED, lim)
    except (_http.BildError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def bild_section_news(section: str, limit: int = 10) -> str:
    """Newest BILD news of one section, from its own official RSS feed.
section: "politik", "sport", "unterhaltung", "digital", "auto",
"reise" or "geld". limit: 1..150 (default 10). Items carry title,
link (a per-article URL for bild_get_article), teaser, the
BILDplus flag (premium), the category list, an image URL, a
has_video flag and publish time."""
    try:
        sec = _dom.validate_section(section)
        lim = _dom.validate_limit(limit)
        out = _feed(_dom.SECTIONS[sec], lim)
        out["section"] = sec
    except (_http.BildError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def bild_search_news(query: str, limit: int = 10) -> str:
    """Search BILD news by keyword (title + teaser)
across the home feed and all seven section feeds. query: free
text, e.g. "Bayern" or "Bundesliga". limit: 1..150 (default 10).
Searches ~800 items client-side, newest first, de-duplicated by
link."""
    try:
        if not (query or "").strip():
            return _ok({"error": "query must not be empty"})
        lim = _dom.validate_limit(limit)
        found = _dom.search_items(_all_items(), query.strip())
        out = {
            "query": query.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.BildError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def bild_videos(limit: int = 10) -> str:
    """Newest BILD stories with an embedded video (items whose feed
entry carries an HLS video stream), across the home feed and all
seven section feeds. limit: 1..150 (default 10). Items carry
title, link (a per-article URL for bild_get_article), teaser, the
BILDplus flag, the category list, an image URL and publish time."""
    try:
        lim = _dom.validate_limit(limit)
        videos = [i for i in _all_items() if i.get("has_video")]
        out = {
            "total_results": len(videos),
            "count": min(lim, len(videos)),
            "items": videos[:lim],
        }
    except (_http.BildError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def bild_premium_news(limit: int = 10) -> str:
    """Newest BILDplus stories (behind the BILDplus paywall — the
feed's <bild:premium> flag), across the home feed and all seven
section feeds. limit: 1..150 (default 10). Items carry title,
link (a per-article URL for bild_get_article), teaser, the
category list, an image URL, a has_video flag and publish time.
bild_get_article returns paywalled=true with only the teaser for
these — the full text needs a BILDplus subscription."""
    try:
        lim = _dom.validate_limit(limit)
        premium = [i for i in _all_items() if i.get("premium")]
        out = {
            "total_results": len(premium),
            "count": min(lim, len(premium)),
            "items": premium[:lim],
        }
    except (_http.BildError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def bild_get_article(url: str) -> str:
    """Full text of one BILD article page (the server-rendered
<article> paragraphs — BILD pages carry no JSON-LD articleBody).
url: a www.bild.de article URL, e.g. from bild_headlines
(/<section>/<slug>-<32-hex-id>). Returns title, author, publish
time, the body text and its word count. BILDplus articles return
paywalled=true with only the 2-paragraph teaser as body — the
full text needs a BILDplus subscription. Feed URLs, the home page
and off-site links are refused. Nothing is ever fabricated."""
    try:
        if not (url or "").strip():
            return _ok({"error": "url must not be empty"})
        url = url.strip()
        article = _dom.parse_article(_http.fetch_article(url))
        paywalled = article["paywalled"]
        note = ""
        if paywalled:
            note = (
                "This article is a BILDplus story: only the teaser is "
                "available; the full text needs a BILDplus subscription."
            )
        elif article["teaser_only"]:
            note = (
                "Only the teaser is available for this item; the teaser "
                "is the whole freely available text."
            )
        out = {
            "url": url,
            "title": article["title"],
            "author": article["author"],
            "published": article["published"],
            "kind": article["kind"],
            "paywalled": paywalled,
            "teaser_only": article["teaser_only"],
            "word_count": article["word_count"],
            "body": article["body"],
            "description": article["description"],
            "note": note,
        }
    except (_http.BildError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def bild_health() -> str:
    """Check whether the BILD home feed is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
