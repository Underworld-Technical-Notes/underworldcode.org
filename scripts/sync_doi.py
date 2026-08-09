#!/usr/bin/env python3
"""Put the archival DOI on the article, before the PDF is built.

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

Usage:
    python3 scripts/sync_doi.py [--check]
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
sys.path.insert(0, str(ROOT / "scripts"))


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

        current = re.search(r"^doi:\s*(.+)$", head, re.M)
        if current and current.group(1).strip() == wanted:
            continue

        stale.append("%s: %s -> %s"
                     % (slug, current.group(1).strip() if current else "(none)", wanted))
        if args.check:
            continue

        if current:
            head = re.sub(r"^doi:.*$", "doi: %s" % wanted, head, count=1, flags=re.M)
        else:
            head = head.rstrip("\n") + "\ndoi: %s" % wanted
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
