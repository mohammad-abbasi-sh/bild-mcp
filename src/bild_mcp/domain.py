"""Domain logic: shape bild.de's official RSS feeds and article pages
into compact dicts (stdlib only).

Data source: the official BILD RSS feeds (no key, no login) — the
home feed (https://www.bild.de/feed/home.xml, 99 items) and one feed
per section (politik, sport, unterhaltung, digital, auto, reise,
geld — 100 items each) — plus article pages, whose full text lives
in the server-rendered <article> paragraphs (BILD pages carry NO
JSON-LD articleBody).

Honest limitations (verified live 2026-11-24):
- BILD article links carry NO ".html" suffix (they end in a 32-hex
  id) — so no suffix filter is applied; every feed item is returned
  as-is. A few feed items are promo/service pages (e.g. /bild-plus/,
  /gewinner-verlierer-.../) — genuine bild.de pages linked by the
  feed, returned as-is.
- The feeds carry a <bild:premium> flag (home feed: 12/99 premium),
  several <category> values per item, a media:content image
  (images.bild.de) and, on video stories, an HLS stream
  (application/x-mpegURL) — exposed as has_video. No author field.
- Article body: the <article> <p> tags ARE the body (free article
  sampled: 18 paragraphs, 5,368 chars). The nav blob and the
  repeated "+++ ..." teaser live OUTSIDE <article>, so they never
  reach the body; identical paragraphs are de-duplicated anyway.
  Filtered out: the "LIVE ... Quelle:" source line, the "Haben Sie
  eine Meinung zu diesem Artikel?" feedback line and the "Mobile
  Ansicht ..." footer line.
- PAYWALL: BILDplus articles expose ONLY a 2-paragraph teaser in
  <article> (365 chars sampled). The paywall signal is the JSON-LD
  NewsArticle "isAccessibleForFree" (false on BILDplus pages, true
  on free pages), with the embedded "contentAccessBlocked":true as
  fallback. A paywalled page returns paywalled=true with the teaser
  only — never fabricated text.
- The feed's <description> is the teaser (~120-160 chars).
- Only the listed sections exist as feeds: wirtschaft 404s on the
  live site — there is NO wirtschaft tool. Section feeds are
  /feed/<section>.xml.
"""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

BASE = "https://www.bild.de"
HEADLINES_FEED = f"{BASE}/feed/home.xml"

# One feed per section (verified 200, 2026-11-24; 100 items each).
# wirtschaft 404s — no feed exists.
SECTIONS = {
    "politik": f"{BASE}/feed/politik.xml",
    "sport": f"{BASE}/feed/sport.xml",
    "unterhaltung": f"{BASE}/feed/unterhaltung.xml",
    "digital": f"{BASE}/feed/digital.xml",
    "auto": f"{BASE}/feed/auto.xml",
    "reise": f"{BASE}/feed/reise.xml",
    "geld": f"{BASE}/feed/geld.xml",
}

_ALL_FEEDS = [HEADLINES_FEED] + list(SECTIONS.values())

_MEDIA_NS = "http://search.yahoo.com/mrss/"
_BILD_NS = "https://www.bild.de/spec"


def validate_limit(limit: int) -> int:
    """Clamp/validate the page size (feeds carry 99-100 items)."""
    if not 1 <= limit <= 150:
        raise ValueError(f"limit out of range: {limit} (expected 1..150)")
    return limit


def validate_section(section: str) -> str:
    """Normalise a section name to one of the seven section feeds."""
    s = (section or "").strip().casefold()
    if s not in SECTIONS:
        raise ValueError(
            f"unknown section: {section!r} (expected one of "
            f"{', '.join(sorted(SECTIONS))})"
        )
    return s


def _text(elem, tag: str) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text).strip()


