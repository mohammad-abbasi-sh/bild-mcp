# bild-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/bild-mcp

Unofficial **read-only** MCP server for **[BILD](https://www.bild.de)** — Germany's largest tabloid and digital news brand (80.22M visits in October 2026, DE rank #21 per SEMrush) — via its official RSS feeds (the home feed, one feed per section) and article pages, whose full text is read from the server-rendered `<article>` paragraphs (BILD pages carry no JSON-LD `articleBody`). Top headlines, news by section (politik, sport, unterhaltung, digital, auto, reise, geld), keyword search, video stories, BILDplus stories, and full article text. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory" (Sepehr-style pipeline). Not affiliated with BILD or Axel Springer.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "bild": {
      "command": "uvx",
      "args": ["bild-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m bild_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `bild_headlines` | Top BILD headlines (official RSS home feed, ~99 items), newest first — `limit` 1..150. Every item carries a title, a per-article link, a teaser, the BILDplus flag (`premium`), the category list, an image URL, a `has_video` flag and publish time |
| `bild_section_news` | Newest BILD news of one section, from its own official RSS feed — `section`: "politik", "sport", "unterhaltung", "digital", "auto", "reise" or "geld", `limit` 1..150 |
| `bild_search_news` | Search BILD news by keyword (title + teaser) across the home feed and all seven section feeds (~800 items) — `query` (e.g. "Bayern"), `limit` 1..150 |
| `bild_videos` | Newest BILD stories with an embedded video (items whose feed entry carries an HLS video stream), across all feeds — `limit` 1..150 |
| `bild_premium_news` | Newest BILDplus stories (behind the BILDplus paywall — the feed's `<bild:premium>` flag), across all feeds — `limit` 1..150 |
| `bild_get_article` | Full text of one BILD article page (server-rendered `<article>` paragraphs) — `url`: a www.bild.de article URL (/<section>/<slug>-<32-hex-id>). BILDplus articles return `paywalled: true` with only the 2-paragraph teaser as body — the full text needs a BILDplus subscription. Feed URLs, the home page and off-site links are refused |
| `bild_health` | Reachability probe (ok / blocked / error) — one polite request |

Example output (`bild_headlines`, `limit` 2):

```json
{"feed_title": "BILD - Home", "total_results": 99, "count": 2,
 "items": [
  {"title": "Minister stellen neue Zahlen vor - Jede Woche werden vier Frauen durch häusliche Gewalt getötet",
   "link": "https://www.bild.de/leben-wissen/neue-bka-zahlen-vorgestellt-drastischer-anstieg-bei-gewalt-gegen-frauen-6b032922816dfbaedcce8a5c",
   "description": "Alle Delikte zeigen, besonders in drei Feldern. BILD erklärt die dramatischen Zahlen.",
   "published": "2026-11-24T10:17:46+00:00", "premium": false,
   "categories": ["Leben & Wissen", "Kriminalstatistik", "Initiative BILD gegen Gewalt an Frauen", "Gewalt", "Polizei", "Häusliche Gewalt", "Team First", "sexueller Missbrauch"],
   "image_url": "https://images.bild.de/6b032922816dfbaedcce8a5c/87ee9a4fc504d7c00d4c2bb29a696909,2dd42395?w=1280",
   "has_video": false},
  ...]}
```

Notes:
- The server reads the **official RSS feeds** (home feed 99 items; section feeds 100 items each: politik/sport/unterhaltung/digital/auto/reise/geld — verified live 2026-11-24). Search, videos and premium run client-side over the fetched feeds (~800 items).
- BILD article links carry **no `.html` suffix** (they end in a 32-hex id) — so no suffix filter is applied; every feed item is returned as-is. A few feed items are promo/service pages (e.g. `/bild-plus/`, `/gewinner-verlierer-.../`) — genuine bild.de pages linked by the feed, returned as-is.
- The feeds carry a **`<bild:premium>` flag** (home feed: 12/99 premium), several **`<category>` values** per item, a `media:content` image (images.bild.de, present on all 99 home items) and, on video stories, an HLS stream (`application/x-mpegURL`, 16/99 home items) — exposed as `has_video`. The HLS streams live inside `<media:group>`, so the parser walks all descendants. No author field.
- Feed `pubDate` values use **CET/CEST** (e.g. `11:17:46 CET`) — `email.utils` does not know those zones, so they are mapped to numeric offsets before parsing (11:17:46 CET → 10:17:46 UTC).
- **Article text, honestly:** BILD pages carry NO JSON-LD `articleBody` — the body comes from the server-rendered `<article>` paragraphs (732 words sampled for a free article). The nav blob and the repeated "+++ ..." teaser live OUTSIDE `<article>`, so they never reach the body; identical paragraphs are de-duplicated anyway. Filtered out: the "LIVE ... Quelle:" source line, the byline fragments (author names rendered as single-token paragraphs), the "Haben Sie eine Meinung zu diesem Artikel?" feedback line and the "Mobile Ansicht ..." footer line.
- **Paywall, honestly:** BILDplus articles expose ONLY a 2-paragraph teaser in `<article>` (55 words sampled). The paywall signal is the JSON-LD NewsArticle `isAccessibleForFree` (false on BILDplus pages, true on free pages), with the embedded `"contentAccessBlocked":true` as fallback. A paywalled page returns `paywalled: true` with the teaser only — never fabricated text. The feed's `<bild:premium>` flag is the same signal at feed level.
- Only the listed sections exist as feeds — wirtschaft 404s on the live site; there is NO wirtschaft tool. Section feeds are `/feed/<section>.xml`.
- Data: BILD public RSS feeds and article pages — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses the real captured home, politik and sport feeds plus two real article pages (a free article and a BILDplus article)
- `tests/test_live.py` — cautious live requests against www.bild.de

Tests: 27/27 green (20 offline + 7 live, 2026-11-24).

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — free for personal and non-commercial use; commercial use needs a separate license (see LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
