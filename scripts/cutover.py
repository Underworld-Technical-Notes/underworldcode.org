#!/usr/bin/env python3
"""Move the site from the staging host to underworldcode.org.

The repository side of the cutover is three coupled edits, and doing two of
them is worse than doing none:

    CNAME              claims the domain, AND switches the build from the
                       project subpath to the site root -- deploy.yml derives
                       the base URL from this file's presence
    giscus.yml         site_url, which is where a reader is sent back to after
                       signing in with GitHub. Left pointing at the staging
                       host, the comment widget loads and offers no way to
                       comment
    README, SETUP      prose that tells the next person where the site is

Order matters and it is not the order you would guess. Adding CNAME BEFORE the
DNS record moves takes the staging site down: GitHub Pages redirects
github.io to the custom domain, and the custom domain still serves Ghost. So
the sequence is

    1. pixi run test-dois          all fifty registered DOIs resolve
    2. change the DNS at Netregistry: www A record -> GitHub Pages
    3. python3 scripts/cutover.py  (this) -- commit and push
    4. pixi run test-dois --live   against production
    5. leave the droplet firewalled but powered for two weeks

--check reports whether the repository is ready and what remains, and touches
nothing.

Usage:
    python3 scripts/cutover.py [--check] [--host www.underworldcode.org]
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STAGING = "https://underworld-technical-notes.github.io/underworldcode.org"


def edits(host):
    """[(path, from, to)] -- every place the host is named."""
    site = "https://%s" % host
    return [
        (ROOT / "giscus.yml", STAGING, site),
        (ROOT / "README.md", "%s/" % STAGING, "%s/" % site),
        (ROOT / "SETUP.md", "%s/" % STAGING, "%s/" % site),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--host", default="www.underworldcode.org",
                        help="the host the fifty registered DOIs point at")
    args = parser.parse_args()

    cname = ROOT / "CNAME"
    done = cname.exists() and cname.read_text(encoding="utf-8").strip() == args.host
    pending = [(path, old) for path, old, _new in edits(args.host)
               if path.exists() and old in path.read_text(encoding="utf-8")]

    if args.check:
        print("CNAME      : %s" % (("%s" % cname.read_text(encoding="utf-8").strip())
                                   if cname.exists() else "absent -- still on the staging host"))
        for path, _old in pending:
            print("still staging: %s" % path.relative_to(ROOT))
        if done and not pending:
            print("\nthe repository is cut over.")
        else:
            print("\nnot cut over. Move the DNS FIRST -- a CNAME while www still "
                  "points at the droplet redirects the staging site to Ghost.")
        return

    cname.write_text("%s\n" % args.host, encoding="utf-8")
    print("CNAME -> %s" % args.host)
    for path, old, new in edits(args.host):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if old not in text:
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        print("  %s: %s -> %s" % (path.relative_to(ROOT), old, new))

    print("\nCommit and push. The deploy workflow will see the CNAME and build "
          "at the site root rather than the project subpath.")
    print("Then: pixi run test-dois, and set the custom domain in the "
          "repository's Pages settings so HTTPS is issued.")


if __name__ == "__main__":
    main()
