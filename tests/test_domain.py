"""Offline tests — parse the real captured bild.de RSS feeds and two
real article pages (a free NewsArticle and a BILDplus article whose
JSON-LD isAccessibleForFree is false), no network."""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from bild_mcp import domain as dom
from bild_mcp import http as http_mod

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class TestHeadlinesFeed:
    def test_main_shape(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert parsed["feed_title"] == "BILD - Home"
        assert parsed["count"] == 99
        assert len(parsed["items"]) == 99

    def test_main_first_item(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        first = parsed["items"][0]
        assert first["title"] == (
            "Minister stellen neue Zahlen vor - Jede Woche werden vier "
            "Frauen durch häusliche Gewalt getötet"
        )
        assert first["link"] == (
            "https://www.bild.de/leben-wissen/"
            "neue-bka-zahlen-vorgestellt-drastischer-anstieg-bei-gewalt-"
            "gegen-frauen-6b032922816dfbaedcce8a5c"
        )
        assert first["description"].startswith(
            "Alle Delikte zeigen, besonders in drei Feldern."
        )
        # pubDate "11:17:46 CET" is 10:17:46 UTC — CET must be
        # converted, not treated as UTC.
        assert first["published"] == "2026-11-24T10:17:46+00:00"
        assert first["premium"] is False
        assert first["has_video"] is False
        assert first["categories"] == [
            "Leben & Wissen",
            "Kriminalstatistik",
            "Initiative BILD gegen Gewalt an Frauen",
            "Gewalt",
            "Polizei",
            "Häusliche Gewalt",
            "Team First",
            "sexueller Missbrauch",
        ]
        assert first["image_url"].startswith(
            "https://images.bild.de/6b032922816dfbaedcce8a5c/"
        )

    def test_main_items_all_have_title_description_image(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert all(i["title"] and i["description"] for i in parsed["items"])
        assert all(i["image_url"] for i in parsed["items"])
        assert all(
            i["link"].startswith("https://www.bild.de/")
            for i in parsed["items"]
        )

    def test_premium_and_video_counts(self):
        # The home feed mixes free and BILDplus items and video
        # stories (HLS streams live inside <media:group>).
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert sum(1 for i in parsed["items"] if i["premium"]) == 12
        assert sum(1 for i in parsed["items"] if i["has_video"]) == 16


class TestSectionFeeds:
    def test_politik_shape(self):
        parsed = dom.parse_rss(_read("section-politik.xml"))
        assert parsed["feed_title"] == "BILD - Politik"
        assert parsed["count"] == 100
        assert len(parsed["items"]) == 100

    def test_politik_first_item(self):
        parsed = dom.parse_rss(_read("section-politik.xml"))
        first = parsed["items"][0]
        assert first["title"] == (
            "Kanzler rügt Altkanzlerin - Merz rechnet mit Merkels "
            "Nato-Politik ab"
        )
        assert first["link"].startswith("https://www.bild.de/politik/")
        assert first["premium"] is False

    def test_sport_shape(self):
        parsed = dom.parse_rss(_read("section-sport.xml"))
        assert parsed["feed_title"] == "BILD - Sport"
        assert parsed["count"] == 100
        assert sum(1 for i in parsed["items"] if i["premium"]) == 23


class TestArticle:
    def test_free_article(self):
        art = dom.parse_article(_read("article-free.html"))
        assert art["kind"] == "article"
        assert art["title"] == (
            "Neue BKA-Zahlen vorgestellt: Drastischer Anstieg bei "
            "Gewalt gegen Frauen | Leben & Wissen"
        )
        # The LD author list keeps the source's own double space.
        assert art["author"] == (
            "Laura  Krimmer, Franz Solms-Laubach, Burkhard Uhlenbroich"
        )
        assert art["published"] == "2026-11-24T10:17:46.168Z"
        assert art["word_count"] == 732
        assert art["paywalled"] is False
        assert art["teaser_only"] is False

    def test_free_article_body_is_ssr(self):
        # BILD pages carry NO JSON-LD articleBody — the body is the
        # server-rendered <article> paragraphs.
        art = dom.parse_article(_read("article-free.html"))
        assert art["body"].startswith(
            "Berlin – Schläge, Vergewaltigungen, Stalking, Frauenhass!"
        )
        assert "Die Polizei registrierte 2025 insgesamt 1176 weibliche" in art["body"]
        assert art["description"].startswith(
            "Die BKA-Lagebilder zeigen eine dramatische Entwicklung"
        )

    def test_free_article_body_filters_noise(self):
        # The byline fragments (bare author-name tokens), the LIVE
        # source line, the feedback line and the footer line must
        # not leak into the body.
        art = dom.parse_article(_read("article-free.html"))
        assert "Krimmer" not in art["body"]
        assert "Solms-Laubach" not in art["body"]
        assert "LIVEQuelle" not in art["body"]
        assert "Haben Sie eine Meinung" not in art["body"]
        assert "Mobile Ansicht" not in art["body"]
        # The repeated "+++ ..." teaser lives outside <article>.
        assert "+++Minister stellen" not in art["body"]

    def test_premium_article_is_paywalled(self):
        art = dom.parse_article(_read("article-premium.html"))
        assert art["kind"] == "article"
        assert art["title"] == (
            "Borussia Mönchengladbach: Rouven Schröder rüffelt diese "
            "Stars! | Sport"
        )
        assert art["author"] == "Dirk Krümpelmann"
        assert art["published"] == "2026-11-24T10:08:27.543Z"
        assert art["paywalled"] is True
        assert art["teaser_only"] is True
        # Only the 2-paragraph teaser is exposed — never the full text.
        assert art["word_count"] == 55
        assert art["body"].startswith(
            "Gladbach steht nach zehn Spieltagen auf dem letzten "
            "Tabellenplatz"
        )
        assert "Krümpelmann" not in art["body"]
        assert art["description"].endswith("– BILDplus!")


class TestValidators:
    def test_limit(self):
        assert dom.validate_limit(1) == 1
        assert dom.validate_limit(150) == 150
        with pytest.raises(ValueError):
            dom.validate_limit(0)
        with pytest.raises(ValueError):
            dom.validate_limit(151)

    def test_section(self):
        assert dom.validate_section("Sport") == "sport"
        assert dom.validate_section(" UNTERHALTUNG ") == "unterhaltung"
        with pytest.raises(ValueError):
            dom.validate_section("wirtschaft")  # 404 on the live site


class TestSearchAndDedupe:
    def test_search_items(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        found = dom.search_items(parsed["items"], "Bayern")
        assert len(found) == 8
        assert dom.search_items(parsed["items"], "bayern") == found
        with pytest.raises(ValueError):
            dom.search_items(parsed["items"], "   ")

    def test_dedupe_sort(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        doubled = parsed["items"] + parsed["items"][:5]
        out = dom.dedupe_sort(doubled)
        assert len(out) == 99
        pubs = [i["published"] for i in out]
        assert pubs == sorted(pubs, reverse=True)


class TestFeedGuards:
    def test_parse_rss_rejects_garbage(self):
        with pytest.raises(ValueError):
            dom.parse_rss("<html><body>not rss</body></html>")

    def test_fetch_article_refuses_feed_urls(self):
        with pytest.raises(http_mod.BildError):
            http_mod.fetch_article("https://www.bild.de/feed/home.xml")
        with pytest.raises(http_mod.BildError):
            http_mod.fetch_article("https://www.bild.de/")

    def test_fetch_article_refuses_other_hosts(self):
        with pytest.raises(http_mod.BildError):
            http_mod.fetch_article(
                "https://www.spiegel.de/politik/deutschland/afd-100.html"
            )
        with pytest.raises(http_mod.BildError):
            http_mod.fetch_article(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )

    def test_fetch_feed_refuses_non_feed_urls(self):
        with pytest.raises(http_mod.BildError):
            http_mod.fetch_feed("https://www.bild.de/politik/")
        with pytest.raises(http_mod.BildError):
            http_mod.fetch_feed(
                "https://www.bild.de/leben-wissen/"
                "neue-bka-zahlen-vorgestellt-6b032922816dfbaedcce8a5c"
            )


class TestServerEnvelope:
    def test_tools_return_json_envelope(self):
        # Offline: the tools hit the network, so only the error path
        # is exercised here — but the envelope shape is the same.
        from bild_mcp import server as srv

        out = json.loads(srv.bild_section_news("wirtschaft"))
        assert "error" in out
        assert out["source"] == "www.bild.de"
        assert "fetched_at" in out
