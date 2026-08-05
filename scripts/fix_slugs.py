#!/usr/bin/env python3
"""Restore full-length article URLs after a MyST build.

MyST derives a page's URL from its filename and **limits the slug to 50
characters** (documented behaviour, not a bug). Twelve of the fifty registered
DOIs point at slugs longer than that, so an unmodified build silently serves
those articles at a truncated path and those DOIs 404.

This renames each truncated directory back to the full slug and rewrites every
internal reference to match. It runs as part of the build task; the DOI test
(`scripts/test_doi_urls.py`) is what proves it worked.

The truncation rule is **discovered, not assumed** -- for each article the
script looks for a built directory whose name is a prefix of the full slug. If
MyST changes its limit, this keeps working.

Usage:
    python3 scripts/fix_slugs.py [--build _build/html] [--dry-run]
"""

import argparse
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Files whose contents may reference a page URL.
REWRITE_SUFFIXES = {".html", ".json", ".xml", ".txt", ".css", ".js"}


def article_slugs():
    """Full slugs, taken from the article source filenames."""
    return sorted({p.stem for p in (ROOT / "articles").glob("*/*.md")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s -- run `myst build --html` first" % build)

    built = {p.name for p in build.iterdir() if p.is_dir() and (p / "index.html").exists()}
    slugs = article_slugs()

    # Guard: two long slugs sharing a 50-character prefix would collide, and
    # MyST would disambiguate with a numeric suffix. Catch that before renaming.
    prefixes = {}
    for slug in slugs:
        key = slug[:50]
        prefixes.setdefault(key, []).append(slug)
    collisions = {k: v for k, v in prefixes.items() if len(v) > 1}
    if collisions:
        print("COLLISION: these slugs share a 50-character prefix:", file=sys.stderr)
        for key, group in collisions.items():
            print("  %s -> %s" % (key, ", ".join(group)), file=sys.stderr)
        sys.exit("cannot rename unambiguously; rename the source files")

    renames = []
    for slug in slugs:
        if slug in built:
            continue                      # already correct, nothing to do
        candidates = [b for b in built if slug.startswith(b) and b != slug]
        if not candidates:
            print("  WARNING: no built page found for %s" % slug, file=sys.stderr)
            continue
        truncated = max(candidates, key=len)   # longest prefix is the real one
        renames.append((truncated, slug))

    if not renames:
        print("all %d article URL(s) already full length" % len(slugs))
        return

    print("restoring %d truncated URL(s):" % len(renames))
    for truncated, slug in renames:
        print("  /%s/  ->  /%s/" % (truncated, slug))
    if args.dry_run:
        print("\n--dry-run: nothing changed")
        return

    # 1. Move the directories and their sibling .json payloads.
    for truncated, slug in renames:
        src, dest = build / truncated, build / slug
        if dest.exists():
            shutil.rmtree(dest)
        src.rename(dest)
        src_json, dest_json = build / (truncated + ".json"), build / (slug + ".json")
        if src_json.exists():
            src_json.rename(dest_json)

    # 2. Rewrite references. The truncated name is a prefix of the full slug, so
    #    a plain replace would corrupt already-correct occurrences. The negative
    #    lookahead only matches the truncated form when it is not followed by a
    #    slug character -- i.e. never inside the full slug.
    patterns = [(re.compile(re.escape(t) + r"(?![A-Za-z0-9_-])"), s) for t, s in renames]
    touched = 0
    for path in build.rglob("*"):
        if not path.is_file() or path.suffix not in REWRITE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new = text
        for pattern, slug in patterns:
            new = pattern.sub(slug, new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            touched += 1

    print("\nrewrote internal references in %d file(s)" % touched)
    print("run scripts/test_doi_urls.py to confirm no DOI is broken")


if __name__ == "__main__":
    main()
