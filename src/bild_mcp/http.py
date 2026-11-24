"""HTTP layer for bild_mcp — plain httpx GETs against www.bild.de.

Endpoints, all public, no key, no login:
- the official RSS feeds: the home feed
  https://www.bild.de/feed/home.xml and one feed per section
  (https://www.bild.de/feed/<politik|sport|unterhaltung|digital|
  auto|reise|geld>.xml)
- article pages: https://www.bild.de/<section>/<slug>-<32-hex-id>
  — the full text is read from the server-rendered <article>
  paragraphs (see domain.parse_article); BILD pages carry no
  JSON-LD articleBody.

Only www.bild.de is ever fetched. Feed items that link off-site are
never fetched: fetch_article only accepts www.bild.de article URLs.
"""
from __future__ import annotations

import os
import ssl
import time
from urllib.parse import urlparse

import httpx

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 25.0
ALLOWED_HOSTS = ("www.bild.de",)
HEALTH_URL = "https://www.bild.de/feed/home.xml"


class BildError(RuntimeError):
    pass


def _verify():
    """TLS trust store: the OS bundle when present, else httpx/certifi.

    The OS bundle matters behind MITM egress proxies (their CA is in the
    system store, not in certifi) and is the right default on Linux
    anyway; on systems without it we fall back to certifi.
    """
    for path in (
        "/etc/ssl/certs/ca-certificates.crt",
        ssl.get_default_verify_paths().openssl_cafile,
    ):
        if path and os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return True


def _client(accept: str) -> httpx.Client:
    # NOTE: we read the proxy URL from the environment but never log it.
    # trust_env=False because httpx fails to parse bracketed IPv6 entries
    # (e.g. [::1]) that some environments put in no_proxy.
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    return httpx.Client(
        headers={"User-Agent": UA, "Accept": accept},
        timeout=TIMEOUT,
        proxy=proxy or None,
        trust_env=False,
        verify=_verify(),
        follow_redirects=True,
    )


def _check_host(url: str) -> None:
    host = (urlparse(url).netloc or "").lower()
    if host not in ALLOWED_HOSTS:
        raise BildError(
            f"only {', '.join(ALLOWED_HOSTS)} pages are fetched "
            f"(got {host or url!r})"
        )


def _get(url: str, accept: str) -> str:
    """GET with one retry on 429/5xx and on transient network errors."""
    _check_host(url)
    last_exc: Exception | None = None
    r: httpx.Response | None = None
    for attempt in range(2):
        try:
            with _client(accept) as c:
                r = c.get(url)
        except httpx.HTTPError as e:
            last_exc = e
            if attempt == 0:
                time.sleep(1.0)
                continue
            raise BildError(f"network error fetching {url}: {e}") from e
        if r.status_code in (429, 500, 502, 503):
            if attempt == 0:
                time.sleep(1.0)
                continue
        break
    assert r is not None  # loop always assigns r or raises
    if r.status_code == 403:
        raise BildError(
            f"www.bild.de returned HTTP 403 for {url} (bot wall) — try again later"
        )
    if r.status_code == 429:
        raise BildError(
            "www.bild.de rate-limited the request (HTTP 429) — try again later"
        )
    if r.status_code != 200:
        raise BildError(f"www.bild.de returned HTTP {r.status_code} for {url}")
    return r.text


def fetch_feed(url: str) -> str:
    """GET an official BILD RSS feed; returns the raw XML text."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = parsed.path
    ok = (
        host in ALLOWED_HOSTS
        and path.startswith("/feed/")
        and path.endswith(".xml")
    )
    if not ok:
        raise BildError(f"only BILD RSS feed URLs are fetched (got {url!r})")
    return _get(url, "application/rss+xml, application/xml, text/xml, */*")


def fetch_article(url: str) -> str:
    """GET one www.bild.de article page; returns the raw HTML text.

    Article URLs are /<section>/<slug>-<32-hex-id> (no .html suffix).
    Feed URLs (/feed/*.xml), the home page and any other host are
    refused.
    """
    parsed = urlparse(url)
    if parsed.fragment:
        raise BildError(
            "URLs with a fragment are not articles (got {url!r})".format(url=url)
        )
    path = parsed.path
    if path.startswith("/feed/") or path.endswith((".xml", ".rss")):
        raise BildError(
            "only www.bild.de article URLs are fetched — feed URLs are "
            f"not articles (got {url!r})"
        )
    if path in ("", "/"):
        raise BildError(
            "only www.bild.de article URLs are fetched — the home page "
            f"is not an article (got {url!r})"
        )
    return _get(url, "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")


def health_check() -> dict:
    """One polite probe of the source feed.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `bild_health` tool
    and the daily smoke CI.
    """
    url = HEALTH_URL
    try:
        fetch_feed(url)
    except BildError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
