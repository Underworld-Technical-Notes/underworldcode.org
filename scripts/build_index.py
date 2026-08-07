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

# Filled from vocabulary.yml at start-up so entries can show readable labels.
FACET_LABELS = {}


def text(value):
    """Prepare a string for a raw HTML block that MyST will re-process.

    MyST parses these blocks and escapes their text again on output, so
    pre-escaping produces `&amp;amp;` and the reader sees `&amp;`. The text is
    therefore passed through raw.

    Angle brackets are refused rather than escaped: escaping them has the same
    doubling problem, and a title containing markup is a mistake to surface
    rather than to paper over.
    """
    value = str(value)
    if "<" in value or ">" in value:
        raise ValueError("angle brackets cannot be placed in a raw HTML block: %r" % value)
    return value


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


def entry_html(meta, description, has_pdf, banner=None, lead=False):
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
        # Shown, not linked. MyST turns any doi.org href into a citation and
        # appends a References section to the page, so linking the DOI here
        # grew a bibliography of its own entries on the front page and on every
        # topic page. The actionable DOI lives on the article itself.
        links.append('<span class="uwtn-doi"><span class="uwtn-doi-label">doi</span>%s</span>'
                     % text(doi))

    facets = list(meta.get("subjects") or []) + list(meta.get("methods") or [])
    tags = "".join('<a class="uwtn-tag" href="/%s/">%s</a>'
                   % (topic_slug(term), text(FACET_LABELS.get(term, term)))
                   for term in facets)

    # MyST keeps div, span and a with their classes and drops everything else's
    # -- <article>, <p class>, <time>, role and aria-* are all stripped. The
    # title stays a real heading (MyST re-renders it as its own node, losing the
    # class but keeping the semantics) and is styled by descendant selector.
    # No blank lines: a blank line ends a raw HTML block in markdown, which
    # silently hands the rest of the entry back to the markdown parser.
    # A path MyST can resolve from index.md, so it copies and fingerprints the
    # file. An absolute /<slug>/... path is passed through untouched and 404s.
    thumb = ('<a class="uwtn-thumb" href="/%s/"><img src="articles/%s/%s" alt=""></a>'
             % (slug, slug, banner)) if banner else ""

    return "".join([
        '<div class="uwtn-entry%s">' % (" uwtn-lead" if lead else ""),
        thumb,
        '<div class="uwtn-entry-text">',
        '<div class="uwtn-entry-meta">',
        '<span class="uwtn-id">%s</span>' % text(str(meta.get("id") or "")),
        '<span class="uwtn-date">%s</span>' % format_date(meta.get("publication_date")),
        '</div>',
        '<h2><a href="/%s/">%s</a></h2>' % (
            slug, text(str(meta.get("title") or slug))),
        '<div class="uwtn-entry-byline">%s</div>' % text(byline),
        '<div class="uwtn-entry-summary">%s</div>' % text(description),
        '<div class="uwtn-entry-links">%s</div>' % " ".join(links),
        ('<div class="uwtn-tags">%s</div>' % tags) if tags else "",
        '</div>',
        '</div>',
    ])


TOC_BEGIN = "  # BEGIN GENERATED TOC"
TOC_END = "  # END GENERATED TOC"
NAV_BEGIN = "  # BEGIN GENERATED NAV"
NAV_END = "  # END GENERATED NAV"


def write_nav():
    """Rewrite site.nav in myst.yml from pages.yml.

    The standing pages are the site's furniture, not its content, so they
    belong in the header rather than in the sidebar beside the notes -- MyST
    keeps the two separate, and `nav` takes dropdowns via `children`.
    """
    config_path = ROOT / "pages.yml"
    if not config_path.exists():
        return {}

    pages, slug = {}, None
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith(" ") and raw.rstrip().endswith(":"):
            slug = raw.rstrip()[:-1]
            pages[slug] = {}
        elif slug and ":" in raw:
            key, _, value = raw.strip().partition(":")
            pages[slug][key.strip()] = value.strip().strip('"')

    groups, standalone = {}, []
    for slug, settings in pages.items():
        group = settings.get("group", "").strip()
        if group:
            groups.setdefault(group, []).append((settings.get("title", slug), slug))
        else:
            # No group: a plain nav item. A one-page dropdown is just a worse link.
            standalone.append((settings.get("title", slug), slug))

    lines = ["  nav:"]
    for group, items in groups.items():
        lines.append('    - title: "%s"' % group)
        lines.append("      children:")
        for title, slug in items:
            lines.append('        - title: "%s"' % title)
            lines.append("          url: /%s" % slug)
    for title, slug in standalone:
        lines.append('    - title: "%s"' % title)
        lines.append("      url: /%s" % slug)
    lines.append('    - title: "Topics"')
    lines.append("      url: /topics")

    myst = ROOT / "myst.yml"
    text = myst.read_text(encoding="utf-8")
    if NAV_BEGIN not in text:
        sys.exit("myst.yml is missing the generated-nav markers")
    head, _, rest = text.partition(NAV_BEGIN)
    _, _, tail = rest.partition(NAV_END)
    myst.write_text("%s%s\n%s\n%s%s" % (head, NAV_BEGIN, "\n".join(lines), NAV_END, tail),
                    encoding="utf-8")
    return pages