def _iso(date_text: str) -> str | None:
    if not date_text:
        return None
    text = date_text.strip()
    # email.utils does not know CET/CEST (BILD feeds use them): map to
    # numeric offsets before parsing.
    text = re.sub(
        r"\s+(CET|CEST)$",
        lambda m: " +0100" if m.group(1) == "CET" else " +0200",
        text,
    )
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _published(item: ET.Element) -> str | None:
    """pubDate (RSS 2.0) or dc:date — matched by local name."""
    for child in item:
        local = child.tag.rsplit("}", 1)[-1]
        if local in ("pubDate", "date") and child.text:
            return _iso(child.text)
    return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def compact_item(item: ET.Element) -> dict | None:
    """One RSS 2.0 <item>: title, link, teaser, publish time, the
    BILDplus flag, the category list, the image URL (first
    image/jpeg media:content) and has_video (an HLS media:content
    is attached).

    Returns None for off-site links (none seen in the feeds, but
    the guard keeps the contract explicit).
    """
    link = _text(item, "link")
    if not link.startswith("https://www.bild.de/"):
        return None
    title = _text(item, "title")
    description = _strip_tags(_text(item, "description"))
    if not title:
        title = description
    categories = [
        html.unescape(c.text).strip()
        for c in item.findall("category")
        if c.text and c.text.strip()
    ]
    premium = False
    image_url = None
    has_video = False
    # media:content lives both as a direct child and inside
    # <media:group> (the HLS video streams live in the group) — walk
    # all descendants, not just direct children.
    for child in item.iter():
        if child is item:
            continue
        local = _local(child.tag)
        if local == "premium":
            premium = (child.text or "").strip().casefold() == "true"
        elif local == "content":
            mime = (child.get("type") or "").strip()
            url = (child.get("url") or "").strip()
            if mime == "image/jpeg" and url and image_url is None:
                image_url = html.unescape(url)
            elif mime == "application/x-mpegURL":
                has_video = True
        elif local == "thumbnail":
            if image_url is None:
                url = (child.get("url") or "").strip()
                if url:
                    image_url = html.unescape(url)
    return {
        "title": title,
        "link": link,
        "description": description,
        "published": _published(item),
        "premium": premium,
        "categories": categories,
        "image_url": image_url,
        "has_video": has_video,
    }


