#!/usr/bin/env python3
"""Restore full-length article URLs after a MyST build.

MyST rewrites a page's URL from its filename in two ways that break a DOI:

  * it **limits the slug to 50 characters**, which moves twelve of the fifty
    registered DOI targets;
  * it **strips leading digits**, so `2-11-scaling` is published at `/scaling/`
    and `30-years-of-citcom-...` at `/years-of-citcom-.../`, moving two more.

Both are documented behaviour rather than bugs, and both are silent: the article
builds, looks right, and its DOI 404s.

This renames each mangled directory back to the full slug and rewrites every
internal reference to match. It runs as part of the build task; the DOI test
(`scripts/test_doi_urls.py`) is what proves it worked -- and is what caught the
leading-digit case, which nobody predicted.

The rule is **discovered, not assumed**: for each article the script looks for a
built directory whose name is a prefix *or* a suffix of the full slug, so it
covers characters removed from either end without encoding which. If MyST
changes its limit, or starts stripping something else, this keeps working.

Usage:
    python3 scripts/fix_slugs.py [--build _build/html] [--dry-run]
"""

import argparse
import pathlib
import re
import shutil
import sys

# MyST truncates a page's URL at this many characters.
SLUG_CAP = 50

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
        key = slug[:SLUG_CAP]
        prefixes.setdefault(key, []).append(slug)
    collisions = {k: v for k, v in prefixes.items() if len(v) > 1}
    if collisions:
        print("COLLISION: these slugs share a 50-character prefix:", file=sys.stderr)
        for key, group in collisions.items():
            print("  %s -> %s" % (key, ", ".join(group)), file=sys.stderr)
        sys.exit("cannot rename unambiguously; rename the source files")

    renames, claimed = [], {}
    for slug in slugs:
        if slug in built:
            continue                      # already correct, nothing to do
        # MyST mangles a URL in exactly two ways, and matching anything looser
        # lets one note claim another's page. On a preview -- which builds only
        # the notes a branch changes, so most slugs have no page at all --
        # `underworld-2-10` was matching `underworld-2` merely by starting with
        # it, and `joss-publication-underworld-2` by ending with it, so both
        # claimed /underworld-2/ and the run died on an ambiguity that does not
        # exist. Neither is a mangling of the other; they are three notes.
        #
        #   truncation     the URL is cut at SLUG_CAP characters
        #   leading strip  a leading NUMBER is dropped, so `2-11-scaling`
        #                  is served as /scaling/ and
        #                  `30-years-of-citcom-...` as /years-of-citcom-.../
        heads = [b for b in built
                 if len(slug) > SLUG_CAP and b == slug[:SLUG_CAP]]
        tails = [b for b in built
                 if b != slug and slug.endswith(b)
                 and re.fullmatch(r"[0-9]+(-[0-9]+)*-", slug[:len(slug) - len(b)])]
        candidates = heads + tails
        if not candidates:
            print("  WARNING: no built page found for %s" % slug, file=sys.stderr)
            continue
        mangled = max(candidates, key=len)   # the longest match is the real one
        if mangled in claimed:
            sys.exit("AMBIGUOUS: /%s/ could belong to %s or %s -- rename the "
                     "source files" % (mangled, claimed[mangled], slug))
        claimed[mangled] = slug
        renames.append((mangled, slug, mangled in heads))

    if not renames:
        print("all %d article URL(s) already full length" % len(slugs))
        return

    print("restoring %d mangled URL(s):" % len(renames))
    for mangled, slug, _head in renames:
        print("  /%s/  ->  /%s/" % (mangled, slug))
    if args.dry_run:
        print("\n--dry-run: nothing changed")
        return

    # 1. Move the directories and their sibling .json payloads.
    for mangled, slug, _head in renames:
        src, dest = build / mangled, build / slug
        if dest.exists():
            shutil.rmtree(dest)
        src.rename(dest)
        src_json, dest_json = build / (mangled + ".json"), build / (slug + ".json")
        if src_json.exists():
            src_json.rename(dest_json)

    # 2. Rewrite references. The mangled name is part of the full slug, so a
    #    plain replace would corrupt already-correct occurrences. The negative
    #    lookahead only matches it when not followed by a slug character -- i.e.
    #    never inside the full slug.
    #
    #    A name mangled at the FRONT needs more care, because what is left can be
    #    an ordinary English word: `2-11-scaling` publishes at `/scaling/`, and
    #    rewriting every "scaling" in the prose would be worse than the bug. Those
    #    are matched only after a URL or JSON delimiter, never after a space.
    patterns = []
    for mangled, slug, head in renames:
        before = "" if head else r"(?<=[/\"=#])"
        patterns.append(
            (re.compile(before + re.escape(mangled) + r"(?![A-Za-z0-9_-])"), slug))
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
