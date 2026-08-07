#!/usr/bin/env python3
"""Add or remove the visible banner block in article bodies.

The feature images kept from the Ghost posts belong on the web and not in the
archival PDF: a stock photograph on page one undercuts the point of a fixed,
citable document. But both renditions build from the same markdown.

The ``banner:`` entry in an article's front matter is the source of truth. The
visible ``<div class="uwtn-banner">`` in the body is derived from it, so it can
be removed before the Typst build and put back afterwards without losing
anything. Both directions are idempotent, so an interrupted build leaves
nothing to repair -- and ``pixi run migrate`` regenerates the articles anyway.

    python3 scripts/banner_body.py --remove    # before myst build --typst
    python3 scripts/banner_body.py --add       # after

(An earlier attempt relied on Typst dropping raw HTML. It does not: the banner
rendered on page one of every PDF.)
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"

BANNER_BLOCK = re.compile(
    r'<div class="uwtn-banner"><img src="[^"]*" alt="">'
    r'(?:<div class="uwtn-credit">.*?</div>)?</div>\n\n', re.S)

# The discussion link is web-only for the same reason as the banner: it is a
# live affordance, and an archival PDF should not invite a reader to click.
DISCUSS_BLOCK = re.compile(
    r'\n*<div class="uwtn-(?:discuss|comments)">.*?</div>\n*', re.S)

DISCUSS_URL = ("https://github.com/Underworld-Technical-Notes/underworldcode.org"
               "/discussions/new?category=general&title=%s")


def giscus_config():
    """Settings from giscus.yml, or None if comments are not enabled."""
    path = ROOT / "giscus.yml"
    if not path.exists():
        return None
    config = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        config[key.strip()] = value.split("#")[0].strip()
    return config if config.get("enabled") == "true" else None


def banner_from_frontmatter(text):
    match = re.search(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    found = re.search(r"^banner:\s*(\S+)\s*$", match.group(1), re.M)
    return found.group(1) if found else None


def credit_from_metadata(directory):
    """The photographer attribution, from the article's metadata.yml.

    Unsplash's licence asks for the credit wherever the photograph appears, so
    rebuilding the banner has to rebuild the credit with it.
    """
    path = directory / "metadata.yml"
    if not path.exists():
        return None
    found = re.search(r'^banner_credit:\s*"(.*)"\s*$', path.read_text(encoding="utf-8"), re.M)
    if not found:
        return None
    return found.group(1).replace('\\"', '"')


def discuss_block(path):
    """A link to open a GitHub Discussion about this note.

    Giscus would embed the thread in the page, and everything it needs is
    recorded in giscus.yml -- but MyST strips <script> from page content and
    from theme parts alike, so its official embed cannot be placed without
    forking the theme. A link needs no JavaScript, keeps the conversation on
    GitHub either way, and cannot break the way an embedded widget can.
    """
    import urllib.parse
    slug = path.stem
    config = giscus_config()
    if config:
        # Giscus's iframe widget. Its <script> cannot be used: MyST strips
        # script from content and from theme parts, and the theme hydrates the
        # whole document so post-build injection is reconciled away.
        query = urllib.parse.urlencode({
            "repo": config["repo"], "repoId": config["repo_id"],
            "category": config["category"], "categoryId": config["category_id"],
            "mapping": config.get("mapping", "specific"), "term": slug,
            "reactionsEnabled": "1" if config.get("reactions_enabled") == "true" else "0",
            "emitMetadata": "0", "inputPosition": "top",
            # Without origin the widget renders but cannot return a reader
            # from the GitHub sign-in, so there is no way to comment.
            "origin": "%s/%s/" % (config["site_url"].rstrip("/"), slug),
            "theme": config.get("theme", "preferred_color_scheme"), "lang": "en",
        })
        # The link stays beneath the embed. The widget is third-party and can
        # fail -- blocked, offline, signed out -- and a reader should never be
        # left with no way to respond.
        return ('<div class="uwtn-comments">'
                '<iframe src="https://giscus.app/en/widget?%s" '
                'title="Comments" loading="lazy"></iframe>'
                '<div class="uwtn-discuss-alt">'
                '<a href="%s">Or open the thread on GitHub</a></div>'
                '</div>' % (query, DISCUSS_URL % urllib.parse.quote(slug)))

    return ('<div class="uwtn-discuss">'
            '<a href="%s">Discuss this note on GitHub</a>'
            '</div>' % (DISCUSS_URL % urllib.parse.quote(slug)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add", action="store_true")
    group.add_argument("--remove", action="store_true")
    args = parser.parse_args()

    changed = 0
    for path in sorted(ARTICLES.glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        banner = banner_from_frontmatter(text)
        if not banner:
            continue

        head, sep, body = text.partition("\n---\n")
        if not sep:
            continue
        stripped = BANNER_BLOCK.sub("", body, count=1)

        stripped = DISCUSS_BLOCK.sub("\n", stripped).rstrip() + "\n"

        if args.remove:
            new_body = stripped
        else:
            credit = credit_from_metadata(path.parent)
            block = '<div class="uwtn-banner"><img src="%s" alt="">' % banner
            if credit:
                block += '<div class="uwtn-credit">%s</div>' % credit
            block += "</div>\n\n"
            new_body = block + stripped.lstrip("\n")
            new_body = new_body.rstrip() + "\n\n" + discuss_block(path) + "\n"

        if new_body != body:
            path.write_text(head + sep + new_body, encoding="utf-8")
            changed += 1

    print("banner block %s in %d article(s)"
          % ("removed" if args.remove else "added", changed))


if __name__ == "__main__":
    main()
