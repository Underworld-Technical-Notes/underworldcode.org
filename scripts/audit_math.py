#!/usr/bin/env python3
"""Find LaTeX that Ghost's editor damaged.

Ghost ate backslashes. The published `constitutive-models` shows it plainly:
the draft's ``C_{ijkl} \\, \\dot\\varepsilon_{kl}`` was published as
``C_{ijkl} , \\dot\\varepsilon_{kl}`` -- the thin space became a literal comma.

Two passes:

1. **Ground truth.** Where a drafted original exists, diff its maths against the
   published maths and catalogue precisely what changed. No guessing.
2. **Detection.** Apply that catalogue, plus a list of LaTeX command names that
   are meaningless as bare words, to every article in the corpus -- including
   the forty-five with no draft to compare against.

Reports rather than edits: a mangled equation is a content fix, and the fix
belongs in ``corrections.yml`` where it is declared and reviewable.

Usage:
    python3 scripts/audit_math.py --repo ~/+Underworld/underworld3-pixi/.claude/worktrees/blog-posts
"""

import argparse
import collections
import html
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


EXPORT = ROOT / "inventory" / "ghost-export"

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

# LaTeX commands that are meaningless as a bare word inside maths. Seeing one
# without its backslash is the signature of an editor that ate the escape.
COMMANDS = [
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
    "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "pi", "rho",
    "sigma", "tau", "upsilon", "phi", "varphi", "chi", "psi", "omega",
    "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi", "Omega",
    "nabla", "partial", "infty", "cdot", "cdots", "times", "quad", "qquad",
    "frac", "sqrt", "sum", "int", "left", "right", "mathbf", "mathrm", "boldsymbol",
    "dot", "ddot", "hat", "bar", "tilde", "vec", "approx", "neq", "leq", "geq",
    "text", "operatorname", "begin", "end", "underbrace", "overbrace",
]
BARE_COMMAND = re.compile(r"(?<![\\A-Za-z])(%s)(?![A-Za-z])" % "|".join(COMMANDS))

# A comma flanked by maths rather than separating list items: what \, becomes.
LONE_COMMA = re.compile(r"[A-Za-z0-9}\)]\s+,\s+\\?[A-Za-z\\]")


def math_spans(text):
    """Every display and inline maths span, in order.

    Inline spans are only recognised when they contain no code fence and no
    sentence-ending punctuation followed by a space: a lone ``$`` in prose or
    inside backticks otherwise pairs with the next one and swallows a whole
    sentence, which the audit then reports as suspect maths.
    """
    spans = []
    for match in re.finditer(r"\$\$(.+?)\$\$", text, re.S):
        if not is_maths(match.group(1)):
            continue          # a closing $$ paired with the next opening one
        spans.append(("display", match.group(1)))
    body = re.sub(r"\$\$.+?\$\$", " ", text, flags=re.S)
    body = re.sub(r"`[^`\n]*`", " ", body)          # inline code is not maths
    for match in re.finditer(r"(?<!\$)\$([^$\n]{2,})\$(?!\$)", body):
        span = match.group(1)
        if not is_maths(span):
            continue                                 # prose caught between dollars
        spans.append(("inline", span))
    return spans


def is_maths(span):
    """Reject a span that is plainly prose.

    A closing ``$$`` can pair with the *next* block's opening one, swallowing
    the paragraphs between them; the same happens inline when a line ends and
    the next begins with a dollar. Real maths carries almost no running English,
    so counting words outside ``\\text{}`` separates the two reliably.
    """
    prose = re.sub(r"\\(?:text|mathrm|operatorname)\{[^}]*\}", " ", span)
    prose = re.sub(r"\\[A-Za-z]+", " ", prose)
    words = re.findall(r"\b[a-z]{3,}\b", prose)
    return len(words) <= 8


def clean(span):
    span = html.unescape(span)
    span = re.sub(r"<br\s*/?>", " ", span)
    span = re.sub(r"<[^>]+>", "", span)
    return " ".join(span.split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="checkout holding publications/blog-posts")
    args = parser.parse_args()

    posts = json.loads((EXPORT / "posts.json").read_text(encoding="utf-8"))["posts"]
    published = {p["slug"]: p for p in posts}

    # ---- pass 1: ground truth from the drafts ---------------------------
    catalogue = collections.Counter()
    if args.repo:
        source = resolve_sources(args.repo)
        print("=== differences between drafted and published maths ===\n")
        for filename, slug in sorted(PAIRS.items(), key=lambda kv: kv[1]):
            draft = source / filename
            if not draft.exists() or slug not in published:
                continue
            d_spans = [clean(s) for _k, s in math_spans(draft.read_text(encoding="utf-8"))]
            p_spans = [clean(s) for _k, s in math_spans(published[slug].get("html") or "")]
            by_shape = {re.sub(r"[^A-Za-z0-9]", "", s): s for s in d_spans}
            shown = 0
            for p in p_spans:
                shape = re.sub(r"[^A-Za-z0-9]", "", p)
                d = by_shape.get(shape)
                if d is None or d == p:
                    continue
                for tag, a, b in char_diffs(d, p):
                    catalogue[(a, b)] += 1
                if shown < 2:
                    print("  %s" % slug)
                    print("    draft    : %s" % d[:110])
                    print("    published: %s" % p[:110])
                    shown += 1
        if catalogue:
            print("\n  catalogue of what changed (draft -> published):")
            for (a, b), n in catalogue.most_common(12):
                print("    %-16r -> %-16r  x%d" % (a, b, n))

    # ---- pass 2: detection across the whole corpus ----------------------
    print("\n=== suspect maths across all %d published posts ===\n" % len(posts))
    findings = []
    for post in posts:
        slug = post["slug"]
        for kind, span in math_spans(post.get("html") or ""):
            span = clean(span)
            bare = sorted(set(BARE_COMMAND.findall(span)))
            comma = bool(LONE_COMMA.search(span))
            if bare or comma:
                findings.append({
                    "slug": slug, "kind": kind, "math": span,
                    "bare_commands": bare, "lone_comma": comma,
                })

    by_slug = collections.Counter(f["slug"] for f in findings)
    for slug, count in by_slug.most_common():
        print("  %-56s %d suspect span(s)" % (slug[:56], count))
        for finding in [f for f in findings if f["slug"] == slug][:2]:
            reason = []
            if finding["bare_commands"]:
                reason.append("bare: " + ", ".join(finding["bare_commands"][:4]))
            if finding["lone_comma"]:
                reason.append("lone comma (was \\,)")
            print("      %-28s %s" % ("; ".join(reason)[:28], finding["math"][:70]))

    out = ROOT / "inventory" / "math-audit.json"
    out.write_text(json.dumps(
        {"catalogue": {"%s -> %s" % k: v for k, v in catalogue.items()},
         "findings": findings}, indent=2), encoding="utf-8")
    print("\n  %d suspect span(s) in %d post(s); detail in inventory/math-audit.json"
          % (len(findings), len(by_slug)))


def char_diffs(a, b):
    import difflib
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal":
            out.append((tag, a[i1:i2][:12], b[j1:j2][:12]))
    return out


if __name__ == "__main__":
    main()
