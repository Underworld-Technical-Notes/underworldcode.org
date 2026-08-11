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
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

NOINDEX = ('<meta name="robots" content="noindex, nofollow">'
           '<meta name="referrer" content="no-referrer">')

# The banner is built by script AFTER hydration, and re-attached when the theme
# routes to another page. Written into the markup instead it appeared for a
# fraction of a second and vanished: the theme calls hydrateRoot(document, ...),
# so React owns the whole document and reconciles away anything it does not know
# about -- including a <style> in <head>. scripts/inject_comments.py hit this
# first and its docstring says so; this made the same mistake anyway.
DISCUSS_NOTICE = "Discussion will be available after publication."

BANNER = """<script id="uwtn-preview-banner">
(function () {
  var TEXT = %s;
  var NOTICE = %s;
  var ID = "uwtn-preview-bar";

  function banner() {
    if (document.getElementById(ID)) return;
    var bar = document.createElement("div");
    bar.id = ID;
    bar.textContent = TEXT;
    bar.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99999;" +
      "background:#7a1f1f;color:#fff;font:600 13px/1.6 system-ui,sans-serif;" +
      "padding:.45em 1em;text-align:center;letter-spacing:.01em";
    document.body.appendChild(bar);
    document.documentElement.style.scrollPaddingTop = "2.6em";
  }

  // The block has to be rewritten in the DOM rather than in the markup: it is
  // in the page TWICE, once as HTML and once as JSON in the hydration payload,
  // and React re-renders from the JSON. A string replacement in the built file
  // is undone the moment the page becomes interactive.
  function discussion() {
    var body = document.querySelector(".uwtn-discuss-body");
    if (body && body.textContent !== NOTICE) body.textContent = NOTICE;
    var links = document.querySelector(".uwtn-discuss-links");
    if (links) links.remove();
  }

  function attach() { banner(); discussion(); }

  function start() { window.setTimeout(attach, 0); }
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start);

  // Client-side routing replaces the page without reloading it.
  var pending = null;
  new MutationObserver(function () {
    if (pending) return;
    pending = window.setTimeout(function () { pending = null; attach(); }, 150);
  }).observe(document.body, { childList: true, subtree: true });
})();
</script>"""


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

    banner = BANNER % (
        json.dumps("PREVIEW — %s at %s. Not published; not the citable version."
                   % (args.branch, (args.commit or "unknown")[:7])),
        json.dumps(DISCUSS_NOTICE))

    marked, unhooked = 0, 0
    for page in build.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        if "noindex" in html:
            continue
        if "</head>" in html:
            html = html.replace("</head>", NOINDEX + "</head>", 1)

        # Giscus never loads on a preview. It keys a thread on the article slug,
        # so a preview would open REAL discussions on the repository for notes
        # that are not published -- and a thread somebody has replied to cannot
        # be tidily withdrawn. This one IS a safe string removal: the bootstrap
        # is a script tag added after the build, so it is not in the hydration
        # payload and React will not put it back.
        if 'id="uwtn-giscus-bootstrap"' in html:
            html = re.sub(r'<script id="uwtn-giscus-bootstrap">.*?</script>', "",
                          html, flags=re.S)
            unhooked += 1

        html = html.replace("</body>", banner.replace("\\", "\\\\") + "</body>", 1)
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
    print("         giscus removed from %d page(s); discussion replaced with a notice"
          % unhooked)
    print("         removed %s; robots.txt now disallows everything"
          % (", ".join(removed) or "nothing"))
    print("         path: /%s/" % preview_path(args.branch))


if __name__ == "__main__":
    main()
