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
# Greedy to the end of the file, deliberately. The block is always appended
# last, and it now contains nested divs -- a non-greedy `.*?</div>` stopped at
# the first inner closing tag, so every remove/add cycle left a fragment behind
# and appended a fresh block on top of it. Articles accumulated the remains of
# earlier versions, including a superseded iframe widget.
DISCUSS_BLOCK = re.compile(
    r'\n*<div class="uwtn-(?:discuss|comments)">.*\Z', re.S)

REPO_URL = "https://github.com/Underworld-Technical-Notes/underworldcode.org"
DISCUSS_URL = REPO_URL + "/discussions/new?category=general&title=%s"
SEARCH_URL = REPO_URL + "/discussions?discussions_q=%s"



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
    """The discussion block: where the conversation is, and how to join it.

    Always the link form. Giscus itself is attached after the build by
    scripts/inject_comments.py, which loads the real client script once React
    has hydrated -- it cannot come through the markdown, because MyST strips
    <script>. This block stays beneath the widget as the fallback: if Giscus is
    blocked, offline or broken, the reader still has somewhere to go.

    An earlier version emitted a Giscus iframe here when comments were enabled.
    That left two embeds on the page, and the stale one offered a sign-in that
    could never work, because GitHub cannot be framed.
    """
    import urllib.parse
    term = urllib.parse.quote(path.stem)
    return ('<div class="uwtn-discuss">'
            '<div class="uwtn-discuss-head">Comments</div>'
            '<div class="uwtn-discuss-body">Discussion of these notes happens in '
            'GitHub Discussions, so it stays with the source and is searchable '
            'alongside it.</div>'
            '<div class="uwtn-discuss-links">'
            '<a href="%s">Read the discussion</a>'
            '<a href="%s">Start one</a>'
            '</div></div>' % (SEARCH_URL % term, DISCUSS_URL % term))


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
