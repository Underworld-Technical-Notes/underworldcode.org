#!/usr/bin/env python3
"""Derive a subject vocabulary from what the articles actually say.

The tags inherited from Ghost ("Tricks of the Trade", "Underworld Code") are
blog furniture, not a subject scheme. This measures the corpus instead, so a
classification can be argued from the text rather than invented.

Two things are counted, and the difference matters:

* **Document frequency** -- how many articles use a term at all. This is what a
  facet needs: a term in one article, however often, is a topic of that article
  and not a category.
* **Term frequency** -- how often overall, which separates a passing mention
  from a subject.

Code blocks and maths are excluded: identifiers and symbols would otherwise
dominate, and they describe the software rather than the science.

A caution learned from running it: match on whole words or long phrases, not
short substrings. Probing for glaciology with ``ice`` scored 29 of 53 documents
-- it was matching device, notice, slice and practice. The narrow probe scored
one, and one was right.

Usage:
    python3 scripts/analyse_vocabulary.py [--corpus articles|ghost] [--top 40]
"""

import argparse
import collections
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

STOP = set("""
a an the and or but if then than that this these those there here of in on at to
from by for with without into over under between across through during before
after above below up down out off again further once is are was were be been
being have has had having do does did doing can could should would may might
must will shall it its it's we our us you your they them their he she his her
as so such no not only own same too very s t just also then now new use used
using uses one two three first second next last each other another any all both
few more most some many much several own way ways thing things make makes made
get gets got go goes going come comes came take takes took see sees saw look
looks looked want wants like likes need needs give gives given work works worked
what which who whom whose when where why how because while about against
i.e e.g etc via per within upon toward towards
""".split())

# Phrases worth counting as one term.
BIGRAM_KEEP = re.compile(r"^[a-z][a-z-]+ [a-z][a-z-]+$")


def prose_of(text):
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    # The banner credit is attribution, not subject matter: leaving it in put
    # "photo" and "unsplash" in the top ten.
    text = re.sub(r'<div class="uwtn-credit">.*?</div>', " ", text, flags=re.S)
    text = re.sub(r'<figcaption.*?</figcaption>', " ", text, flags=re.S)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"\$\$.+?\$\$", " ", text, flags=re.S)
    text = re.sub(r"(?<!\$)\$[^$\n]+\$(?!\$)", " ", text)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return html.unescape(text)


def tokens(text):
    words = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", text.lower())
    return [w for w in words if w not in STOP and not w.endswith("-")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", choices=["articles", "ghost"], default="articles")
    parser.add_argument("--top", type=int, default=40)
    args = parser.parse_args()

    documents = []
    if args.corpus == "articles":
        for path in sorted(ROOT.glob("articles/*/*.md")):
            documents.append((path.parent.name, prose_of(path.read_text(encoding="utf-8"))))
    else:
        export = ROOT / "inventory" / "ghost-export" / "posts.json"
        for post in json.loads(export.read_text(encoding="utf-8"))["posts"]:
            if re.match(r"^(rce(-\d+)?|sysinfo-)", post["slug"]):
                continue
            documents.append((post["slug"], prose_of(post.get("html") or "")))

    if not documents:
        sys.exit("no documents found")

    term_freq, doc_freq = collections.Counter(), collections.Counter()
    for _slug, text in documents:
        words = tokens(text)
        grams = collections.Counter(words)
        for first, second in zip(words, words[1:]):
            phrase = "%s %s" % (first, second)
            if BIGRAM_KEEP.match(phrase):
                grams[phrase] += 1
        term_freq.update(grams)
        doc_freq.update(set(grams))

    total = len(documents)
    print("corpus: %s -- %d documents\n" % (args.corpus, total))
    print("%-34s %6s %6s" % ("term", "docs", "uses"))
    print("-" * 50)
    # Rank by document frequency, then by use: a facet has to span the corpus.
    ranked = sorted(term_freq, key=lambda t: (-doc_freq[t], -term_freq[t]))
    shown = 0
    for term in ranked:
        if doc_freq[term] < max(3, total // 6) or term_freq[term] < 8:
            continue
        print("%-34s %6d %6d" % (term, doc_freq[term], term_freq[term]))
        shown += 1
        if shown >= args.top:
            break


if __name__ == "__main__":
    main()
