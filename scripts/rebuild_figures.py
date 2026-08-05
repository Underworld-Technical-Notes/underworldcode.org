#!/usr/bin/env python3
"""Replace rasterised figures with vector ones rebuilt from their sources.

Several figures in the recent posts were drawn in Typst/cetz and committed to
the underworld3 repository alongside the data that generates them
(``publications/blog-posts/figures/``). Ghost only ever held the exported PNG,
so that is what the migration recovered: a screenshot of a drawing.

Where a source exists, this rebuilds the figure as SVG and points the article at
it. The result is sharp at any zoom in the archival PDF, much smaller, and
traceable back to the data that produced it -- the ``.typ`` source, its
``*-data.json`` and the ``generate-*.py`` that wrote them.

Figures with no source (screenshots, model output) are left alone and reported.

Usage:
    python3 scripts/rebuild_figures.py --repo ~/+Underworld/underworld3-pixi
    python3 scripts/rebuild_figures.py --repo ... --dry-run
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"


def find_sources(figures_dir):
    """basename stem -> .typ source path, searched recursively."""
    return {p.stem: p for p in figures_dir.rglob("*.typ")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="path to the underworld3 checkout")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_dir = pathlib.Path(args.repo).expanduser() / "publications" / "blog-posts" / "figures"
    if not source_dir.exists():
        sys.exit("no figure sources at %s" % source_dir)

    sources = find_sources(source_dir)
    print("%d figure source(s) available\n" % len(sources))

    rebuilt, unsourced, failed = [], [], []
    for figure in sorted(ARTICLES.glob("*/figures/*")):
        if figure.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        article = figure.parent.parent
        source = sources.get(figure.stem)
        if source is None:
            unsourced.append((article.name, figure.name))
            continue

        target = figure.with_suffix(".svg")
        if args.dry_run:
            rebuilt.append((article.name, figure.name, target.name, 0, 0))
            continue

        # Compile in the source's own directory: the .typ files read their data
        # with a relative json() call.
        result = subprocess.run(
            ["typst", "compile", "--format", "svg", source.name, str(target.resolve())],
            cwd=source.parent, capture_output=True, text=True)
        if result.returncode != 0:
            failed.append((article.name, figure.name, result.stderr.strip().splitlines()[:2]))
            continue

        before, after = figure.stat().st_size, target.stat().st_size
        figure.unlink()

        # Repoint the article. The figure may be referenced by a {figure}
        # directive or an inline image.
        for markdown in article.glob("*.md"):
            text = markdown.read_text(encoding="utf-8")
            updated = text.replace("figures/%s" % figure.name, "figures/%s" % target.name)
            if updated != text:
                markdown.write_text(updated, encoding="utf-8")
        rebuilt.append((article.name, figure.name, target.name, before, after))

    for article, old, new, before, after in rebuilt:
        note = "" if args.dry_run else "  %6dKB -> %5dKB" % (before / 1024, after / 1024)
        print("  rebuilt   %-46s %s -> %s%s" % (article[:46], old, new, note))
    for article, name in unsourced:
        print("  no source %-46s %s" % (article[:46], name))
    for article, name, err in failed:
        print("  FAILED    %-46s %s  %s" % (article[:46], name, " ".join(err)))

    if rebuilt and not args.dry_run:
        saved = sum(b - a for _, _, _, b, a in rebuilt)
        print("\n%d figure(s) rebuilt as vector, %.1f MB saved" % (len(rebuilt), saved / 1e6))
    print("%d figure(s) have no source and were left as-is" % len(unsourced))
    if failed:
        sys.exit("%d figure(s) failed to compile" % len(failed))


if __name__ == "__main__":
    main()
