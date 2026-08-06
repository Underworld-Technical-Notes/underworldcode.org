#!/usr/bin/env python3
"""Generate the landing page as a reverse-chronological feed of notes.

MyST has no listing or view feature -- ``jupyter-book/mystmd#840`` is still
open -- so a blog-style index has to be produced rather than declared. Doing it
from ``metadata.yml`` means the front page cannot drift from the articles: add a
note, rebuild, and it appears with the right date, authors, DOI and downloads.

The markup is emitted as raw HTML with its own class names. MyST passes that
through untouched, which avoids styling around the theme's utility classes and
keeps the page under our control rather than the template's.

Usage:
    python3 scripts/build_index.py
"""

import datetime
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"


def read_yaml(path):
    """Parse the fixed-shape metadata.yml without a YAML dependency."""
    data, current_list, current_obj = {}, None, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            key, _, value = line.partition(":")
            value = value.strip()
            if value == "":
                data[key] = []
                current_list, current_obj = data[key], None
            else:
                data[key] = scalar(value)
                current_list, current_obj = None, None
        elif line.startswith("- ") and current_list is not None:
            item = line[2:]
            if ":" in item:
                key, _, value = item.partition(":")
                current_obj = {key.strip(): scalar(value.strip())}
                current_list.append(current_obj)
            else:
                current_list.append(scalar(item))
                current_obj = None
        elif current_obj is not None and ":" in line:
            key, _, value = line.partition(":")
            current_obj[key.strip()] = scalar(value.strip())
    return data


def scalar(text):
    if text in ("null", "~", ""):
        return None
    if text.startswith('"') and text.endswith('"') and len(text) > 1:
        return text[1:-1].replace('\\"', '"')
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def description_of(path, slug):
    """The article's own summary, from its front matter."""
    text = (path / ("%s.md" % slug)).read_text(encoding="utf-8")
    match = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        return ""
    block = match.group(1)
    field = re.search(r"^description:\s*(?:>-\s*\n((?:\s{2,}.*\n?)+)|(.+))$", block, re.M)
    if not field:
        return ""
    value = field.group(1) or field.group(2) or ""
    return " ".join(value.replace('"', "").split())


def format_date(iso):
    if not iso:
        return ""
    try:
        date = datetime.date.fromisoformat(str(iso))
    except ValueError:
        return str(iso)
    return "%d %s %d" % (date.day, date.strftime("%B"), date.year)


def entry_html(meta, description, has_pdf):
    slug = meta["slug"]
    authors = [a.get("name", "") for a in (meta.get("authors") or [])]
    if len(authors) > 2:
        byline = "%s and %d others" % (authors[0], len(authors) - 1)
    else:
        byline = " and ".join(authors)

    links = ['<a class="uwtn-read" href="/%s/">Read</a>' % slug]
    if has_pdf:
        links.append('<a href="/%s/%s.pdf">PDF</a>' % (slug, slug))
    doi = meta.get("doi")
    if doi:
        links.append('<a href="https://doi.org/%s"><span class="uwtn-doi-label">doi</span>%s</a>'
                     % (doi, html.escape(doi)))

    tags = "".join('<span class="uwtn-tag">%s</span>' % html.escape(str(t))
                   for t in (meta.get("tags") or []) if t)

    # MyST keeps div, span and a with their classes and drops everything else's
    # -- <article>, <p class>, <time>, role and aria-* are all stripped. The
    # title stays a real heading (MyST re-renders it as its own node, losing the
    # class but keeping the semantics) and is styled by descendant selector.
    # No blank lines: a blank line ends a raw HTML block in markdown, which
    # silently hands the rest of the entry back to the markdown parser.
    return "".join([
        '<div class="uwtn-entry">',
        '<div class="uwtn-entry-meta">',
        '<span class="uwtn-id">%s</span>' % html.escape(str(meta.get("id") or "")),
        '<span class="uwtn-date">%s</span>' % format_date(meta.get("publication_date")),
        '</div>',
        '<h2><a href="/%s/">%s</a></h2>' % (
            slug, html.escape(str(meta.get("title") or slug))),
        '<div class="uwtn-entry-byline">%s</div>' % html.escape(byline),
        '<div class="uwtn-entry-summary">%s</div>' % html.escape(description),
        '<div class="uwtn-entry-links">%s</div>' % " ".join(links),
        ('<div class="uwtn-tags">%s</div>' % tags) if tags else "",
        '</div>',
    ])


def main():
    metas = []
    for meta_path in sorted(ARTICLES.glob("*/metadata.yml")):
        meta = read_yaml(meta_path)
        if meta.get("status") == "draft":
            continue          # unpublished notes do not appear on the front page
        directory = meta_path.parent
        metas.append((meta,
                      description_of(directory, meta["slug"]),
                      (directory / ("%s.pdf" % meta["slug"])).exists()))

    metas.sort(key=lambda m: (m[0].get("publication_date") or ""), reverse=True)
    if not metas:
        sys.exit("no articles found -- run `pixi run migrate` first")

    with_doi = sum(1 for m, _d, _p in metas if m.get("doi"))
    entries = "\n".join(entry_html(m, d, p) for m, d, p in metas)

    page = """---
title: Underworld Technical Notes
site:
  hide_outline: true
  hide_title_block: true
---

<div class="uwtn-masthead"><div class="uwtn-kicker">Underworld</div><div class="uwtn-wordmark">Technical Notes</div><div class="uwtn-standfirst">Methods, implementation notes, benchmarks and worked examples from the <a href="https://github.com/underworldcode/underworld3">Underworld</a> geodynamics code. Each note is a living web article and, where it carries a DOI, a fixed archival PDF.</div></div>

<div class="uwtn-feed">
%s
</div>

<div class="uwtn-colophon">%d notes, %d with a registered DOI. The DOI identifies the archival publication; this site is the current rendition and may carry corrections, updated links and discussion.</div>
""" % (entries, len(metas), with_doi)

    (ROOT / "index.md").write_text(page, encoding="utf-8")
    print("index.md: %d note(s), %d with a DOI, %d with a PDF"
          % (len(metas), with_doi, sum(1 for _m, _d, p in metas if p)))
    for meta, _description, _pdf in metas:
        print("  %-12s %-11s %s" % (meta.get("id"), meta.get("publication_date"),
                                    str(meta.get("title"))[:52]))


if __name__ == "__main__":
    main()