def write_toc(metas):
    """Rewrite the toc in myst.yml, grouped by year, newest first.

    The sidebar is the reader's sense of the series over time, so it is
    organised the way the article ids are: by year. If the series ever adopts
    volumes, this is where that renaming happens -- nothing else depends on the
    grouping.

    Generated between markers rather than by rewriting the whole file, so the
    rest of myst.yml stays hand-edited.
    """
    myst = ROOT / "myst.yml"
    text = myst.read_text(encoding="utf-8")
    if TOC_BEGIN not in text or TOC_END not in text:
        sys.exit("myst.yml is missing the generated-toc markers")

    by_year = {}
    for meta, _description, _pdf in metas:
        year = str(meta.get("publication_date") or "")[:4] or "undated"
        by_year.setdefault(year, []).append(meta)

    lines = ["  toc:", "    - file: index.md"]
    topic_files = sorted((ROOT / "topics").glob("topic-*.md"))
    if topic_files:
        lines.append('    - title: "Topics"')
        lines.append("      children:")
        lines.append("        - file: topics/topics.md")
        for path in topic_files:
            lines.append("        - file: topics/%s" % path.name)
    page_files = sorted((ROOT / "pages").glob("*.md"))
    if page_files:
        lines.append('    - title: "About"')
        lines.append("      children:")
        for path in page_files:
            lines.append("        - file: pages/%s" % path.name)
    for year in sorted(by_year, reverse=True):
        lines.append('    - title: "%s"' % year)
        lines.append("      children:")
        for meta in by_year[year]:
            slug = meta["slug"]
            lines.append("        - file: articles/%s/%s.md" % (slug, slug))

    head, _, rest = text.partition(TOC_BEGIN)
    _, _, tail = rest.partition(TOC_END)
    myst.write_text("%s%s\n%s\n%s%s" % (head, TOC_BEGIN, "\n".join(lines), TOC_END, tail),
                    encoding="utf-8")
    return by_year


def vocabulary():
    """axis -> {term: (label, scope)} from vocabulary.yml."""
    text = (ROOT / "vocabulary.yml").read_text(encoding="utf-8")
    axes, axis, term = {}, None, None
    for raw in text.splitlines():
        if raw.startswith("#") or not raw.strip():
            continue
        if not raw.startswith(" ") and raw.rstrip().endswith(":"):
            axis = raw.rstrip()[:-1]
            axes[axis] = {}
        elif raw.startswith("  ") and not raw.startswith("    ") and raw.rstrip().endswith(":"):
            term = raw.strip()[:-1]
            axes[axis][term] = ["", ""]
        elif raw.startswith("    ") and term:
            key, _, value = raw.strip().partition(":")
            value = value.strip().strip(">-").strip()
            if key == "label":
                axes[axis][term][0] = value
            elif key == "scope" and value:
                axes[axis][term][1] = value
        elif raw.startswith("      ") and term:
            axes[axis][term][1] = (axes[axis][term][1] + " " + raw.strip()).strip()
    return axes


def topic_slug(tag):
    """A URL slug for a tag, prefixed so it can never collide with an article.

    MyST takes a page's URL from its filename regardless of directory, so a
    topic page called `documentation.md` would compete with any article of that
    slug -- and article slugs are fixed by registered DOIs.
    """
    return "topic-" + re.sub(r"[^a-z0-9]+", "-", str(tag).lower()).strip("-")


