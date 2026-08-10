#!/usr/bin/env python3
"""Serve a feed, because the site being replaced served one.

Ghost published `/rss/` -- it is what Rogue Scholar read to mint the fifty
registered DOIs, so it certainly had subscribers. The cutover would otherwise
have handed every one of them a 404 with no notice and no way to find out
where the notes went. That is the sort of loss that is invisible from the
inside: nothing fails, no test goes red, people just stop reading.

    /feed.xml    Atom 1.0    the modern one, and what the pages advertise
    /rss.xml     RSS 2.0     for readers that still want it
    /rss/        a page that points at both, where Ghost's feed used to be

MyST has no feed generator (jupyter-book/mystmd#840 is open), so this is hand
written. It is XML assembled from strings, which is usually a poor idea; here
the alternative is a dependency in CI to emit sixty entries of a fixed shape,
and every value that comes near the output goes through escape() first.

**Summaries, not full text.** The plan asked for full content. The article body
IS server-rendered and could be lifted out of the built HTML -- but that means
scraping the output of a React theme, rewriting every relative image and link
as it goes, and dropping the discussion block and banner on the way. It would
work today and break quietly on a MyST upgrade, and a feed that silently starts
emitting half an article is worse than one that always emitted a paragraph.
Each entry carries its summary, its authors, its subjects, its licence and its
DOI, and links to the article.

Run after `myst build --html`, and after the pages exist.

Usage:
    python3 scripts/build_feed.py [--build _build/html] [--host www.underworldcode.org]
"""

import argparse
import datetime
import os
import pathlib
import re
import sys
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
sys.path.insert(0, str(ROOT / "scripts"))

TITLE = "Underworld Technical Notes"
SUBTITLE = ("Methods, worked examples, benchmarks and design rationale for the "
            "Underworld geodynamics code.")


def first_paragraph(directory, slug):
    """A fallback summary for the older notes, which have no `description`.

    The first paragraph of prose -- not a heading, a directive, a figure, an
    equation, the banner div or a bold stand-first.
    """
    source = directory / ("%s.md" % slug)
    if not source.exists():
        return ""
    body = re.sub(r"^---\n.*?\n---\n", "", source.read_text(encoding="utf-8"), flags=re.S)
    for block in body.split("\n\n"):
        block = block.strip()
        if not block or block.startswith(("#", "```", ":::", "<", "$$", "|", "-", "*")):
            continue
        if block.startswith("**") and block.endswith("**"):
            continue                      # a stand-first, not the article
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", block)   # links to text
        text = re.sub(r"[*_`]", "", text)
        text = " ".join(text.split())
        if len(text) > 40:
            return text[:400] + ("…" if len(text) > 400 else "")
    return ""


def entries(host):
    """Every published article, newest first."""
    import build_index
    build_index.TYPES.update(build_index.article_types())
    # The same rule as the site, not a second copy of it. This had its own
    # `status == "draft"` test and so put a note that the site was correctly
    # withholding into every subscriber's reader -- the one place a mistake
    # cannot be taken back.
    preview = bool(os.environ.get("UWTN_PREVIEW"))
    found = []
    for path in sorted(ARTICLES.glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        if not preview and meta.get("status") in ("draft", "review", "withdrawn"):
            continue
        slug = meta["slug"]
        summary = (build_index.description_of(path.parent, slug)
                   or first_paragraph(path.parent, slug))
        found.append({
            "title": str(meta.get("title") or slug),
            "url": "https://%s/%s/" % (host, slug),
            "date": str(meta.get("publication_date") or ""),
            "authors": [str(a.get("name") or "") for a in (meta.get("authors") or [])],
            "tags": [str(t) for t in (meta.get("ghost_tags") or [])],
            "summary": summary,
            "licence": str(meta.get("license") or "CC-BY-4.0"),
            # The archival DOI where there is one -- it is the identifier to
            # circulate, and a reader who wants the fixed copy should not have
            # to open the page to find it.
            "doi": meta.get("archive_doi") or meta.get("legacy_doi") or "",
        })
    found.sort(key=lambda e: (e["date"], e["title"]), reverse=True)
    return found


def rfc3339(date):
    """A date-only publication date, as an instant. Feeds require a time."""
    try:
        return "%sT00:00:00Z" % datetime.date.fromisoformat(date).isoformat()
    except ValueError:
        return "1970-01-01T00:00:00Z"


def rfc822(date):
    try:
        day = datetime.date.fromisoformat(date)
    except ValueError:
        return "Thu, 01 Jan 1970 00:00:00 GMT"
    return day.strftime("%a, %d %b %Y 00:00:00 GMT")


def atom(found, host, stamp):
    site = "https://%s" % host
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<feed xmlns="http://www.w3.org/2005/Atom">',
           "  <title>%s</title>" % escape(TITLE),
           "  <subtitle>%s</subtitle>" % escape(SUBTITLE),
           '  <link href="%s/"/>' % site,
           '  <link rel="self" type="application/atom+xml" href="%s/feed.xml"/>' % site,
           "  <id>%s/</id>" % site,
           "  <updated>%s</updated>" % stamp,
           "  <generator>scripts/build_feed.py</generator>"]
    for entry in found:
        out.append("  <entry>")
        out.append("    <title>%s</title>" % escape(entry["title"]))
        out.append('    <link href="%s"/>' % escape(entry["url"]))
        # The DOI where there is one: an identifier that outlives the URL is a
        # better entry id than the URL, which is the whole point of having one.
        out.append("    <id>%s</id>"
                   % escape("https://doi.org/%s" % entry["doi"] if entry["doi"]
                            else entry["url"]))
        out.append("    <published>%s</published>" % rfc3339(entry["date"]))
        out.append("    <updated>%s</updated>" % rfc3339(entry["date"]))
        for name in entry["authors"]:
            out.append("    <author><name>%s</name></author>" % escape(name))
        for tag in entry["tags"]:
            out.append('    <category term="%s"/>' % escape(tag))
        if entry["summary"]:
            out.append('    <summary type="text">%s</summary>' % escape(entry["summary"]))
        out.append("    <rights>%s</rights>" % escape(entry["licence"]))
        out.append("  </entry>")
    out.append("</feed>")
    return "\n".join(out) + "\n"


