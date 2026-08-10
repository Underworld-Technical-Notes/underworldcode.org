#!/usr/bin/env python3
"""Assert that every registered DOI still lands on a page in the built site.

This is the most important test in the repository. Fifty Crossref DOIs, minted
by Rogue Scholar under a prefix we do not control, resolve to
``https://www.underworldcode.org/<slug>/``. They cannot be re-pointed. If a
build stops serving one of those paths, a registered DOI breaks permanently.

The test reads ``inventory/doi-register.csv`` -- not the sitemap, and not the
list of files that happen to exist -- and checks the built HTML tree for each.

While the migration is staged, DOIs for articles not yet converted are reported
as *pending* rather than failing. Set --strict once the full corpus has landed,
which is the state the production CI must run in.

Exit status is 1 if any expected page is missing.

--live checks PRODUCTION instead: it follows each DOI's target URL over the
network and fails on anything that is not a 200. A file existing in a build
directory is a good proxy before cutover and no proof at all afterwards --
between the two sit DNS, the custom domain, the base URL, the redirect from
the apex, and the certificate. Every one of those was a way to break fifty
DOIs on the day the site moved, and none of them is visible in _build/html.

Usage:
    python3 scripts/test_doi_urls.py [--build _build/html] [--strict]
    python3 scripts/test_doi_urls.py --live [--host www.underworldcode.org]
"""

import argparse
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def check_live(entries, host):
    """Resolve every registered DOI's target against the running site."""
    import concurrent.futures
    import urllib.error
    import urllib.request

    def fetch(entry):
        url = "https://%s/%s/" % (host, entry["slug"])
        request = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "uwtn-doi-check"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return entry, response.status, response.url
        except urllib.error.HTTPError as exc:
            return entry, exc.code, url
        except Exception as exc:                       # DNS, TLS, timeout
            return entry, 0, "%s (%s)" % (url, exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch, entries))

    good = [r for r in results if r[1] == 200]
    bad = [r for r in results if r[1] != 200]
    print("DOI register: %d entries, checked against https://%s"
          % (len(entries), host))
    print("  resolved 200 : %d" % len(good))
    print("  BROKEN       : %d" % len(bad))
    for entry, status, where in bad:
        print("  https://doi.org/%s -> %s  [%s]"
              % (entry["doi"], where, status or "no response"))
    if bad:
        sys.exit(1)
    print("\nOK -- all %d registered DOIs resolve on the live site." % len(good))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html", help="built site root")
    parser.add_argument("--strict", action="store_true",
                        help="treat not-yet-migrated DOIs as failures")
    parser.add_argument("--live", action="store_true",
                        help="check the running site over the network")
    parser.add_argument("--host", default="www.underworldcode.org",
                        help="the host the registered DOIs point at")
    args = parser.parse_args()

    register = ROOT / "inventory" / "doi-register.csv"
    if not register.exists():
        sys.exit("no DOI register -- run scripts/inventory_site.py first")

    with register.open(encoding="utf-8") as fh:
        entries = list(csv.DictReader(fh))

    if args.live:
        check_live(entries, args.host)
        return

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s -- run `myst build --html` first" % build)

    # Which slugs has this build actually converted?
    converted = {p.parent.name for p in (ROOT / "articles").glob("*/*.md")}

    resolved, pending, broken = [], [], []
    for entry in entries:
        slug, doi = entry["slug"], entry["doi"]
        page = build / slug / "index.html"
        if page.exists():
            resolved.append((doi, slug))
        elif slug in converted:
            # Converted but absent from the build: almost always a missing toc
            # entry, and exactly the silent failure this test exists to catch.
            broken.append((doi, slug, "converted but not built -- check myst.yml toc"))
        else:
            pending.append((doi, slug))

    print("DOI register: %d entries" % len(entries))
    print("  resolved in build : %d" % len(resolved))
    print("  pending migration : %d" % len(pending))
    print("  BROKEN            : %d" % len(broken))

    if broken:
        print("\nBROKEN -- these DOIs would 404:")
        for doi, slug, why in broken:
            print("  https://doi.org/%s -> /%s/  (%s)" % (doi, slug, why))

    if pending:
        print("\npending (not yet migrated; still served by Ghost):")
        for doi, slug in pending[:60]:
            print("  https://doi.org/%s -> /%s/" % (doi, slug))

    if broken:
        sys.exit(1)
    if args.strict and pending:
        print("\n--strict: %d DOI(s) still unmigrated" % len(pending))
        sys.exit(1)
    print("\nOK -- no registered DOI is broken by this build.")


if __name__ == "__main__":
    main()
