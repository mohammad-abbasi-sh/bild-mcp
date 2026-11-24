"""Live tests — hit the real www.bild.de RSS feeds and article pages.
Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set BILD_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from bild_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("BILD_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="BILD_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_headlines_live(self):
        out = json.loads(srv.bild_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["description"] for i in out["items"]))
        print(f"\nLIVE headlines: {out['count']} items, first: {out['items'][0]['title']}")

    def test_section_live(self):
        out = json.loads(srv.bild_section_news("sport", limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["section"], "sport")
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["link"].startswith("https://www.bild.de/") for i in out["items"]))
        print(f"\nLIVE sport: {out['total_results']} items")

    def test_search_live(self):
        out = json.loads(srv.bild_search_news("Bayern", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(
            "bayern" in (i["title"] + i["description"]).casefold()
            for i in out["items"]
        ))
        print(f"\nLIVE search 'Bayern': {out['total_results']} hits")

    def test_videos_live(self):
        out = json.loads(srv.bild_videos(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["has_video"] for i in out["items"]))
        print(f"\nLIVE videos: {out['total_results']} items")

    def test_premium_live(self):
        out = json.loads(srv.bild_premium_news(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["premium"] for i in out["items"]))
        print(f"\nLIVE premium: {out['total_results']} items")

    def test_get_article_live(self):
        # An article from the current feed: a free article returns a
        # long body, a BILDplus one returns paywalled=true with only
        # the teaser. Try the first few items until one parses.
        feed = json.loads(srv.bild_headlines(limit=10))
        self.assertNotIn("error", feed)
        self.assertGreater(len(feed["items"]), 0)
        out = None
        tried = []
        for item in feed["items"][:5]:
            tried.append(item["link"])
            out = json.loads(srv.bild_get_article(item["link"]))
            if "error" not in out:
                break
        self.assertNotIn("error", out, f"no article parsed from {tried}")
        if out["paywalled"]:
            self.assertTrue(out["teaser_only"])
            self.assertLess(out["word_count"], 100)
        else:
            self.assertGreater(out["word_count"], 50)
        print(f"\nLIVE article: {out['word_count']} words, paywalled={out['paywalled']}, {out['title'][:60]}")

    def test_health_live(self):
        out = json.loads(srv.bild_health())
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)


if __name__ == "__main__":
    unittest.main()
