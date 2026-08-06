#!/usr/bin/env python3
"""Add or remove the visible banner block in article bodies.

The feature images kept from the Ghost posts belong on the web and not in the
archival PDF: a stock photograph on page one undercuts the point of a fixed,
citable document. But both renditions build from the same markdown.

The ``banner:`` entry in an article's front matter is the source of truth. The
visible ``<div class="uwtn-banner">`` in the body is derived from it, so it can
be removed before the Typst build and put back afterwards without losing
anything. Both directions are idempotent, so an interrupted build leaves
nothing to repair -- and ``pixi run migrate`` regenerates the articles anyway.

    python3 scripts/banner_body.py --remove    # before myst build --typst
    python3 scripts/banner_body.py --add       # after

(An earlier attempt relied on Typst dropping raw HTML. It does not: the banner
rendered on page one of every PDF.)
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"

BANNER_BLOCK = re.compile(
    r'<div class="uwtn-banner"><img src="[^"]*" alt=""></div>\n\n', re.M)


def banner_from_frontmatter(text):
    match = re.search(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    found = re.search(r"^banner:\s*(\S+)\s*$", match.group(1), re.M)
    return found.group(1) if found else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add", action="store_true")
    group.add_argument("--remove", action="store_true")
    args = parser.parse_args()

    changed = 0
    for path in sorted(ARTICLES.glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        banner = banner_from_frontmatter(text)
        if not banner:
            continue

        head, sep, body = text.partition("\n---\n")
        if not sep:
            continue
        stripped = BANNER_BLOCK.sub("", body, count=1)

        if args.remove:
            new_body = stripped
        else:
            block = '<div class="uwtn-banner"><img src="%s" alt=""></div>\n\n' % banner
            new_body = block + stripped.lstrip("\n")

        if new_body != body:
            path.write_text(head + sep + new_body, encoding="utf-8")
            changed += 1

    print("banner block %s in %d article(s)"
          % ("removed" if args.remove else "added", changed))


if __name__ == "__main__":
    main()
