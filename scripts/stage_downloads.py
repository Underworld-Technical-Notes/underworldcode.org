#!/usr/bin/env python3
"""Place each article's archival PDF and markdown source beside its page.

MyST writes the PDF next to the article source, not into the site, so without
this the download link on every page and on the front page is a 404. The PDF is
served from the article's own URL -- ``/<slug>/<slug>.pdf`` -- so it travels
with the article and does not depend on a separate downloads area.

Run after ``myst build --html``; ``pixi run build-html`` does this.

Usage:
    python3 scripts/stage_downloads.py [--build _build/html]
"""

import argparse
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    args = parser.parse_args()

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s -- run `myst build --html` first" % build)

    staged, missing = [], []
    for directory in sorted(ARTICLES.iterdir()):
        if not directory.is_dir():
            continue
        slug = directory.name
        pdf = directory / ("%s.pdf" % slug)
        target_dir = build / slug
        if not target_dir.exists():
            continue          # not in the toc; nothing to attach it to
        if not pdf.exists():
            missing.append(slug)
            continue
        shutil.copy2(pdf, target_dir / pdf.name)
        staged.append((slug, pdf.stat().st_size))
        # The markdown the article is written from, at /<slug>/<slug>.md. The
        # reader page offers it beside the PDF: it is what someone reusing a
        # figure, a table or an equation actually wants, and it is already here.
        source = directory / ("%s.md" % slug)
        if source.exists():
            shutil.copy2(source, target_dir / source.name)

    for slug, size in staged:
        print("  staged %-56s %5dKB" % (slug[:56], size / 1024))
    if missing:
        # Not fatal: `pixi run build-html` alone does not produce PDFs, and a
        # site without them is still correct -- the links simply do not appear.
        print("  %d article(s) built without a PDF: %s"
              % (len(missing), ", ".join(m[:40] for m in missing[:4])), file=sys.stderr)
    print("%d PDF(s) staged into the site" % len(staged))


if __name__ == "__main__":
    main()