def parse_rss(xml_text: str) -> dict:
    """Parse a BILD RSS 2.0 feed into {feed_title, count, items}.

    Raises ValueError on malformed XML or a non-RSS document.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"invalid RSS XML: {e}") from e
    channel = root.find("channel")
    if channel is None:
        raise ValueError("unexpected RSS shape: no <channel> element")
    items = []
    for it in channel.findall("item"):
        compacted = compact_item(it)
        if compacted is not None:
            items.append(compacted)
    return {
        "feed_title": _text(channel, "title"),
        "count": len(items),
        "items": items,
    }


_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.S | re.I,
)
_ARTICLE_RE = re.compile(r"<article[^>]*>(.*?)</article>", re.S | re.I)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_OG_DESC_RE = re.compile(
    r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
    re.S | re.I,
)


def _author_name(raw) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return str(raw.get("name") or "").strip()
    if isinstance(raw, list):
        names = [_author_name(a) for a in raw]
        return ", ".join(n for n in names if n)
    return ""


def _ld_blocks(html_text: str) -> list:
    """JSON-LD blocks (a block may be a single object or a list)."""
    blocks: list[dict] = []
    for match in _LD_JSON_RE.finditer(html_text):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            blocks.append(data)
        elif isinstance(data, list):
            blocks.extend(b for b in data if isinstance(b, dict))
    return blocks


def _page_title(html_text: str) -> str:
    match = _TITLE_RE.search(html_text)
    if not match:
        return ""
    title = _strip_tags(match.group(1))
    return re.sub(r"\s*\|\s*BILD\.de\s*$", "", title, flags=re.I)


def _ssr_body(
    html_text: str, title: str, description: str, author: str = ""
) -> str:
    """Body text from the server-rendered <article> paragraphs.

    Filters out the "LIVE ... Quelle:" source line, the byline
    fragments (the author names are rendered as single-token
    paragraphs), the feedback line ("Haben Sie eine Meinung zu
    diesem Artikel? ..."), the footer line ("Mobile Ansicht ...")
    and repeats of the title / description, and de-duplicates
    identical paragraphs. Raises ValueError when no usable body
    paragraphs are found.
    """
    match = _ARTICLE_RE.search(html_text)
    if not match:
        raise ValueError(
            "no article text found on this page (no <article> body) — "
            "the page may be JS-rendered or an error page"
        )
    author_tokens = {
        t.casefold() for t in re.split(r"[^A-Za-zÀ-ÿ-]+", author) if t
    }
    paras: list[str] = []
    seen: set[str] = set()
    for raw in _P_RE.findall(match.group(1)):
        text = _strip_tags(raw)
        if not text:
            continue
        if text.startswith("LIVE") and "Quelle:" in text:
            continue  # live-ticker source line, not article text
        if " " not in text and text.casefold() in author_tokens:
            continue  # byline fragment: a bare author-name token
        if text.startswith("Haben Sie eine Meinung zu diesem Artikel?"):
            continue  # feedback line, not article text
        if text.startswith("Mobile Ansicht"):
            continue  # footer line, not article text
        if title and text == title:
            continue  # header paragraph: the title again
        if description and text == description:
            continue  # teaser paragraph: the description again
        if text in seen:
            continue  # repeated paragraph (teaser echo)
        seen.add(text)
        paras.append(text)
    body = "\n\n".join(paras).strip()
    if not body:
        raise ValueError(
            "no article text found on this page (the <article> body is "
            "empty after filtering)"
        )
    return body


def parse_article(html_text: str) -> dict:
    """Extract the article from a bild.de page.

    Metadata comes from the JSON-LD NewsArticle block (headline,
    description, author list, datePublished, isAccessibleForFree);
    the body comes from the server-rendered <article> paragraphs
    (BILD pages carry no JSON-LD articleBody). A BILDplus page
    (isAccessibleForFree=false, or the embedded
    "contentAccessBlocked":true) returns paywalled=true with only
    the teaser paragraphs as body — never fabricated text. Returns
    {title, description, body, author, published, word_count,
    teaser_only, paywalled, kind}. Raises ValueError when no usable
    text is found.
    """
    blocks = _ld_blocks(html_text)
    article_block = None
    for block in blocks:
        if block.get("@type") in ("NewsArticle", "Article"):
            article_block = block
            break

    title = _page_title(html_text)
    description = ""
    og = _OG_DESC_RE.search(html_text)
    if og:
        description = html.unescape(og.group(1)).strip()

    paywalled = False
    if article_block is not None:
        free = article_block.get("isAccessibleForFree")
        if free is not None:
            paywalled = not bool(free)
        title = (
            _strip_tags(str(article_block.get("headline") or "")) or title
        )
        description = description or _strip_tags(
            str(article_block.get("description") or "")
        )
    if '"contentAccessBlocked":true' in html_text:
        paywalled = True
    elif (
        '"contentAccessBlocked":false' in html_text
        and article_block is None
    ):
        paywalled = False
    if not paywalled and description.endswith("– BILDplus!"):
        # og:description of a BILDplus page ends with the marker;
        # the LD description does not carry it, so this only fires
        # when no NewsArticle block was found.
        if article_block is None:
            paywalled = True

    body_author = ""
    published = None
    if article_block is not None:
        body_author = _author_name(article_block.get("author"))
        published = str(article_block.get("datePublished") or "") or None
    body = _ssr_body(html_text, title, description, body_author)
    teaser_only = paywalled or (bool(body) and body == description)
    return {
        "title": title,
        "description": description,
        "body": body,
        "author": body_author,
        "published": published,
        "word_count": len(body.split()),
        "teaser_only": teaser_only,
        "paywalled": paywalled,
        "kind": "article",
    }


def search_items(items: list, query: str) -> list:
    """Case-insensitive substring match over title + description."""
    q = (query or "").strip().casefold()
    if not q:
        raise ValueError("query must not be empty")
    return [
        it for it in items
        if q in (it.get("title") or "").casefold()
        or q in (it.get("description") or "").casefold()
    ]


def dedupe_sort(items: list) -> list:
    """De-duplicate by link, newest first (empty publish time sorts last)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for it in items:
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        unique.append(it)
    unique.sort(key=lambda it: it.get("published") or "", reverse=True)
    return unique
