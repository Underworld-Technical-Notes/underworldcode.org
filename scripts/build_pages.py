#!/usr/bin/env python3
"""Recapture the standing pages from the Ghost site.

These are the site's furniture rather than its content -- who we are, how to
cite, credits, governance -- so they live in the header navigation rather than
in the table of contents beside the notes.

Which pages come across, and which do not, is declared in ``pages.yml``: the
Ghost site accumulated stubs, a dead mailing-list page and material about other
projects, and carrying all of it over would be migration by inertia.

The Zotero-backed bibliographies are **baked at build time** rather than
fetched by client-side JavaScript. Ghost rendered them with jQuery against
api.zotero.org on every page load, which meant the page was empty without
scripts, empty if Zotero was down, and empty in the archive. The collection is
public, so the same content can simply be part of the page.

Usage:
    python3 scripts/build_pages.py [--refresh]
"""

import argparse
import html
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPORT = ROOT / "inventory" / "ghost-export"
PAGES = ROOT / "pages"
CACHE = ROOT / "inventory" / "bibliography"


def load_pages_config():
    """slug -> {title, nav, group} for pages declared in pages.yml."""
    path = ROOT / "pages.yml"
    config, slug = {}, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith(" ") and raw.rstrip().endswith(":"):
            slug = raw.rstrip()[:-1]
            config[slug] = {}
        elif slug and ":" in raw:
            key, _, value = raw.strip().partition(":")
            config[slug][key.strip()] = value.strip().strip('"')
    return config


def zotero_bibliography(group, collection, refresh=False):
    """The rendered bibliography for a public Zotero collection.

    Cached in the repository so a build does not depend on Zotero being up, and
    so the deposited copy of a page is the one that was published.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / ("%s-%s.html" % (group, collection))
    if cached.exists() and not refresh:
        return cached.read_text(encoding="utf-8")

    url = ("https://api.zotero.org/groups/%s/collections/%s/items"
           "?format=bib&style=apa&linkwrap=1" % (group, collection))
    request = urllib.request.Request(url, headers={"User-Agent": "uwtn-pages/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        body = response.read().decode("utf-8")
    cached.write_text(body, encoding="utf-8")
    return body


DOI_ANCHOR = re.compile(r'<a[^>]+href="https?://(?:dx\.)?doi\.org/([^"]+)"[^>]*>(.*?)</a>', re.S)
# The converter emits markdown links, so the same rule has to apply to those.
DOI_MARKDOWN = re.compile(r'\[([^\]]*)\]\(https?://(?:dx\.)?doi\.org/([^)]+)\)')


def unlink_dois(text):
    """Render DOIs as text rather than links.

    MyST rewrites any doi.org href into a citation and appends a References
    section built from them. On a page that is already a bibliography that
    duplicates every entry; on a catalogue it lists works that have nothing to
    do with the page. The DOI stays visible either way -- it is an identifier,
    and this site is not the place it needs to be clickable.
    """
    text = DOI_ANCHOR.sub(lambda m: m.group(2) or m.group(1), text)
    return DOI_MARKDOWN.sub(lambda m: m.group(1) or m.group(2), text)


def bibliography_html(raw):
    entries = re.findall(r'<div class="csl-entry">(.*?)</div>', unlink_dois(raw), re.S)
    items = "".join(
        '<div class="uwtn-ref">%s</div>' % " ".join(entry.split()) for entry in entries)
    return len(entries), '<div class="uwtn-bibliography">%s</div>' % items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true",
                        help="re-fetch the bibliographies from Zotero")
    args = parser.parse_args()

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ghost_to_myst", ROOT / "scripts" / "ghost_to_myst.py")
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)

    config = load_pages_config()
    records = {p["slug"]: p for p in
               json.loads((EXPORT / "pages.json").read_text(encoding="utf-8"))["pages"]}

    PAGES.mkdir(exist_ok=True)
    for existing in PAGES.glob("*.md"):
        existing.unlink()

    written = []
    for slug, settings in config.items():
        # A nav-only entry: `url` points at a page build_index.py generates
        # (/notes, /topics). It is declared in pages.yml so its position in the
        # header comes from the same place as everything else, but there is
        # nothing here to write -- and looking for it in the Ghost export
        # reported it as missing on every build.
        if settings.get("url"):
            continue
        written_source = settings.get("source")
        if written_source:
            # A hand-written replacement: the Ghost page was not worth
            # migrating, but the page is worth having.
            body = (ROOT / written_source).read_text(encoding="utf-8")
            conv = converter.GhostToMyst(slug)
            record = records.get(slug) or {}
        else:
            record = records.get(slug)
            if record is None:
                print("  MISSING from the Ghost export: %s" % slug, file=sys.stderr)
                continue
            conv = converter.GhostToMyst(slug)
            conv.feed(record.get("html") or "")
            conv.close()
            body = unlink_dois(conv.markdown())

        note = ""
        if settings.get("zotero"):
            group, collection = settings["zotero"].split("/")
            count, rendered = bibliography_html(
                zotero_bibliography(group, collection, args.refresh))
            body += "\n\n" + rendered
            note = "%d references baked" % count

        title = settings.get("title") or record.get("title") or slug
        (PAGES / ("%s.md" % slug)).write_text(
            '---\ntitle: "%s"\nsite:\n  hide_outline: true\n---\n\n%s' % (title, body),
            encoding="utf-8")

        for src, name, _alt, _cap in conv.figures:
            # Already present means committed from an earlier run: page figures
            # are kept in the repository because they come from the Ghost
            # mirror and from GitHub, and CI has neither.
            if (PAGES / "figures" / name).exists():
                continue
            result = converter.copy_figure(src, name, PAGES / "figures")
            if not result.startswith(("copied", "localised")):
                print("  %s: %s -- page figures must be committed"
                      % (slug, result), file=sys.stderr)

        written.append((slug, len(body.split()), conv.dropped, note))

    for slug, words, dropped, note in written:
        print("  %-34s %5dw  %s%s" % (slug[:34], words,
                                      ("dropped %s  " % dict(dropped)) if dropped else "",
                                      note))
    print("%d page(s) written to pages/" % len(written))


if __name__ == "__main__":
    main()
