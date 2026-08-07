#!/usr/bin/env python3
"""Add Giscus to article pages, after the build.

MyST strips ``<script>`` from page content and from theme parts, so the embed
has to be added to the built HTML. Doing that naively does not work: the
theme's client entry calls ``hydrateRoot(document, ...)``, so React owns the
whole document and reconciles away markup it does not know about -- which is
what removed an inlined stylesheet from ``<head>``.

The way round it is to add nothing to the page *statically*. A small bootstrap
script waits until hydration has finished and only then builds the Giscus
container and loads the widget. There is nothing for React to remove, because
nothing was there when it hydrated.

Two further details make it hold up:

* The theme routes on the client, so moving between articles never reloads the
  page. A ``MutationObserver`` notices the new article and re-attaches.
* Giscus is inserted *after* the existing discussion block, which stays put. If
  the widget is blocked, offline or fails, the reader still has the link.

Configuration comes from ``giscus.yml``.

Usage:
    python3 scripts/inject_comments.py [--build _build/html]
"""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = "uwtn-giscus-bootstrap"


def load_config():
    config = {}
    for raw in (ROOT / "giscus.yml").read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        config[key.strip()] = value.split("#")[0].strip()
    return config


def bootstrap(config):
    """A script that attaches Giscus once React has finished hydrating."""
    settings = {
        "repo": config["repo"],
        "repoId": config["repo_id"],
        "category": config["category"],
        "categoryId": config["category_id"],
        "mapping": config.get("mapping", "specific"),
        "reactionsEnabled": "1" if config.get("reactions_enabled") == "true" else "0",
        "emitMetadata": "0",
        "inputPosition": "top",
        "theme": config.get("theme", "preferred_color_scheme"),
        "lang": "en",
    }
    return """<script id="%s">
(function () {
  var SETTINGS = %s;
  var HOST = "uwtn-giscus";

  function slugOf() {
    var parts = window.location.pathname.split("/").filter(Boolean);
    return parts.length ? parts[parts.length - 1] : "";
  }

  function attach() {
    var anchor = document.querySelector(".uwtn-discuss");
    if (!anchor) return;                       // not an article page
    var existing = document.getElementById(HOST);
    if (existing && existing.dataset.term === slugOf()) return;   // already right
    if (existing) existing.remove();           // client-side navigation

    var host = document.createElement("div");
    host.id = HOST;
    host.className = "uwtn-comments";
    host.dataset.term = slugOf();

    var script = document.createElement("script");
    script.src = "https://giscus.app/client.js";
    script.async = true;
    script.crossOrigin = "anonymous";
    Object.keys(SETTINGS).forEach(function (key) {
      script.setAttribute("data-" + key.replace(/[A-Z]/g, function (c) {
        return "-" + c.toLowerCase();
      }), SETTINGS[key]);
    });
    script.setAttribute("data-term", slugOf());
    host.appendChild(script);
    anchor.parentNode.insertBefore(host, anchor.nextSibling);
  }

  // Hydration has to finish first: anything present beforehand is reconciled
  // away, because the theme hydrates the whole document rather than a root.
  function start() { window.setTimeout(attach, 0); }
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start);

  // The theme routes on the client, so a new article never reloads the page.
  // Debounced: Giscus mutates the DOM itself when it inserts its frame, and an
  // undebounced observer would run on every one of those.
  var pending = null;
  new MutationObserver(function () {
    if (pending) return;
    pending = window.setTimeout(function () { pending = null; attach(); }, 150);
  }).observe(document.body, { childList: true, subtree: true });
})();
</script>""" % (MARKER, json.dumps(settings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default="_build/html")
    args = parser.parse_args()

    config = load_config()
    if config.get("enabled") != "true":
        print("comments disabled in giscus.yml; nothing injected")
        return

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s" % build)

    payload = bootstrap(config)
    slugs = {p.parent.name for p in (ROOT / "articles").glob("*/*.md")}

    injected = 0
    for page in sorted(build.rglob("index.html")):
        if page.parent.name not in slugs:
            continue
        text = page.read_text(encoding="utf-8")
        if MARKER in text or "</body>" not in text:
            continue
        page.write_text(text.replace("</body>", payload + "</body>", 1), encoding="utf-8")
        injected += 1

    print("Giscus bootstrap added to %d article page(s)" % injected)
    if injected == 0:
        sys.exit("nothing was injected -- the build layout has changed")


if __name__ == "__main__":
    main()
