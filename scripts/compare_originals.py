#!/usr/bin/env python3
"""Compare the drafted originals against what Ghost actually published.

The recent posts were drafted as markdown in the underworld3 repository
(``publications/blog-posts/``) and then published through Ghost. Neither copy
is uniformly the later one: some posts were edited in Ghost after the repo copy
was last touched, others were tidied in the repo after publication.

That matters because the published Ghost version is the **version of record** --
it is what the registered DOI resolves to. A migration must not quietly
substitute an unpublished draft for it. This reports, per article, which side
has content the other lacks, so each can be judged rather than assumed.

Usage:
    python3 scripts/compare_originals.py --repo ~/+Underworld/underworld3-pixi
"""

import argparse
import difflib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def resolve_sources(repo):
    """Where the drafted sources live.

    Defaults to the copy preserved in ``sources/``. The originals lived only as
    uncommitted edits in a worktree, so nothing here depends on a checkout
    outside this repository.
    """
    if repo:
        candidate = pathlib.Path(repo).expanduser() / "publications" / "blog-posts"
        if candidate.exists():
            return candidate
    return ROOT / "sources" / "blog-posts"

# original filename in publications/blog-posts -> published Ghost slug
PAIRS = {
    "sympy-to-c-pipeline.md": "how-underworld3-turns-sympy-into-c",
    "physical-units.md": "physical-units-in-computational-geodynamics",
    "finding-particles.md": "finding-particles-in-a-distributed-unstructured-mesh",
    "constitutive-models.md": "constitutive-models-in-symbolic-form",
    "arrays-in-sync.md": "mesh-variables-and-petsc-vectors-keeping-arrays-in-sync",
    "time-derivatives.md": "symbolic-time-derivatives-in-underworld3",
    "particles-as-symbols.md": "particles-in-underworld3",
    "uw2-to-uw3-journey.md": "our-journey-from-underworld2-to-underworld3",
    "ai-development-strategy.md": "ai-and-scientific-software-what-we-learned-rebuilding-underworld3",
}


def normalise(block):
    block = " ".join(block.split())
    block = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", block)      # link text only
    block = re.sub(r"</?[a-z][^>]*>", " ", block)                  # stray tags
    block = re.sub(r"[*`_]", "", block)
    block = re.sub(r"\\", "", block)                              # \mathbf vs mathbf
    block = re.sub(r"[{}$]", "", block)
    block = re.sub(r"[^a-zA-Z0-9 ]", " ", block)                   # punctuation drift
    return " ".join(block.split()).lower()


def sentences(paras):
    out = []
    for para in paras:
        for s in re.split(r"(?<=[a-z0-9])\s+(?=[a-z])", para) if False else [para]:
            out.extend(x.strip() for x in re.split(r"\s*\.\s+", s) if len(x.split()) >= 5)
    return out


def md_paragraphs(text):
    """Prose from the drafted markdown: no front matter, code or directives."""
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"^#.*$", "", text, flags=re.M)
    out = []
    for block in re.split(r"\n\s*\n", text):
        block = normalise(block)
        if len(block.split()) >= 8:
            out.append(block)
    return out


def html_paragraphs(html):
    """Prose from the published Ghost HTML.

    Code and figures are removed first. Ghost's `plaintext` field cannot be used
    for this: it flattens code blocks into the prose with no marker, so a
    comparison against fenced markdown reports every code listing as a
    difference.
    """
    html = re.sub(r"<pre.*?</pre>", "", html or "", flags=re.S)
    html = re.sub(r"<figure.*?</figure>", "", html, flags=re.S)
    html = re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", "", html, flags=re.S)
    # Ghost merges what were separate markdown paragraphs into one <p> joined by
    # <br>, so paragraph counts are not comparable until these are split back
    # out. 155 of them across the corpus.
    html = re.sub(r"<br\s*/?>", " ", html)
    out = []
    for block in re.findall(r"<p[^>]*>(.*?)</p>|<li[^>]*>(.*?)</li>", html, flags=re.S):
        text = normalise(html_unescape(block[0] or block[1]))
        if len(text.split()) >= 8:
            out.append(text)
    return out


def html_unescape(text):
    import html as _html
    return _html.unescape(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="path to the underworld3 checkout")
    parser.add_argument("--show", type=int, default=2, help="sample paragraphs to print")
    args = parser.parse_args()

    source = resolve_sources(args.repo)
    if not source.exists():
        sys.exit("no blog-posts directory at %s" % source)

    ghost = {}
    export = ROOT / "inventory" / "ghost-export" / "posts.json"
    for post in json.loads(export.read_text(encoding="utf-8"))["posts"]:
        ghost[post["slug"]] = post

    print("%-30s %5s %5s  %5s  %s"
          % ("original", "orig", "ghost", "same", "verdict"))
    print("-" * 96)
    report = []

    for filename, slug in sorted(PAIRS.items()):
        original = source / filename
        if not original.exists() or slug not in ghost:
            print("%-30s  MISSING" % filename)
            continue

        orig_paras = md_paragraphs(original.read_text(encoding="utf-8"))
        published = ghost[slug]
        ghost_paras = html_paragraphs(published.get("html") or "")

        # Compare sentences, not paragraphs. Ghost re-chunks paragraphs (it
        # merges them around <br>), so paragraph alignment reports formatting
        # as content. Sentences survive re-chunking.
        orig_s, ghost_s = sentences(orig_paras), sentences(ghost_paras)
        matcher = difflib.SequenceMatcher(None, orig_s, ghost_s)
        ratio = matcher.ratio()
        only_orig = [s for s in orig_s if s not in set(ghost_s)]
        only_ghost = [s for s in ghost_s if s not in set(orig_s)]

        if ratio > 0.995:
            verdict = "identical prose"
        elif not only_ghost:
            verdict = "repo is a superset -- edited after publication"
        elif not only_orig:
            verdict = "Ghost is a superset -- repo copy is a stale draft"
        else:
            verdict = "both diverge -- read before choosing"

        print("%-30s %5d %5d  %4.0f%%  %s"
              % (filename[:30], len(orig_s), len(ghost_s), 100 * ratio, verdict))
        report.append({
            "original": filename, "slug": slug, "verdict": verdict,
            "similarity": round(ratio, 4),
            "only_in_original": only_orig, "only_in_ghost": only_ghost,
        })

        for label, items in (("only in repo ", only_orig), ("only in ghost", only_ghost)):
            for para in items[:args.show]:
                print("      %s: %s%s" % (label, para[:96], "..." if len(para) > 96 else ""))

    (ROOT / "inventory" / "original-vs-published.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print("\nfull detail: inventory/original-vs-published.json")


if __name__ == "__main__":
    main()
