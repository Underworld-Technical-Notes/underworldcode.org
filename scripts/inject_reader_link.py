#!/usr/bin/env python3
"""Point the theme's PDF download at the reader page.

The article page carries the theme's own Downloads menu, whose PDF entry links
straight at the fingerprinted export under ``/build/``. Clicking it hands the
reader a file. The site has somewhere better to send them -- ``/<slug>/read/``,
which shows the PDF embedded and offers the download and the markdown source as
buttons -- so the entry is rewritten to go there.

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
  function slugOf() {
    var parts = window.location.pathname.split("/").filter(Boolean);
    return parts.length ? parts[parts.length - 1] : "";
  }

  function retarget() {
    var slug = slugOf();
    if (!slug || slug === "read") return;
    var links = document.querySelectorAll('a[href^="/build/"][href$=".pdf"]');
    for (var i = 0; i < links.length; i++) {
      links[i].setAttribute("href", "/" + slug + "/read/");
      links[i].removeAttribute("download");     // it is a page now, not a file
    }
  }

  // After hydration, like the comments bootstrap: anything done earlier is undone.
  function start() { window.setTimeout(retarget, 0); }
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start);

  // The menu renders when it is opened, and the theme routes on the client, so
  // the links appear and change without a reload. Debounced: retarget mutates
  // the DOM itself.
  var pending = null;
  new MutationObserver(function () {
    if (pending) return;
    pending = window.setTimeout(function () { pending = null; retarget(); }, 120);
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