def write_topic_pages(metas):
    """One page per tag, plus an index. Returns tag -> (slug, count).

    Static pages rather than a search query. The built search index is derived
    from page content -- its records carry only hierarchy, type, url and
    position -- so there is no tag field for a `tag:x` query to match against.
    Generated pages also give each topic a real URL that can be linked, shared
    and indexed.

    Each topic page does carry a visible ``tag:<slug>`` token, which the search
    index then contains, so the query works after all. Visible rather than
    hidden: searching the bare tag word buries the topic page under every prose
    mention of it, and a token nobody can see is a query nobody knows to type.
    """
    vocab = vocabulary()
    topics, axis_of, label_of, scope_of = {}, {}, {}, {}
    for axis in ("subjects", "methods"):
        for term, (label, scope) in vocab.get(axis, {}).items():
            label_of[term], scope_of[term], axis_of[term] = label, scope, axis
    for meta, description, has_pdf in metas:
        for axis in ("subjects", "methods"):
            for term in (meta.get(axis) or []):
                topics.setdefault(term, []).append((meta, description, has_pdf))

    directory = ROOT / "topics"
    directory.mkdir(exist_ok=True)
    for existing in directory.glob("*.md"):
        existing.unlink()

    for tag, entries in topics.items():
        slug = topic_slug(tag)
        body = "\n".join(entry_html(m, d, p) for m, d, p in entries)
        page = (
            '---\ntitle: "{label}"\nsite:\n  hide_outline: true\n---\n\n'
            '<div class="uwtn-topic-head">'
            '<div class="uwtn-kicker">{kicker}</div>'
            '<div class="uwtn-wordmark">{label}</div>'
            '<div class="uwtn-standfirst">{scope}</div>'
            '<div class="uwtn-query">{count} note{plural} &middot; '
            'search <code>tag:{token}</code> &middot; '
            '<a href="/topics/">all topics</a></div>'
            '</div>\n\n'
            '<div class="uwtn-feed">\n{body}\n</div>\n'
        ).format(label=text(label_of.get(tag, tag)),
                 kicker="Subject" if axis_of.get(tag) == "subjects" else "Method",
                 scope=text(scope_of.get(tag, "")),
                 count=len(entries), plural="" if len(entries) == 1 else "s",
                 token=slug[len("topic-"):], body=body)
        (directory / ("%s.md" % slug)).write_text(page, encoding="utf-8")

    sections = []
    for axis, heading in (("subjects", "Subject"), ("methods", "Method")):
        terms = [(t_, e) for t_, e in topics.items() if axis_of.get(t_) == axis]
        if not terms:
            continue
        links = "".join(
            '<a class="uwtn-topic-link" href="/%s/">%s<span class="uwtn-topic-count">%d</span></a>'
            % (topic_slug(term), text(label_of.get(term, term)), len(entries))
            for term, entries in sorted(terms, key=lambda kv: (-len(kv[1]), kv[0])))
        unused = sorted(t_ for t_ in vocab.get(axis, {}) if t_ not in topics)
        note = ""
        if unused:
            # Shown rather than hidden: an empty facet is a statement about the
            # corpus -- these are subjects the series has not covered yet.
            note = ('<div class="uwtn-unused">Not yet used: %s</div>'
                    % ", ".join(text(label_of[t_]) for t_ in unused))
        sections.append('<div class="uwtn-axis"><div class="uwtn-year">%s</div>'
                        '<div class="uwtn-topic-list">%s</div>%s</div>'
                        % (heading, links, note))

    (directory / "topics.md").write_text(
        '---\ntitle: Topics\nsite:\n  hide_outline: true\n---\n\n'
        '<div class="uwtn-topic-head"><div class="uwtn-kicker">Browse</div>'
        '<div class="uwtn-wordmark">Topics</div>'
        '<div class="uwtn-standfirst">Notes are classified on two axes: the Earth\u2019s '
        'behaviour they are about, and the computational method they use. Many are '
        'purely about method, and carry no subject. Each facet has a page, and can '
        'be reached from the search box as <code>tag:name</code>.</div></div>\n\n'
        + "\n".join(sections) + "\n", encoding="utf-8")

    return {tag: (topic_slug(tag), len(entries)) for tag, entries in topics.items()}


def banner_of(directory):
    for candidate in ("banner.jpg", "banner.png", "banner.webp"):
        if (directory / "figures" / candidate).exists():
            return "figures/" + candidate
    return None


def main():
    for axis, terms in vocabulary().items():
        for term, (label, _scope) in terms.items():
            FACET_LABELS[term] = label

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
    topics = write_topic_pages(metas)
    pages = write_nav()
    by_year = write_toc(metas)

    # The most recent note leads, shown larger and with its banner; the rest
    # follow as a compact list under a rule for each year.
    blocks, seen_year = [], None
    for index, (meta, description, has_pdf) in enumerate(metas):
        year = str(meta.get("publication_date") or "")[:4]
        if year != seen_year:
            blocks.append('<div class="uwtn-year">%s</div>' % year)
            seen_year = year
        directory = ARTICLES / meta["slug"]
        blocks.append(entry_html(meta, description, has_pdf,
                                 banner=banner_of(directory) if index == 0 else None,
                                 lead=(index == 0)))
    entries = "\n".join(blocks)

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

<div class="uwtn-colophon">%d notes, %d with a registered DOI. The DOI identifies the archival publication; this site is the current rendition and may carry corrections, updated links and discussion. Notes are written by the Underworld community — <a href="/submit/">how to submit one</a>.</div>
""" % (entries, len(metas), with_doi)

    (ROOT / "index.md").write_text(page, encoding="utf-8")
    print("nav: %d standing page(s)" % len(pages))
    print("topics: %d (%s)" % (len(topics), ", ".join(sorted(topics))))
    print("index.md: %d note(s), %d with a DOI, %d with a PDF"
          % (len(metas), with_doi, sum(1 for _m, _d, p in metas if p)))
    for meta, _description, _pdf in metas:
        print("  %-12s %-11s %s" % (meta.get("id"), meta.get("publication_date"),
                                    str(meta.get("title"))[:52]))


if __name__ == "__main__":
    main()
