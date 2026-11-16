#!/usr/bin/env python3
"""Put the funding acknowledgement on every Underworld3 note.

AuScope and NCRIS fund the project, and a note about the code should say so --
in the archival PDF as much as on the page, because the PDF is what outlives
the site and what a funder's reporting will eventually be pointed at.

Three of the Underworld3 notes carried it and eight did not, which is what
happens when an acknowledgement is a thing an author remembers rather than a
thing the build guarantees.

**Which notes.** Those listed in `acknowledgements.yml`, which names them
explicitly rather than guessing from the text. A note that merely mentions
Underworld3 is not necessarily work the project funded, and claiming funding
that did not happen is worse than omitting one that did.

**Computing time.** Notes listed in `acknowledgements-nci.yml` also acknowledge
the NCI merit allocations (the National Computational Merit Allocation Scheme
and the ANU Merit Allocation Scheme), which are granted year by year. That list
is checked at each allocation round: a note from a year without an allocation
does not go on it.

Idempotent: the block is recognised by its own marker and replaced, so running
this twice changes nothing and editing the wording here updates every note.

Usage:
    python3 scripts/acknowledgement.py [--check]
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"

MARKER = "<!-- uwtn-acknowledgement -->"

TEXT = (
    "*The Underworld project is supported by AuScope and the Australian "
    "Government through the National Collaborative Research Infrastructure "
    "Strategy (NCRIS). Source code:* "
    "[*github.com/underworldcode/underworld3*]"
    "(https://github.com/underworldcode/underworld3)"
)

# Merged from the two schemes' required wordings (NCMAS and ANU MAS, as given
# by Louis Moresi, 2026-11-16).
NCI_TEXT = (
    "*This research was supported by the Australian Government's National "
    "Collaborative Research Infrastructure Strategy (NCRIS), with access to "
    "computational resources provided by the National Computational "
    "Infrastructure (NCI Australia) through the National Computational Merit "
    "Allocation Scheme and the ANU Merit Allocation Scheme.*"
)

# The surrounding blank lines are part of what gets removed. Without them the
# rewrite is not idempotent: it strips the block, leaves the whitespace that
# framed it, and adds its own on the way back in, so eight articles grew two
# blank lines on EVERY build. Nothing breaks and the diff never stops.
BLOCK = re.compile(r"\n*" + re.escape(MARKER) + r".*?" + re.escape(MARKER) + r"\n*", re.S)

# Three notes already say this, in the author's own words. Those are LEFT
# ALONE: the first version of this script tried to replace them with a regex
# spanning from the phrase to the next "underworld3", which swallowed a
# paragraph and half an equation on the way past. An acknowledgement that is
# already there does not need improving.


def articles_to_credit(name="acknowledgements.yml"):
    """Slugs from a list file at the repository root."""
    path = ROOT / name
    if not path.exists():
        return []
    slugs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("- "):
            slugs.append(line[2:].strip())
    return slugs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    project = articles_to_credit()
    nci = articles_to_credit("acknowledgements-nci.yml")
    changed, missing = 0, []
    for slug in project + [s for s in nci if s not in project]:
        source = ARTICLES / slug / ("%s.md" % slug)
        if not source.exists():
            sys.exit("an acknowledgements list names %s, which does not exist" % slug)
        text = source.read_text(encoding="utf-8")

        # The author's own words, outside any generated block, stand: such a
        # note gets only the NCI sentence, if it is on that list.
        own_words = "NCRIS" in BLOCK.sub("\n\n", text)
        parts = (([TEXT] if slug in project and not own_words else [])
                 + ([NCI_TEXT] if slug in nci else []))
        if not parts:
            continue
        block = "%s\n\n%s\n\n%s" % (MARKER, "\n\n".join(parts), MARKER)
        stripped = BLOCK.sub("\n\n", text).rstrip() + "\n"

        # Before the discussion block, which is web-only and belongs last.
        discuss = stripped.find('<div class="uwtn-discuss"')
        if discuss >= 0:
            new = "%s\n\n%s\n\n%s" % (stripped[:discuss].rstrip(), block,
                                      stripped[discuss:])
        else:
            new = stripped.rstrip() + "\n\n" + block + "\n"

        if new != text:
            missing.append(slug)
            if not args.check:
                source.write_text(new, encoding="utf-8")
                changed += 1

    if args.check:
        if missing:
            sys.exit("%d note(s) missing the acknowledgement: %s"
                     % (len(missing), ", ".join(missing)))
        print("every Underworld3 note carries the acknowledgement")
        return
    print("acknowledgement written into %d note(s)" % changed)


if __name__ == "__main__":
    main()