def rss(found, host, stamp):
    site = "https://%s" % host
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
           "  <channel>",
           "    <title>%s</title>" % escape(TITLE),
           "    <description>%s</description>" % escape(SUBTITLE),
           "    <link>%s/</link>" % site,
           '    <atom:link href="%s/rss.xml" rel="self" type="application/rss+xml"/>' % site,
           "    <lastBuildDate>%s</lastBuildDate>"
           % datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
                     .strftime("%a, %d %b %Y %H:%M:%S GMT")]
    for entry in found:
        out.append("    <item>")
        out.append("      <title>%s</title>" % escape(entry["title"]))
        out.append("      <link>%s</link>" % escape(entry["url"]))
        out.append('      <guid isPermaLink="false">%s</guid>'
                   % escape(entry["doi"] or entry["url"]))
        out.append("      <pubDate>%s</pubDate>" % rfc822(entry["date"]))
        for name in entry["authors"]:
            out.append("      <dc:creator xmlns:dc=\"http://purl.org/dc/elements/1.1/\">"
                       "%s</dc:creator>" % escape(name))
        for tag in entry["tags"]:
            out.append("      <category>%s</category>" % escape(tag))
        if entry["summary"]:
            out.append("      <description>%s</description>" % escape(entry["summary"]))
        out.append("    </item>")
    out.extend(["  </channel>", "</rss>"])
    return "\n".join(out) + "\n"


def ghost_feed_page(host):
    """Where Ghost's feed was. Not a 404, and not a lie about being one."""
    site = "https://%s" % host
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Feeds — %s</title>
<link rel="alternate" type="application/atom+xml" title="%s" href="%s/feed.xml">
<link rel="alternate" type="application/rss+xml" title="%s" href="%s/rss.xml">
<meta name="robots" content="noindex">
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:34em;margin:12vh auto;padding:0 1.5em}</style>
</head>
<body>
<h1>Feeds</h1>
<p>This is where the old blog's feed lived. The notes are still here and still
have a feed; it moved when the site did.</p>
<ul>
  <li><a href="%s/feed.xml">Atom</a> — <code>%s/feed.xml</code></li>
  <li><a href="%s/rss.xml">RSS</a> — <code>%s/rss.xml</code></li>
</ul>
<p>Your reader may have picked the new address up already: this page advertises
both. <a href="%s/">Back to the notes</a>.</p>
</body>
</html>
""" % (TITLE, TITLE, site, TITLE, site, site, site, site, site, site)


def advertise(build, host):
    """Autodiscovery in every page's head, which is how readers find a feed.

    A feed nobody can discover is a file on a server. Injected here rather than
    in the theme: the theme is a dependency, and a post-step that adds one line
    survives upgrading it.
    """
    site = "https://%s" % host
    links = ('<link rel="alternate" type="application/atom+xml" title="%s" href="%s/feed.xml">'
             '<link rel="alternate" type="application/rss+xml" title="%s" href="%s/rss.xml">'
             % (TITLE, site, TITLE, site))
    touched = 0
    for page in build.rglob("index.html"):
        html = page.read_text(encoding="utf-8")
        if 'type="application/atom+xml"' in html or "</head>" not in html:
            continue
        page.write_text(html.replace("</head>", links + "</head>", 1), encoding="utf-8")
        touched += 1
    return touched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    # Derived from the CNAME, exactly as deploy.yml derives the base URL, so a
    # staging build cannot emit a feed full of production links -- and so the
    # cutover does not need anyone to remember this file.
    cname = ROOT / "CNAME"
    parser.add_argument("--host",
                        default=(cname.read_text(encoding="utf-8").strip()
                                 if cname.exists()
                                 else "underworld-technical-notes.github.io"))
    args = parser.parse_args()

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s -- run `myst build --html` first" % build)

    found = entries(args.host)
    if not found:
        sys.exit("no articles -- refusing to publish an empty feed")
    missing = [e["title"] for e in found if not e["summary"]]

    stamp = (datetime.datetime.now(datetime.timezone.utc)
             .replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"))
    (build / "feed.xml").write_text(atom(found, args.host, stamp), encoding="utf-8")
    (build / "rss.xml").write_text(rss(found, args.host, stamp), encoding="utf-8")
    (build / "rss").mkdir(exist_ok=True)
    (build / "rss" / "index.html").write_text(ghost_feed_page(args.host), encoding="utf-8")

    touched = advertise(build, args.host)
    print("feed: %d entries -> /feed.xml, /rss.xml, and /rss/ where Ghost's was"
          % len(found))
    print("      advertised in the head of %d page(s)" % touched)
    if missing:
        print("      %d entry/entries have no summary: %s"
              % (len(missing), ", ".join(missing[:3])))


if __name__ == "__main__":
    main()
