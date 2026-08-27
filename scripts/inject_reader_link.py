#!/usr/bin/env python3
"""Give an article one visible route to its PDF, and remove the theme's.

The theme's own route is an entry inside a Downloads menu, behind an icon in the
frontmatter row: a reader has to know it is there. It is replaced by a visible
"PDF" link in that row, which goes to ``/<slug>/read/`` -- the PDF embedded, with
the file and the markdown source as buttons. Both of the things the menu offered
are on that page, so the menu is removed rather than left as a second, quieter
way to the same two files.

* **The menu is dropped at its source.** The theme renders it from the
  ``exports`` array in the page's hydration payload; emptying that array means
  there is nothing to render after hydration. The button MyST already rendered
  into the static HTML is deleted with it -- React would reconcile it away, but
  not before it had been on screen, and never at all for a reader without
  Javascript.
* **A "PDF" link is added to the frontmatter badge row**, beside the licence
  badge, after hydration -- markup added before it is reconciled away.
* **A click on any surviving export link is caught** in the capture phase and
  sent to the reader page. Belt and braces: the payload edit should leave none,
  and if a theme upgrade renders one from somewhere else it still leads to the
  right place rather than to a bare file.

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
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = "uwtn-reader-link"
# The theme's Downloads menu is rendered from this array in the hydration
# payload. Emptied rather than deleted: the key is what the theme reads.
EXPORTS = re.compile(r'"exports":\[(?!\])(?:[^][]|\[[^]]*\])*?\](?=[,}])')

SCRIPT = r"""<script id="%s">
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


def drop_downloads_button(html):
    """Remove the server-rendered Downloads button from the frontmatter row.

    Located by its own accessible label rather than by a class: the theme's
    classes are utility soup and its element ids are generated per render, but
    the button carries ``<span class="sr-only">Downloads</span>`` because a
    screen reader needs it to. Buttons do not nest, so the first closing tag
    after the opening one is the right one.
    """
    label = '<span class="sr-only">Downloads</span>'
    at = html.find(label)
    if at < 0:
        return html, False
    start = html.rfind("<button", 0, at)
    if start < 0:
        return html, False
    end = html.find("</button>", at)
    if end < 0:
        return html, False
    return html[:start] + html[end + len("</button>"):], True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    args = parser.parse_args()

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s -- run `myst build --html` first" % build)

    touched, emptied, buttons = 0, 0, 0
    for page in build.rglob("index.html"):
        html = page.read_text(encoding="utf-8")
        if MARKER in html or "</body>" not in html:
            continue
        # Empty the exports the Downloads menu is rendered from. Non-greedy to
        # the closing bracket that is followed by a comma or a brace, so it
        # stops at the array and not at the end of the payload.
        html, count = EXPORTS.subn('"exports":[]', html)
        emptied += 1 if count else 0
        html, dropped = drop_downloads_button(html)
        buttons += 1 if dropped else 0
        page.write_text(html.replace("</body>", SCRIPT + "</body>", 1),
                        encoding="utf-8")
        touched += 1
    print("reader link wired into %d page(s); theme downloads dropped from %d "
          "payload(s) and %d button(s)" % (touched, emptied, buttons))


if __name__ == "__main__":
    main()
