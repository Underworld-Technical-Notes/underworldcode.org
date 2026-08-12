#!/usr/bin/env python3
"""Cut the toc down to the notes under review, for a fast preview.

MyST builds what the toc lists. A preview of one note does not need the other
fifty-three pages, the topic pages or the standing pages -- and building them
is most of the time a preview takes: about 114 seconds of HTML against 75 of
PDFs, measured.

The sidebar then holds one entry. That is the point rather than a loss: with
one page in it there is nowhere to get lost, and this is for checking how a
note reads and renders, not for checking the site. The full preview still
exists -- the workflow builds it on every push -- so anything that needs the
site in one piece has somewhere to go.

Run after build_index.py, which generates the full toc; this replaces it.
Rewrites `index.md` too, because it is the root of the toc and MyST will not
start without it.

Usage:
    python3 scripts/preview_only.py --slugs a-note,another-note
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
sys.path.insert(0, str(ROOT / "scripts"))

TOC_BEGIN = "  # BEGIN GENERATED TOC"
TOC_END = "  # END GENERATED TOC"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slugs", required=True,
                        help="comma-separated article slugs")
    args = parser.parse_args()

    import build_index
    slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
    missing = [s for s in slugs if not (ARTICLES / s / ("%s.md" % s)).exists()]
    if missing:
        sys.exit("no such article: %s" % ", ".join(missing))
    if not slugs:
        sys.exit("nothing to preview")

    myst = ROOT / "myst.yml"
    text = myst.read_text(encoding="utf-8")
    if TOC_BEGIN not in text:
        sys.exit("myst.yml is missing the generated-toc markers")

    lines = ["  toc:", "    - file: index.md"]
    for slug in slugs:
        lines.append("    - file: articles/%s/%s.md" % (slug, slug))
    head, _, rest = text.partition(TOC_BEGIN)
    _, _, tail = rest.partition(TOC_END)
    myst.write_text("%s%s\n%s\n%s%s" % (head, TOC_BEGIN, "\n".join(lines),
                                        TOC_END, tail), encoding="utf-8")

    entries = []
    for slug in slugs:
        meta = build_index.read_yaml(ARTICLES / slug / "metadata.yml")
        entries.append(
            '<div class="uwtn-entry"><div class="uwtn-entry-text">'
            '<h2><a href="/%s/">%s</a></h2>'
            '<div class="uwtn-entry-summary">%s</div></div></div>'
            % (slug, build_index.text(str(meta.get("title") or slug)),
               build_index.text(build_index.description_of(ARTICLES / slug, slug))))

    (ROOT / "index.md").write_text(
        '---\ntitle: Preview\nsite:\n  hide_outline: true\n---\n\n'
        '<div class="uwtn-masthead"><div class="uwtn-kicker">Preview</div>'
        '<div class="uwtn-wordmark">Under review</div>'
        '<div class="uwtn-standfirst">Only the notes changed on this branch '
        'were built. The rest of the site is not here, which is why this was '
        'quick.</div></div>\n\n<div class="uwtn-feed">\n%s\n</div>\n'
        % "\n".join(entries), encoding="utf-8")

    print("toc cut to %d note(s): %s" % (len(slugs), ", ".join(slugs)))


if __name__ == "__main__":
    main()
