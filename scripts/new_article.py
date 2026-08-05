#!/usr/bin/env python3
"""Start a new technical note from the template.

Creates ``articles/<slug>/<slug>.md``, ``metadata.yml`` and ``figures/``, with
the article ID allocated so it cannot collide with an existing note or with one
allocated later during the legacy backfill.

The filename matters: MyST takes a page's URL from it, so ``<slug>.md`` is what
publishes the note at ``/<slug>/``. Do not rename it to ``index.md``.

Usage:
    python3 scripts/new_article.py --slug particle-level-sets \\
        --title "Particle-based level sets" --author louis
"""

import argparse
import datetime
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "article-template"
ARTICLES = ROOT / "articles"


def load_authors():
    """Slug -> {name, orcid, affiliation} from authors.yml."""
    path = ROOT / "authors.yml"
    registry, current = {}, None
    if not path.exists():
        return registry
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        key, _, value = line.strip().partition(":")
        value = value.strip()
        if indent == 2 and not value:
            current = key
            registry[current] = {}
        elif indent == 4 and current:
            registry[current][key] = None if value in ("null", "") else value
    return registry


def next_article_id(year):
    """Allocate an ID that no existing article uses.

    Legacy notes are numbered across the whole Ghost corpus by publication date,
    so a backfill can land in the middle of a year. Allocating above the highest
    number already present in that year keeps a new note clear of anything the
    backfill will produce, and an ID that has been published never moves.
    """
    used = set()
    for meta in ARTICLES.glob("*/metadata.yml"):
        match = re.search(r"^id:\s*(UWTN\s+(\d{4})-(\d{3}))\s*$",
                          meta.read_text(encoding="utf-8"), re.M)
        if match and match.group(2) == str(year):
            used.add(int(match.group(3)))

    # Also respect the Ghost corpus, so a note started now cannot be given a
    # number that migrating an older post would later want.
    export = ROOT / "inventory" / "ghost-export" / "posts.json"
    if export.exists():
        import json
        posts = json.loads(export.read_text(encoding="utf-8"))["posts"]
        same_year = [p for p in posts
                     if (p.get("published_at") or "")[:4] == str(year)
                     and not re.match(r"^(rce(-\d+)?|sysinfo-[0-9a-f]+)$", p["slug"])]
        used.update(range(1, len(same_year) + 1))

    n = 1
    while n in used:
        n += 1
    return "UWTN %d-%03d" % (year, n)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True, help="URL slug, lowercase and hyphenated")
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", action="append", default=[],
                        help="author key from authors.yml; repeatable")
    parser.add_argument("--date", help="publication date, YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    slug = args.slug.strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        sys.exit("slug must be lowercase alphanumeric and hyphens: %r" % slug)

    dest = ARTICLES / slug
    if dest.exists():
        sys.exit("%s already exists" % dest)

    date = args.date or datetime.date.today().isoformat()
    year = int(date[:4])
    article_id = next_article_id(year)

    registry = load_authors()
    authors = []
    for key in args.author:
        if key not in registry:
            sys.exit("unknown author %r -- add them to authors.yml first "
                     "(known: %s)" % (key, ", ".join(sorted(registry))))
        authors.append(registry[key])
    if not authors:
        authors = [{"name": "Your Name", "orcid": None, "affiliation": None}]

    def front_authors(indent, orcid_key, affil_block):
        lines = []
        for a in authors:
            lines.append("%s- name: %s" % (indent, a["name"]))
            if a.get("orcid"):
                lines.append("%s  %s: %s" % (indent, orcid_key, a["orcid"]))
            elif orcid_key == "orcid" and affil_block == "affiliation":
                lines.append("%s  orcid: null" % indent)
            if a.get("affiliation"):
                if affil_block == "affiliations":
                    lines.append("%s  affiliations:" % indent)
                    lines.append("%s    - %s" % (indent, a["affiliation"]))
                else:
                    lines.append("%s  affiliation: %s" % (indent, a["affiliation"]))
        return "\n".join(lines)

    body = (TEMPLATE / "ARTICLE.md").read_text(encoding="utf-8")
    body = body.replace("title: A short, specific title", "title: %s" % args.title)
    body = body.replace("date: 2026-01-01", "date: %s" % date)
    body = body.replace("output: SLUG.pdf", "output: %s.pdf" % slug)
    body = body.replace("article_id: UWTN 2026-000", "article_id: %s" % article_id)
    body = re.sub(r"authors:\n  - name: Your Name\n    orcid: [^\n]*\n    affiliations:\n      - Your Institution",
                  "authors:\n" + front_authors("  ", "orcid", "affiliations"), body)

    meta = (TEMPLATE / "metadata.yml").read_text(encoding="utf-8")
    meta = meta.replace("id: UWTN 2026-000", "id: %s" % article_id)
    meta = meta.replace("slug: SLUG", "slug: %s" % slug)
    meta = meta.replace("title: A short, specific title", "title: %s" % args.title)
    meta = meta.replace("canonical_path: /SLUG/", "canonical_path: /%s/" % slug)
    meta = re.sub(r"authors:\n  - name: Your Name\n    orcid: [^\n]*\n    affiliation: [^\n]*",
                  "authors:\n" + front_authors("  ", "orcid", "affiliation"), meta)

    (dest / "figures").mkdir(parents=True)
    (dest / ("%s.md" % slug)).write_text(body, encoding="utf-8")
    (dest / "metadata.yml").write_text(meta, encoding="utf-8")

    print("created %s" % dest.relative_to(ROOT))
    print("  %s.md" % slug)
    print("  metadata.yml   (%s)" % article_id)
    print("  figures/")
    print("\nAdd it to the toc in myst.yml, then:")
    print("  pixi run build && pixi run test")


if __name__ == "__main__":
    main()
