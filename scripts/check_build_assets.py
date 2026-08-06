#!/usr/bin/env python3
"""Assert every local asset referenced by the built site actually exists.

MyST resolves and fingerprints images it can find relative to the source, and
passes through anything it cannot -- silently. A path that looks absolute and
correct (``/<slug>/figures/banner.jpg``) is emitted verbatim and 404s in the
browser, which is exactly how the front-page thumbnails broke.

Checks every ``src`` and local ``href`` in the built HTML against the build
tree. External URLs are left to ``scripts/check_links.py``.

Exit status is 1 if anything is missing.

Usage:
    python3 scripts/check_build_assets.py [--build _build/html]
"""

import argparse
import collections
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent

REFERENCE = re.compile(r'(?:src|href)="(/[^":]*?\.(?:png|jpg|jpeg|svg|webp|gif|css|js|pdf))"')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    parser.add_argument("--base-url", default="",
                        help="path prefix the site is served under, if any")
    args = parser.parse_args()

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s" % build)

    missing = collections.defaultdict(list)
    checked = 0
    for page in sorted(build.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        for reference in set(REFERENCE.findall(text)):
            path = urllib.parse.unquote(reference)
            if args.base_url and path.startswith(args.base_url + "/"):
                path = path[len(args.base_url):]
            checked += 1
            if not (build / path.lstrip("/")).exists():
                missing[reference].append(page.relative_to(build).parent.name or "/")

    print("checked %d local asset reference(s) across %d page(s)"
          % (checked, len(list(build.rglob("*.html")))))
    if missing:
        print("\n%d referenced asset(s) do not exist in the build:" % len(missing))
        for reference, pages in sorted(missing.items()):
            print("  %-64s referenced by: %s" % (reference[:64], ", ".join(sorted(set(pages))[:3])))
        sys.exit(1)
    print("all referenced assets are present.")


if __name__ == "__main__":
    main()
