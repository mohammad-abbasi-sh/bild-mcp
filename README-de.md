# bild-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/bild-mcp

Inoffizieller **Read-only**-MCP-Server für **[BILD](https://www.bild.de)** — Deutschlands größte Boulevardzeitung und digitale Nachrichtenmarke (80,22 Mio. Besuche im Oktober 2026, DE-Rang #21 laut SEMrush) — über die offiziellen RSS-Feeds (Hauptfeed, ein Feed je Ressort) und Artikelseiten, deren Volltext aus den serverseitig gerenderten `<article>`-Absätzen gelesen wird (BILD-Seiten tragen kein JSON-LD-`articleBody`). Top-Schlagzeilen, Nachrichten nach Ressort (politik, sport, unterhaltung, digital, auto, reise, geld), Stichwortsuche, Video-Geschichten, BILDplus-Geschichten und Volltexte von Artikeln. Kein Schlüssel, kein Login.

> Gebaut von Mohammad Abbasi als Teil der "Germany MCP factory" (Sepehr-ähnliche Pipeline). Nicht mit BILD oder Axel Springer verbunden.

## Für KI-Agenten

In die MCP-Client-Konfiguration eintragen (stdio):

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

Oder lokal starten: `python -m bild_mcp.server` (benötigt `mcp<2`, `httpx`).

## Tools

| Tool | Beschreibung |
|------|-------------|
| `bild_headlines` | Top-Schlagzeilen von BILD (offizieller RSS-Hauptfeed, ~99 Einträge), neueste zuerst — `limit` 1..150. Jeder Eintrag trägt Titel, Artikel-Link, Teaser, BILDplus-Kennzeichen (`premium`), Kategorienliste, Bild-URL, `has_video`-Kennzeichen und Veröffentlichungszeit |
| `bild_section_news` | Neueste BILD-Nachrichten eines Ressorts, aus dem eigenen offiziellen RSS-Feed — `section`: "politik", "sport", "unterhaltung", "digital", "auto", "reise" oder "geld", `limit` 1..150 |
| `bild_search_news` | Stichwortsuche in den BILD-Nachrichten (Titel + Teaser) über Hauptfeed und alle sieben Ressort-Feeds (~800 Einträge) — `query` (z. B. "Bayern"), `limit` 1..150 |
| `bild_videos` | Neueste BILD-Geschichten mit eingebettetem Video (Einträge, deren Feed-Eintrag einen HLS-Videostream trägt), über alle Feeds — `limit` 1..150 |
| `bild_premium_news` | Neueste BILDplus-Geschichten (hinter der BILDplus-Paywall — das `<bild:premium>`-Kennzeichen des Feeds), über alle Feeds — `limit` 1..150 |
| `bild_get_article` | Volltext einer BILD-Artikelseite (serverseitig gerenderte `<article>`-Absätze) — `url`: eine www.bild.de-Artikel-URL (/<ressort>/<slug>-<32-Hex-ID>). BILDplus-Artikel liefern `paywalled: true` und nur den 2-absätzigen Teaser als Text — der Volltext braucht ein BILDplus-Abo. Feed-URLs, die Startseite und externe Links werden abgelehnt |
| `bild_health` | Erreichbarkeitsprüfung (ok / blocked / error) — eine höfliche Anfrage |

Beispielausgabe (`bild_headlines`, `limit` 2):

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

Hinweise:
- Der Server liest die **offiziellen RSS-Feeds** (Hauptfeed 99 Einträge; Ressort-Feeds je 100 Einträge: politik/sport/unterhaltung/digital/auto/reise/geld — live verifiziert 2026-11-24). Suche, Videos und Premium laufen clientseitig über die geladenen Feeds (~800 Einträge).
- BILD-Artikel-Links tragen **kein `.html`-Suffix** (sie enden in einer 32-stelligen Hex-ID) — es wird also kein Suffix-Filter angewendet; jeder Feed-Eintrag wird unverändert zurückgegeben. Ein paar Feed-Einträge sind Promo-/Serviceseiten (z. B. `/bild-plus/`, `/gewinner-verlierer-.../`) — echte bild.de-Seiten aus dem Feed, unverändert zurückgegeben.
- Die Feeds tragen ein **`<bild:premium>`-Kennzeichen** (Hauptfeed: 12/99 Premium), mehrere **`<category>`-Werte** je Eintrag, ein `media:content`-Bild (images.bild.de, bei allen 99 Hauptfeed-Einträgen vorhanden) und bei Video-Geschichten einen HLS-Stream (`application/x-mpegURL`, 16/99 Hauptfeed-Einträge) — als `has_video` ausgewiesen. Die HLS-Streams liegen innerhalb von `<media:group>`, der Parser durchläuft daher alle Nachkommen. Kein Autorenfeld.
- Die `pubDate`-Werte der Feeds verwenden **CET/CEST** (z. B. `11:17:46 CET`) — `email.utils` kennt diese Zonen nicht, sie werden vor dem Parsen auf numerische Offsets abgebildet (11:17:46 CET → 10:17:46 UTC).
- **Artikeltexte, ehrlich:** BILD-Seiten tragen KEIN JSON-LD-`articleBody` — der Text kommt aus den serverseitig gerenderten `<article>`-Absätzen (732 Wörter in der Stichprobe für einen freien Artikel). Der Navigations-Block und der wiederholte "+++ ..."-Teaser liegen AUSSERHALB von `<article>`, sie erreichen den Text also nie; identische Absätze werden ohnehin dedupliziert. Herausgefiltert: die "LIVE ... Quelle:"-Quellenzeile, die Byline-Fragmente (Autorennamen als Einzel-Token-Absätze), die "Haben Sie eine Meinung zu diesem Artikel?"-Feedbackzeile und die "Mobile Ansicht ..."-Fußzeile.
- **Paywall, ehrlich:** BILDplus-Artikel zeigen NUR einen 2-absätzigen Teaser in `<article>` (55 Wörter in der Stichprobe). Das Paywall-Signal ist das JSON-LD-NewsArticle-`isAccessibleForFree` (false bei BILDplus-Seiten, true bei freien Seiten), mit dem eingebetteten `"contentAccessBlocked":true` als Fallback. Eine Paywall-Seite liefert `paywalled: true` und nur den Teaser — niemals erfundenen Text. Das `<bild:premium>`-Kennzeichen des Feeds ist dasselbe Signal auf Feed-Ebene.
- Nur die aufgeführten Ressorts existieren als Feeds — wirtschaft liefert auf der Live-Seite 404; es gibt KEIN wirtschaft-Tool. Ressort-Feeds liegen unter `/feed/<ressort>.xml`.
- Daten: öffentliche BILD-RSS-Feeds und Artikelseiten — kein Schlüssel, kein Login, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parst die echten, gespeicherten Haupt-, Politik- und Sport-Feeds sowie zwei echte Artikelseiten (einen freien Artikel und einen BILDplus-Artikel)
- `tests/test_live.py` — vorsichtige Live-Anfragen an www.bild.de

Tests: 27/27 grün (20 offline + 7 live, 2026-11-24).

## Lizenz

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — frei für private und nicht-kommerzielle Nutzung; kommerzielle Nutzung braucht eine separate Lizenz (siehe LICENSE).

---

Gebaut von [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
