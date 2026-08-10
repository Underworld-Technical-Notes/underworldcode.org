#!/usr/bin/env python3
"""Mark a built site as a preview, and give the branch a stable hashed path.

A preview exists so an unfinished note can be read and sent to a co-author
without being published. Two things follow from that, and both are done here.

**It must not be findable.** Every page gets `noindex, nofollow`, and the
sitemap and feeds are removed. An unfinished note that a search engine indexes
is worse than no preview at all: it competes with the canonical article for the
same title, and this series has fifty registered DOIs whose targets must be the
only copy that ranks.

**It must be visibly a preview.** A banner on every page, naming the branch and
the commit. Someone sent a link three weeks ago will not otherwise know whether
they are reading the draft or the published note, and the two look identical.

**The hashed path.** Each branch publishes to `/<hash>/`, derived from the
branch name -- stable, so a link keeps working as the branch is updated, and
meaningless, so the set of drafts in flight is not enumerable from the site.
It is obscurity, not security: anyone with the link can read it. That is the
intended level -- these are drafts of things we intend to publish, not secrets.

Usage:
    python3 scripts/preview_mark.py --branch feature/x --commit abc1234
    python3 scripts/preview_mark.py --path-only --branch feature/x
"""

import argparse
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

NOINDEX = ('<meta name="robots" content="noindex, nofollow">'
           '<meta name="referrer" content="no-referrer">')

BANNER = """<div style="position:sticky;top:0;z-index:9999;background:#7a1f1f;
color:#fff;font:600 13px/1.5 system-ui,sans-serif;padding:.5em 1em;
text-align:center">PREVIEW — branch <code>%s</code> at <code>%s</code>.
Not published; not the citable version.</div>"""


def preview_path(branch):
    """A stable, meaningless directory name for a branch.

    Ten hex characters of a digest: collision is not a practical concern for
    the number of branches this project will ever have in flight at once, and
    a longer string only makes the link harder to paste.
    """
    return hashlib.sha256(branch.encode("utf-8")).hexdigest()[:10]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--commit", default="")
    parser.add_argument("--path-only", action="store_true",
                        help="print the hashed directory and exit")
    args = parser.parse_args()

    if args.path_only:
        print(preview_path(args.branch))
        return

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s" % build)

    banner = BANNER % (args.branch, (args.commit or "unknown")[:7])
    marked = 0
    for page in build.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        if "noindex" in html:
            continue
        if "</head>" in html:
            html = html.replace("</head>", NOINDEX + "</head>", 1)
        # After the opening body tag, so it is the first thing on the page
        # whatever the theme does with the rest.
        html = re.sub(r"(<body[^>]*>)", r"\1" + banner.replace("\\", "\\\\"),
                      html, count=1)
        page.write_text(html, encoding="utf-8")
        marked += 1

    # A preview must not advertise itself to a crawler, or offer a feed that
    # would carry drafts into somebody's reader alongside the real thing.
    removed = []
    for name in ("sitemap.xml", "feed.xml", "rss.xml", "robots.txt"):
        target = build / name
        if target.exists():
            target.unlink()
            removed.append(name)
    (build / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    print("preview: %d page(s) marked noindex and bannered" % marked)
    print("         removed %s; robots.txt now disallows everything"
          % (", ".join(removed) or "nothing"))
    print("         path: /%s/" % preview_path(args.branch))


if __name__ == "__main__":
    main()
