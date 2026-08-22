#!/usr/bin/env python3
"""Give every archival PDF a page of its own to be read on.

A DOI click lands a reader on the repository's item page, which is a file
browser: it shows a PDF and a zip and asks which one you wanted. The PDF is the
publication, so the site serves it embedded on a page that says what it is and
offers the two things a reader actually asks for next -- the file itself, and the
markdown the article is written from.

Written at ``/<slug>/read/``, so it sits under the article's own URL and travels
with it. Every link on it is RELATIVE (``../<slug>.pdf``, ``../``): the preview
site serves the whole thing from a hashed subdirectory, and an absolute path
would walk out of it to the domain root. Standalone HTML rather than a MyST page: it carries an embedded PDF and
nothing else, it must not enter the toc, and generating it here keeps it out of
the theme's client-side router (where a hydrated document would reconcile the
embed away).

Run after ``stage_downloads.py``, which is what puts the PDF and the markdown
where this page links to.

Usage:
    python3 scripts/build_reader_pages.py [--build _build/html]
"""

import argparse
import html
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"

sys.path.insert(0, str(ROOT / "scripts"))

# The site's own tokens, inlined. The stylesheet is injected into MyST pages by
# `inject_style.py` rather than published as a file, so there is nothing to link
# to; keeping a small copy here is the price of a standalone page, and it is only
# the half-dozen values that make it look like the rest of the site.
STYLE = """
:root {
  --uwtn-ink: #16202b; --uwtn-muted: #5d6b7a; --uwtn-rule: #dfe4ea;
  --uwtn-accent: #1a4f80; --uwtn-paper: #ffffff;
  --uwtn-sans: "Helvetica Neue", Helvetica, Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --uwtn-ink: #e6e9ec; --uwtn-muted: #9aa7b4; --uwtn-rule: #2b3541;
    --uwtn-accent: #7cb3e0; --uwtn-paper: #131a21;
  }
}
* { box-sizing: border-box; }
/* height, not just min-height: a percentage height inside a flex column needs
   a DEFINITE container, and without it the viewer below fell back to its
   min-height (512px) however tall the window was -- a letterbox showing a
   few lines of a page scaled to the full window width. */
body { margin: 0; background: var(--uwtn-paper); color: var(--uwtn-ink);
       font-family: var(--uwtn-sans); font-size: 16px; line-height: 1.5;
       display: flex; flex-direction: column; height: 100vh; min-height: 100vh; }
header { border-bottom: 1px solid var(--uwtn-rule); padding: 1.1rem 1.4rem; }
.wrap { max-width: 68rem; margin: 0 auto; width: 100%; }
.kicker { font-size: .78rem; letter-spacing: .09em; text-transform: uppercase;
          color: var(--uwtn-muted); }
h1 { font-size: 1.25rem; margin: .25rem 0 .35rem; font-weight: 600; }
.meta { color: var(--uwtn-muted); font-size: .9rem; }
.meta a { color: inherit; }
.actions { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .9rem; }
.actions a { display: inline-block; text-decoration: none; font-size: .88rem;
             padding: .4rem .8rem; border-radius: 5px;
             border: 1px solid var(--uwtn-rule); color: var(--uwtn-ink); }
.actions a:hover { border-color: var(--uwtn-accent); color: var(--uwtn-accent); }
.actions a.primary { background: var(--uwtn-accent); border-color: var(--uwtn-accent);
                     color: #fff; }
/* min-height: 0 lets a flex item shrink below its content; without it the
   viewer cannot give the window's height back and the page scrolls instead. */
.reader { flex: 1 1 auto; min-height: 0; display: flex; }
.reader object, .reader iframe { flex: 1 1 auto; display: block; width: 100%;
                                 height: 100%; min-height: 20rem; border: 0; }
.fallback { padding: 2rem 1.4rem; color: var(--uwtn-muted); }
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s — Underworld Geodynamics</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="../">
<style>%(style)s</style>
</head>
<body>
<header><div class="wrap">
  <div class="kicker">%(kicker)s</div>
  <h1>%(title)s</h1>
  <div class="meta">%(meta)s</div>
  <div class="actions">
    <a class="primary" href="../%(slug)s.pdf" download>Download PDF</a>
    <a href="../%(slug)s.md" download>Markdown source</a>
    <a href="../">Read on the site</a>
  </div>
</div></header>
<div class="reader">
  <object data="../%(slug)s.pdf#view=Fit" type="application/pdf">
    <div class="fallback">
      <p>This browser will not display a PDF here — most phones will not.</p>
      <p><a href="../%(slug)s.pdf">Open the PDF</a> or
         <a href="../">read the article on the site</a>.</p>
    </div>
  </object>
</div>
</body>
</html>
"""


def meta_line(meta):
    """Authors, date and DOI, as one line of plain text with the DOI linked."""
    authors = [str(a.get("name") or "") for a in (meta.get("authors") or [])]
    if len(authors) > 2:
        byline = "%s and %d others" % (authors[0], len(authors) - 1)
    else:
        byline = " and ".join(a for a in authors if a)
    bits = [html.escape(byline)] if byline else []
    date = str(meta.get("publication_date") or "")
    if date:
        bits.append(html.escape(date))
    doi = meta.get("archive_doi") or meta.get("legacy_doi")
    if doi:
        bits.append('<a href="https://doi.org/%s">doi:%s</a>'
                    % (html.escape(str(doi)), html.escape(str(doi))))
    return " · ".join(bits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    args = parser.parse_args()

    import build_index

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s -- run `myst build --html` first" % build)

    written = 0
    for path in sorted(ARTICLES.glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        slug = str(meta.get("slug") or path.parent.name)
        target = build / slug
        # Only where the reader has something to read: the PDF must be staged.
        if not (target / ("%s.pdf" % slug)).exists():
            continue
        kind = str(meta.get("id") or meta.get("article_type") or "").strip()
        page = PAGE % {
            "slug": html.escape(slug),
            "title": html.escape(str(meta.get("title") or slug)),
            "kicker": html.escape(kind or "Underworld Geodynamics"),
            "meta": meta_line(meta),
            "style": STYLE,
        }
        reader = target / "read"
        reader.mkdir(exist_ok=True)
        (reader / "index.html").write_text(page, encoding="utf-8")
        written += 1

    print("%d reader page(s) written at /<slug>/read/" % written)


if __name__ == "__main__":
    main()
