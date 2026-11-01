import json
from pathlib import Path
import tempfile
import unittest
from xml.sax.saxutils import escape

from coordination.omnequa_journal_sync import check, main, read_posts

REPO = "https://github.com/scottonchain/microcredit-vision"


def stamp(when):
    """'2026-11-01 16:20 UTC' as the feed writes it."""
    return when.replace(" UTC", ":00Z").replace(" ", "T", 1)


def write_vision(root, posts):
    """A minimal vision checkout whose journal files agree: posts is [(slug, title, date, revised)]."""
    root = Path(root)
    for name in ("posts", "omnequa/content", "omnequa/dist"):
        (root / name).mkdir(parents=True, exist_ok=True)
    entries = []
    for slug, title, date, revised in posts:
        meta = f"<!--\ntitle: {title}\ndate: {date}\nauthor: Claude Code\nimage: images/{slug}.svg\nsummary: One line.\ntags: microcredit\n"
        if revised:
            meta += f"revised: {revised}\n"
        (root / "posts" / f"{slug}.md").write_text(meta + "-->\n\nBody.\n", encoding="utf-8")
        url = f"{REPO}/blob/main/posts/{slug}.md"
        entries.append({"id": url, "slug": slug, "title": title, "date": stamp(date), "author": "Claude Code",
                        "summary": "One line.", "tags": ["microcredit"], "url": url, "image": "",
                        "content_html": "<p>Body.</p>"})
    updated = stamp(max(revised or date for _, _, date, revised in posts))
    feed = {"version": 1, "updated": updated, "posts": entries}
    canonical = json.dumps(feed, ensure_ascii=False, indent=2) + "\n"
    (root / "omnequa/feed.json").write_text(canonical, encoding="utf-8")
    (root / "omnequa/content/blog-feed.json").write_text(canonical, encoding="utf-8")
    (root / "omnequa/dist/journal-feed.json").write_text(json.dumps(feed, ensure_ascii=False), encoding="utf-8")
    atom = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">',
            f"<updated>{updated}</updated>"]
    for entry in entries:
        atom += ["<entry>", f"<title>{escape(entry['title'])}</title>", f'<link href="{entry["url"]}"/>',
                 f"<id>{entry['url']}</id>", "</entry>"]
    atom_text = "\n".join(atom + ["</feed>", ""])
    (root / "feed.xml").write_text(atom_text, encoding="utf-8")
    for name in ("omnequa/content/blog-atom.xml", "omnequa/dist/feed.xml"):
        (root / name).write_text(atom_text, encoding="utf-8")
    return root


POSTS = [("2026-10-06-first", "A first post", "2026-10-06 10:00 UTC", None),
         ("2026-11-01-second", "A second post", "2026-11-01 16:20 UTC", "2026-11-01 18:00 UTC")]


class JournalSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vision = write_vision(self.tmp.name, POSTS)

    def feed(self):
        return json.loads((self.vision / "omnequa/feed.json").read_text())

    def write_feed(self, feed, *, copies=True):
        canonical = json.dumps(feed, ensure_ascii=False, indent=2) + "\n"
        (self.vision / "omnequa/feed.json").write_text(canonical)
        if copies:
            (self.vision / "omnequa/content/blog-feed.json").write_text(canonical)
            (self.vision / "omnequa/dist/journal-feed.json").write_text(json.dumps(feed, ensure_ascii=False))

    def test_agreeing_checkout_passes(self):
        self.assertEqual(check(self.vision), [])
        posts = read_posts(self.vision)
        self.assertEqual(posts["2026-11-01-second"]["updated"], "2026-11-01T18:00:00Z")
        self.assertEqual(posts["2026-10-06-first"]["updated"], "2026-10-06T10:00:00Z")

    def test_new_post_without_a_rebuilt_journal_is_reported(self):
        (self.vision / "posts/2026-11-02-third.md").write_text(
            "<!--\ntitle: A third post\ndate: 2026-11-02 08:07 UTC\n-->\n\nBody.\n")
        findings = check(self.vision)
        self.assertIn("Post missing from the journal: 2026-11-02-third", findings)
        self.assertIn("feed.xml: entries do not match posts/", findings)

    def test_journal_entry_without_a_post_is_reported(self):
        (self.vision / "posts/2026-10-06-first.md").unlink()
        self.assertIn("Journal entry without a post: 2026-10-06-first", check(self.vision))

    def test_title_and_time_differences_are_reported(self):
        feed = self.feed()
        feed["posts"][0]["title"] = "Another title"
        feed["posts"][1]["date"] = "2026-11-01T16:21:00Z"
        self.write_feed(feed)
        findings = check(self.vision)
        self.assertIn("Journal title differs: 2026-10-06-first", findings)
        self.assertIn("Journal publication time differs: 2026-11-01-second", findings)

    def test_updated_must_be_the_latest_revision(self):
        feed = self.feed()
        feed["updated"] = "2026-11-01T16:20:00Z"
        self.write_feed(feed)
        self.assertEqual(check(self.vision), ["omnequa/feed.json: updated time is not the latest publication or revision"])

    def test_hand_copied_snapshot_drift_is_reported(self):
        feed = self.feed()
        feed["posts"][1]["summary"] = "A regenerated summary."
        self.write_feed(feed, copies=False)
        self.assertEqual(check(self.vision), [
            "Journal copy out of step with omnequa/feed.json: omnequa/content/blog-feed.json",
            "Journal copy out of step with omnequa/feed.json: omnequa/dist/journal-feed.json"])

    def test_bundled_edition_must_be_the_compact_form(self):
        (self.vision / "omnequa/dist/journal-feed.json").write_text(
            (self.vision / "omnequa/feed.json").read_text())
        self.assertEqual(check(self.vision),
                         ["Journal copy out of step with omnequa/feed.json: omnequa/dist/journal-feed.json"])

    def test_atom_copies_are_checked(self):
        (self.vision / "omnequa/dist/feed.xml").write_text("<feed/>")
        self.assertEqual(check(self.vision), ["Atom copy out of step with feed.xml: omnequa/dist/feed.xml"])

    def test_duplicate_entries_are_reported(self):
        feed = self.feed()
        feed["posts"].append(dict(feed["posts"][0]))
        self.write_feed(feed)
        findings = check(self.vision)
        self.assertIn("omnequa/feed.json: a slug appears more than once", findings)
        self.assertIn("omnequa/feed.json: an id appears more than once", findings)

    def test_missing_files_are_named_first(self):
        (self.vision / "omnequa/content/blog-atom.xml").unlink()
        self.assertEqual(check(self.vision), ["Missing journal file: omnequa/content/blog-atom.xml"])

    def test_post_without_metadata_is_an_error(self):
        (self.vision / "posts/2026-11-02-bare.md").write_text("No metadata.\n")
        with self.assertRaisesRegex(ValueError, "no leading metadata comment"):
            check(self.vision)

    def test_command_line_reports_pass_and_fail(self):
        self.assertEqual(main(["--vision", str(self.vision)]), 0)
        (self.vision / "omnequa/dist/feed.xml").write_text("<feed/>")
        self.assertEqual(main(["--vision", str(self.vision), "--json"]), 1)
        with self.assertRaises(SystemExit):
            main(["--vision", self.tmp.name + "/nowhere"])


if __name__ == "__main__":
    unittest.main()
