#!/usr/bin/env python3
"""Inline the site stylesheet into every built page.

MyST's ``site.options.style`` does not work here, on mystmd 1.10.1: it records
the stylesheet in ``config.json`` as ``/uwtn-<hash>.css`` while writing the file
to ``/build/uwtn-<hash>.css``, so the path never resolves — and the recorded
path is not adjusted for ``BASE_URL`` either, so a project site served under a
subpath would miss it a second way. Both failures are silent: the site renders,
unstyled, and looks merely plain rather than broken.

Inlining sidesteps the whole question. The stylesheet is small, it costs no
extra request, and it cannot be defeated by a path prefix.

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
