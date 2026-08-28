#!/usr/bin/env python3
"""Add the Cloudflare Web Analytics beacon to every built page.

The same constraint as the comments embed: MyST strips ``<script>`` from page
content, and the theme's client entry calls ``hydrateRoot(document, ...)``, so
React owns the whole document and reconciles away markup it did not render.
A beacon placed statically in ``<head>`` would be removed on hydration.

So nothing is placed statically. A small bootstrap waits for hydration to
finish and then creates the beacon, which leaves React nothing to remove. It
differs from the Giscus bootstrap in two ways:

* it goes on EVERY page, not only articles, since the question is how much of
  the site is read rather than which notes draw comments;
* it needs no ``MutationObserver``. Cloudflare's beacon measures client-side
  route changes itself -- "every route change that occurs in the single-page
  app will send the measurement of the route before the route is changed to
  the beacon endpoint" -- which is exactly what this theme's client routing
  produces.

The beacon loads only on the configured hostname, so preview deployments and
the local dev server do not report into the live figures.

Configuration comes from ``analytics.yml``.

Usage:
    python3 scripts/inject_analytics.py [--build _build/html]
"""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = "uwtn-analytics-bootstrap"
BEACON = "https://static.cloudflareinsights.com/beacon.min.js"


def load_config(path=None):
    config = {}
    source = path or (ROOT / "analytics.yml")
    for raw in source.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        config[key.strip()] = value.split("#")[0].strip().strip('"').strip("'")
    return config


def bootstrap(config):
    """A script that loads the beacon once React has finished hydrating."""
    return """<script id="%s">
(function () {
  var HOSTNAME = %s;
  var TOKEN = %s;

  // Preview deployments and the dev server share this build; only the real
  // site should report, or the figures include our own editing.
  if (HOSTNAME && window.location.hostname !== HOSTNAME) return;

  function attach() {
    if (document.querySelector('script[data-cf-beacon]')) return;
    var script = document.createElement("script");
    script.src = %s;
    script.defer = true;
    // set BEFORE append: the beacon reads its own tag as it executes
    script.setAttribute("data-cf-beacon", JSON.stringify({token: TOKEN}));
    document.body.appendChild(script);
  }

  // Hydration has to finish first: anything present beforehand is reconciled
  // away, because the theme hydrates the whole document rather than a root.
  // The beacon follows client-side route changes on its own from there.
  if (document.readyState === "complete") window.setTimeout(attach, 0);
  else window.addEventListener("load", function () {
    window.setTimeout(attach, 0);
  });
})();
</script>""" % (MARKER, json.dumps(config.get("hostname", "")),
                json.dumps(config["token"]), json.dumps(BEACON))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", default="_build/html")
    args = parser.parse_args()

    config = load_config()
    if config.get("enabled") != "true":
        print("analytics disabled in analytics.yml; nothing injected")
        return
    if not config.get("token"):
        sys.exit("analytics.yml is enabled but has no token")

    build = ROOT / args.build
    if not build.exists():
        sys.exit("no build at %s" % build)

    payload = bootstrap(config)
    injected = already = 0
    for page in sorted(build.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        if MARKER in text:
            already += 1
            continue
        if "</body>" not in text:
            continue
        page.write_text(text.replace("</body>", payload + "</body>", 1),
                        encoding="utf-8")
        injected += 1

    print("analytics beacon added to %d page(s)%s"
          % (injected, ", %d already had it" % already if already else ""))
    # Re-running over a finished build is a no-op, not a failure; a build
    # with no page to inject at all is the layout having moved.
    if injected == 0 and already == 0:
        sys.exit("nothing was injected -- the build layout has changed")


if __name__ == "__main__":
    main()
