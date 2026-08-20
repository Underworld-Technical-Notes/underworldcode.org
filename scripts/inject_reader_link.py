#!/usr/bin/env python3
"""Put a visible PDF link on an article, and send the theme's download to it.

Two things, because the theme gives a reader only one way to the PDF and it is
not a visible one: an entry inside the Downloads menu behind the icon in the
frontmatter row. Both now lead to ``/<slug>/read/``, which shows the PDF embedded
and offers the file and the markdown source as buttons.

* **A "PDF" link is added to the frontmatter badge row**, beside the licence
  badge, so there is something to click without opening a menu first.
* **The menu entry is intercepted at click time.** The theme renders that menu
  from its hydration payload only when it is opened, so the anchor does not
  exist to be rewritten until then; a rewrite watching for it races the reader's
  second click. Catching the click instead has no such race.

Rewritten in the browser rather than in the HTML, for the same reason as the
comments (see ``inject_comments.py``): the theme calls ``hydrateRoot(document,
...)``, so React owns the document and reconciles away markup it did not render.
Anything changed before hydration is changed back.

Only anchors pointing INTO ``/build/`` are touched. That is the theme's export
path and nothing else uses it, so a PDF linked from an article's own prose --
which points at ``/<slug>/<slug>.pdf`` or off-site -- is left alone.

Usage:
    python3 scripts/inject_reader_link.py [--build _build/html]
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = "uwtn-reader-link"

SCRIPT = """<script id="%s">
(function () {
  var CLASS = "uwtn-pdf-link";

  function readerHref() {
    // Built from the CURRENT path, not from "/" + slug: the preview site serves
    // the whole site from a hashed subdirectory, and an absolute path would walk
    // out of it to the domain root.
    var path = window.location.pathname.replace(/\/+$/, "");
    if (!path || /\/read$/.test(path)) return null;
    return path + "/read/";
  }

  // 1. A visible link in the frontmatter badge row, beside the licence badge.
  function addBadge() {
    var href = readerHref();
    if (!href) return;
    var row = document.querySelector(".myst-fm-block-badges");
    if (!row) return;                                  // not an article page
    var existing = row.querySelector("." + CLASS);
    if (existing) { existing.setAttribute("href", href); return; }
    var link = document.createElement("a");
    link.className = CLASS;
    link.setAttribute("href", href);
    link.setAttribute("aria-label", "Read the archival PDF");
    link.textContent = "PDF";
    row.insertBefore(link, row.firstChild);
  }

  // 2. The theme's Downloads menu. Its entries are rendered from the hydration
  //    payload only when the menu opens, so there is nothing to rewrite until
  //    then -- and a rewrite that waits for them races the reader's next click.
  //    Catching the click is exact.
  document.addEventListener("click", function (event) {
    var anchor = event.target && event.target.closest
      ? event.target.closest('a[href*="/build/"][href$=".pdf"]') : null;
    if (!anchor) return;
    var href = readerHref();
    if (!href) return;
    event.preventDefault();
    window.location.href = href;
  }, true);                                            // capture: before the theme

  // After hydration, like the comments bootstrap: anything done earlier is undone.
  function start() { window.setTimeout(addBadge, 0); }
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start);

  // The theme routes on the client, so a new article never reloads the page.
  var pending = null;
  new MutationObserver(function () {
    if (pending) return;
    pending = window.setTimeout(function () { pending = null; addBadge(); }, 120);
  }).observe(document.body, { childList: true, subtree: true });
})();
</script>""" % MARKER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    args = parser.parse_args()

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s -- run `myst build --html` first" % build)

    touched = 0
    for page in build.rglob("index.html"):
        html = page.read_text(encoding="utf-8")
        if MARKER in html or "</body>" not in html:
            continue
        page.write_text(html.replace("</body>", SCRIPT + "</body>", 1),
                        encoding="utf-8")
        touched += 1
    print("reader link wired into %d page(s)" % touched)


if __name__ == "__main__":
    main()
