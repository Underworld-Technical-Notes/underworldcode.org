#!/usr/bin/env python3
"""House-style hints for a note in draft.

The conventions in CONTRIBUTING.md ("How the notes read") that can be
checked mechanically. It reports; it does not judge, and it does not fail
a build unless asked. Several checks are densities rather than rules,
because whether a document should be using them is the author's call and
not something a regular expression can decide.

Every hint is a prompt to look, so each one names the convention it comes
from and quotes the line. Anyone writing for these notes, working from a
draft or from someone else's edit, gets the same report.

Usage:
    python3 scripts/check_style.py                 # every article
    python3 scripts/check_style.py articles/x/x.md # one
    python3 scripts/check_style.py --strict        # exit 1 if anything found
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --- announcing the writing, rather than writing plainly -------------------
ANNOUNCING = re.compile(
    r"\b(written|put|stated|speaking)\s+(plainly|honestly|frankly|simply)\b"
    r"|\bthe honest (framing|version|answer)\b"
    r"|\bto be (honest|clear|frank)\b"
    r"|\bin (truth|all honesty)\b"
    r"|\bthe truth is\b",
    re.I)

# --- withholding a point in order to reveal it -----------------------------
WITHHOLDING = re.compile(
    r"\bthe (thing|part|bit) that matters\b"
    r"|\bthe word to notice\b"
    r"|\bthe (useful|interesting|important|real) (part|point|question|bit)\b"
    r"|\b(not entirely|far from) obvious\b"
    r"|\bworth knowing about\b"
    r"|\bhere is the (thing|catch|rub)\b"
    r"|\bthe (key|real) (insight|reason|answer)\b"
    r"|\bwhat(?:'s| is) really going on\b"
    r"|\bthe punchline\b"
    r"|\band then the part\b",
    re.I)

# --- not-X-but-Y; one is a correction, five is a mannerism -----------------
ANTITHESIS = re.compile(
    r"\bis not (a|an|the) \b"
    r"|\bare not (a|an|the) \b"
    r"|\bnot just\b|\bnot only\b|\bnot merely\b"
    r"|\brather than (a|an|the)\b",
    re.I)
# the corpus median is 0, so this is a count with a density guard rather
# than a density: three in a note is a rhythm, three in a monograph is not
ANTITHESIS_MIN = 3
ANTITHESIS_PER_1000 = 1.0

SECOND_PERSON = re.compile(r"\b(you|your|yours|yourself)\b", re.I)
# calibrated on the corpus: notes sit at 0-8 per 1000 words, step-by-step
# install guides legitimately reach 25-62. Flag well above the notes band.
SECOND_PERSON_PER_1000 = 12.0

FIRST_SINGULAR = re.compile(r"\bI\b|\bmy\b|\bmine\b")
FIRST_PLURAL = re.compile(r"\b(we|our|ours|us)\b", re.I)

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
# A leading label -- "UWTN 2026-014: ...", "Stage 2: ...", "Gadi: ..." -- is
# what a colon is for, and so is a trailing colon introducing a list or a code
# block ("Ubuntu:"). Neither is the construction under discussion.
LABEL_PREFIX = re.compile(
    r"^(UWTN\s*[\d-]+|Part\s+\w+|Appendix\s*\w*|Stage\s+\d+|"
    r"Step\s+\d+|Table\s*\d*|Figure\s*\d*|\d+|"
    r"(A\s+\w+\s+)?Examples?|[A-Z][a-z0-9_]*)\s*$")
# at least a third of the headings, and at least this many, before it is a
# habit rather than a heading
COLON_HEADING_SHARE = 1 / 3
COLON_HEADING_MIN = 3


def prose(text):
    """The article body with front matter, code and HTML removed.

    Returns (lines, words) where lines keep their original 1-based numbers
    so a hint can point at the source.
    """
    lines = text.splitlines()
    out, in_front, in_code = [], False, False
    for i, line in enumerate(lines, 1):
        if i == 1 and line.strip() == "---":
            in_front = True
            out.append((i, ""))
            continue
        if in_front:
            if line.strip() == "---":
                in_front = False
            out.append((i, ""))
            continue
        if line.lstrip().startswith("```"):
            in_code = not in_code
            out.append((i, ""))
            continue
        out.append((i, "" if in_code else re.sub(r"<[^>]+>", " ", line)))
    words = sum(len(t.split()) for _i, t in out)
    return out, words


def check(path):
    text = path.read_text(errors="ignore")
    lines, words = prose(text)
    hints = []
    headings, colon_headings = [], []

    def add(rule, lineno, quote, note):
        hints.append((rule, lineno, quote.strip()[:78], note))

    for lineno, line in lines:
        m = HEADING.match(line)
        if m:
            title = m.group(2)
            headings.append((lineno, title))
            if "!" in title:
                add("heading-argues", lineno, title,
                    "an exclamation mark in a heading is always the wrong "
                    "instinct")
            # not elif: an excited heading is usually an instance of the same
            # habit, and should be counted in it
            if ":" in title:
                before, after = title.split(":", 1)
                # a trailing colon introduces a list; a labelled prefix is a
                # label. Neither is "name it, then reveal the point".
                if after.strip() and not LABEL_PREFIX.match(
                        before.strip().strip("*_`")):
                    colon_headings.append((lineno, title))
            continue
        for rule, pat, note in (
            ("announcing", ANNOUNCING,
             "the prose is either plain or it is not; delete the frame and "
             "keep the sentence"),
            ("withholding", WITHHOLDING,
             "says something important is coming instead of saying it; "
             "usually deletable with no loss"),
        ):
            found = pat.search(line)
            if found:
                add(rule, lineno, line, note)

    # the objection is to the HABIT, not to any one heading: a contents list
    # where every entry names a thing and then reveals the point reads as
    # though each section is about to surprise you
    if (len(colon_headings) >= COLON_HEADING_MIN and headings
            and len(colon_headings) / len(headings) >= COLON_HEADING_SHARE):
        add("heading-habit", colon_headings[0][0],
            f"{len(colon_headings)} of {len(headings)} headings are "
            f"\"name: then the point\"",
            "e.g. " + "; ".join(t for _l, t in colon_headings[:3])
            + " — does the text after each colon NAME something, or assert "
              "it?")

    if words >= 300:
        def density(pat):
            n = sum(len(pat.findall(t)) for _i, t in lines)
            return n, n / words * 1000

        n_anti, d_anti = density(ANTITHESIS)
        if n_anti >= ANTITHESIS_MIN and d_anti >= ANTITHESIS_PER_1000:
            add("antithesis", 0, f"{n_anti} not-X-but-Y constructions "
                f"({d_anti:.1f} per 1000 words)",
                "one is a useful correction; a pattern reads as arguing with "
                "a sceptic who is not in the room")

        n_you, d_you = density(SECOND_PERSON)
        if d_you > SECOND_PERSON_PER_1000:
            add("second-person", 0,
                f"{n_you} second-person pronouns ({d_you:.1f} per 1000 words)",
                "right for step-by-step instructions, out of place in a note "
                "reporting a result — which is this?")

        n_i, _ = density(FIRST_SINGULAR)
        n_we, _ = density(FIRST_PLURAL)
        return hints, (words, n_i, n_we, n_you)
    return hints, (words, 0, 0, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*", type=pathlib.Path)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any hint is reported")
    ap.add_argument("--voice", action="store_true",
                    help="also print the I / we / you counts per article")
    args = ap.parse_args()

    paths = args.paths or sorted((ROOT / "articles").glob("*/*.md"))
    total = 0
    for path in paths:
        hints, (words, n_i, n_we, n_you) = check(path)
        if not hints and not args.voice:
            continue
        rel = path.relative_to(ROOT) if path.is_absolute() else path
        print(f"\n{rel}  ({words} words)")
        if args.voice:
            print(f"    voice: I/my {n_i}, we/our {n_we}, you/your {n_you}")
        for rule, lineno, quote, note in hints:
            where = f"{lineno}" if lineno else "-"
            print(f"  {where:>5}  [{rule}] {quote}")
            print(f"         {note}")
        total += len(hints)

    if total:
        print(f"\n{total} hint(s). These are the conventions in "
              f"CONTRIBUTING.md, 'How the notes read' — a prompt to look, "
              f"not a verdict.")
    else:
        print("No hints.")
    return 1 if (args.strict and total) else 0


if __name__ == "__main__":
    sys.exit(main())
