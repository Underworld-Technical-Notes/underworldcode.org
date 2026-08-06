#!/usr/bin/env python3
"""Inline the site stylesheet into every built page, for the first paint.

``site.options.style`` in ``myst.yml`` is what actually styles the site: the
theme is a React app that injects the stylesheet from the page's hydration
data. That is easy to miss, because the path in ``config.json`` is wrong
(``/uwtn-<hash>.css`` while the file is written to ``/build/uwtn-<hash>.css``)
and there is no ``<link>`` in the static HTML — but the hydration payload
carries the correct, BASE_URL-adjusted path, and the theme uses that.

The gap it leaves is the first paint. Until React hydrates there is no
stylesheet at all, so the page appears briefly as unstyled text. This inlines
the same CSS into ``<head>`` so the very first frame is correct. Hydration then
discards the inlined tag and the theme's own link takes over, which is
seamless because they are the same stylesheet.

Do not remove ``style:`` from ``myst.yml`` and rely on this alone: hydration
would strip the inlined tag and leave the page permanently unstyled, having
looked correct for a moment first.

Usage:
    python3 scripts/inject_style.py [--build _build/html] [--style static/uwtn.css]
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = "uwtn-inlined-style"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    parser.add_argument("--style", default="static/uwtn.css")
    args = parser.parse_args()

    build = ROOT / args.build
    style = ROOT / args.style
    if not build.exists():
        sys.exit("no build at %s -- run `myst build --html` first" % build)
    if not style.exists():
        sys.exit("no stylesheet at %s" % style)

    css = style.read_text(encoding="utf-8")
    if "</style>" in css:
        sys.exit("stylesheet contains </style> and cannot be inlined safely")
    block = '<style id="%s">\n%s\n</style>' % (MARKER, css)

    injected, skipped = 0, 0
    for page in sorted(build.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        if MARKER in text:
            skipped += 1
            continue
        if "</head>" not in text:
            continue
        page.write_text(text.replace("</head>", block + "</head>", 1), encoding="utf-8")
        injected += 1

    print("inlined the stylesheet into %d page(s)%s"
          % (injected, "" if not skipped else " (%d already had it)" % skipped))
    if injected == 0 and skipped == 0:
        sys.exit("no pages were styled -- the build layout has changed")


if __name__ == "__main__":
    main()
