#!/usr/bin/env python3
"""Put the archival facts on the article, before the PDF is built.

The whole reason Figshare was chosen is that a DOI can be reserved *before* the
document exists, so it can be printed on the document it identifies. That only
works if something carries the reserved DOI from `metadata.yml`, where the
deposit writes it, into the article's front matter, which is what the PDF
template renders. This is that something.

It cannot live in the converter. `archive_doi` is assigned by the deposit, long
after conversion, and re-running the converter to pick it up would discard the
merged original text and the rebuilt vector figures. So it runs at build time,
like the banner, and is idempotent in both directions.

Which DOI wins:

  * `archive_doi` if the note has been deposited -- it resolves to a fixed
    record with checksums, and it is the one to circulate;
  * otherwise `legacy_doi`, the Rogue Scholar registration, which resolves to
    the web page. For the fifty migrated notes that is all there is until they
    are deposited.

Three things travel from `metadata.yml` into the front matter and the export
options, so the PDF can state them:

  * `archive_doi`, the identifier that resolves to this document;
  * `archived_at`, when the archival version was made;
  * the source URL, where the living article is.

Together the last two are what a reader of a fixed document most needs: a
snapshot with no date cannot be judged against the article it came from, and a
date with no link cannot be followed up.

Usage:
    python3 scripts/sync_archival.py [--check]
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
sys.path.insert(0, str(ROOT / "scripts"))


SITE = "https://www.underworldcode.org"


def set_frontmatter(head, key, value):
    if re.search(r"^%s:\s*.+$" % key, head, re.M):
        return re.sub(r"^%s:.*$" % key, "%s: %s" % (key, value), head,
                      count=1, flags=re.M)
    return head.rstrip("\n") + "\n%s: %s" % (key, value)


def set_export_option(head, key, value):
    """Set a key inside the typst export block.

    The export block is where the PDF template's own options live, and it is
    indented under `exports:`; a top-level key of the same name would be
    ignored. Articles that get no archival PDF have no export block, and are
    left alone.
    """
    if "  - format: typst" not in head:
        return head
    if re.search(r"^    %s:\s*.+$" % key, head, re.M):
        return re.sub(r"^    %s:.*$" % key, "    %s: %s" % (key, value), head,
                      count=1, flags=re.M)
    return re.sub(r"^(  - format: typst\n)", r"\g<1>    %s: %s\n" % (key, value),
                  head, count=1, flags=re.M)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report what would change; do not write")
    args = parser.parse_args()

    import build_index

    changed, stale = 0, []
    for meta_path in sorted(ARTICLES.glob("*/metadata.yml")):
        meta = build_index.read_yaml(meta_path)
        slug = meta.get("slug")
        wanted = meta.get("archive_doi") or meta.get("legacy_doi")
        if not wanted:
            continue

        source = meta_path.parent / ("%s.md" % slug)
        text = source.read_text(encoding="utf-8")
        head, sep, body = text.partition("\n---\n")
        if not sep:
            continue

        source_url = SITE + str(meta.get("canonical_path") or ("/%s/" % slug))
        wants = {"doi": wanted}
        exports = {"origin_url": source_url}
        if meta.get("archived_at"):
            # Quoted, because YAML reads an unquoted ISO-8601 stamp as a
            # timestamp rather than a string -- and the template option is
            # declared as a string, so it was being dropped on the floor
            # without a word. The PDF simply had no Archived line.
            exports["archived"] = '"%s"' % meta["archived_at"]

        before = head
        # An option that was once written under a different name stays in the
        # file forever otherwise, and MyST reports it as unknown on every build.
        head = re.sub(r"^    source_url:.*\n", "", head, flags=re.M)
        for key, value in wants.items():
            head = set_frontmatter(head, key, value)
        for key, value in exports.items():
            head = set_export_option(head, key, value)
        if head == before:
            continue

        stale.append("%s: doi %s%s" % (
            slug, wanted, ", archived %s" % meta["archived_at"]
            if meta.get("archived_at") else ""))
        if args.check:
            continue
        source.write_text(head + sep + body, encoding="utf-8")
        changed += 1

    for line in stale:
        print("  %s" % line)
    if args.check:
        if stale:
            sys.exit("%d article(s) would carry the wrong DOI on their PDF" % len(stale))
        print("every article's front matter carries the right DOI")
        return
    print("synced the DOI on %d article(s)" % changed)


if __name__ == "__main__":
    main()
