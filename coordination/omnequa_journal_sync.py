#!/usr/bin/env python3
"""Check that the blog and the Omnequa journal are one record. Local files only; no network.

The canonical source is microcredit-vision/posts/*.md. The vision build renders
omnequa/feed.json, which omnequa.org reads from main on every page view, and the four
copies the site bundles. This check compares the committed files without running the
vision build, so it works from any checkout and from the testbed's workspace check:

  - every post in posts/ is in omnequa/feed.json exactly once, with the same title and
    publication time, and the feed names nothing else;
  - the feed's "updated" time is the latest publication or revision time;
  - omnequa/content/blog-feed.json is byte-identical to omnequa/feed.json;
  - omnequa/dist/journal-feed.json is the compact form of omnequa/feed.json;
  - omnequa/content/blog-atom.xml and omnequa/dist/feed.xml are byte-identical to feed.xml;
  - feed.xml lists the same posts.

Process and lanes: coordination/OMNEQUA_JOURNAL_SYNC.md.
"""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

CANONICAL = "omnequa/feed.json"
ATOM = "feed.xml"
JSON_COPIES = {"omnequa/content/blog-feed.json": "identical", "omnequa/dist/journal-feed.json": "compact"}
ATOM_COPIES = ("omnequa/content/blog-atom.xml", "omnequa/dist/feed.xml")
META_RE = re.compile(r"\A<!--\n(.*?)-->", re.S)
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def iso(stamp):
    """'2026-11-01 16:20 UTC' as the feed writes it: '2026-11-01T16:20:00Z'."""
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) UTC", stamp.strip())
    if not match:
        raise ValueError(f"unrecognised time: {stamp!r}")
    return f"{match[1]}T{match[2]}:00Z"


def read_posts(vision):
    """slug -> {title, date, updated} from each post's leading metadata comment."""
    posts = {}
    for path in sorted((vision / "posts").glob("*.md")):
        match = META_RE.match(path.read_text(encoding="utf-8"))
        if not match:
            raise ValueError(f"{path.name}: no leading metadata comment")
        meta = dict(re.findall(r"^(\w+):[ \t]*(.*?)[ \t]*$", match[1], re.M))
        for key in ("title", "date"):
            if not meta.get(key):
                raise ValueError(f"{path.name}: missing {key}")
        posts[path.stem] = {"title": meta["title"], "date": iso(meta["date"]),
                            "updated": iso(meta["revised"]) if meta.get("revised") else iso(meta["date"])}
    return posts


def check(vision):
    """Return a list of findings; empty means the blog and the journal agree."""
    vision = Path(vision)
    errors = []
    required = [CANONICAL, ATOM, *JSON_COPIES, *ATOM_COPIES]
    missing = [name for name in required if not (vision / name).is_file()]
    if missing:
        return [f"Missing journal file: {name}" for name in missing]
    posts = read_posts(vision)
    canonical_text = (vision / CANONICAL).read_text(encoding="utf-8")
    feed = json.loads(canonical_text)
    if feed.get("version") != 1 or not isinstance(feed.get("posts"), list):
        return [f"{CANONICAL}: not a version 1 journal feed"]
    entries = feed["posts"]
    slugs = [entry.get("slug") for entry in entries]
    ids = [entry.get("id") for entry in entries]
    if len(set(slugs)) != len(slugs):
        errors.append(f"{CANONICAL}: a slug appears more than once")
    if len(set(ids)) != len(ids):
        errors.append(f"{CANONICAL}: an id appears more than once")
    for slug in sorted(set(posts) - set(slugs)):
        errors.append(f"Post missing from the journal: {slug}")
    for slug in sorted(set(slugs) - set(posts)):
        errors.append(f"Journal entry without a post: {slug}")
    for entry in entries:
        post = posts.get(entry.get("slug"))
        if not post:
            continue
        if entry.get("title") != post["title"]:
            errors.append(f"Journal title differs: {entry['slug']}")
        if entry.get("date") != post["date"]:
            errors.append(f"Journal publication time differs: {entry['slug']}")
    if posts and feed.get("updated") != max(post["updated"] for post in posts.values()):
        errors.append(f"{CANONICAL}: updated time is not the latest publication or revision")
    for name, form in JSON_COPIES.items():
        expected = canonical_text if form == "identical" else json.dumps(feed, ensure_ascii=False)
        if (vision / name).read_text(encoding="utf-8") != expected:
            errors.append(f"Journal copy out of step with {CANONICAL}: {name}")
    atom_text = (vision / ATOM).read_text(encoding="utf-8")
    for name in ATOM_COPIES:
        if (vision / name).read_text(encoding="utf-8") != atom_text:
            errors.append(f"Atom copy out of step with {ATOM}: {name}")
    try:
        root = ET.fromstring(atom_text)
    except ET.ParseError:
        errors.append(f"{ATOM}: not well-formed XML")
    else:
        atom_slugs = set()
        for entry in root.findall("a:entry", ATOM_NS):
            link = entry.find("a:link", ATOM_NS)
            href = link.get("href", "") if link is not None else ""
            atom_slugs.add(href.rsplit("/", 1)[-1].removesuffix(".md"))
        if atom_slugs != set(posts):
            errors.append(f"{ATOM}: entries do not match posts/")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vision", type=Path, default=Path(__file__).resolve().parents[2] / "microcredit-vision",
                        help="the microcredit-vision checkout (default: beside this testbed)")
    parser.add_argument("--json", action="store_true", help="one machine-readable summary")
    args = parser.parse_args(argv)
    if not (args.vision / "posts").is_dir():
        parser.exit(1, f"Journal check failed: no posts/ directory under {args.vision}\n")
    try:
        errors = check(args.vision)
        count = len(read_posts(args.vision))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Journal check failed: {exc}\n")
    if args.json:
        print(json.dumps({"ok": not errors, "posts": count, "findings": errors}, indent=2))
    else:
        for error in errors:
            print("FAIL:", error)
        if not errors:
            print(f"PASS: {count} posts; omnequa/feed.json, the site's four copies and feed.xml agree")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
