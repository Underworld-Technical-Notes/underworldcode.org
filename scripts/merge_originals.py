#!/usr/bin/env python3
"""Merge the drafted originals with the text that was actually published.

Neither source is complete on its own:

* The **drafted original** (underworld3 ``publications/blog-posts/``) is native
  markdown. It carries intent -- a figure is a figure, code is fenced and
  language-tagged, maths is real LaTeX. None of that has to be inferred.
* The **published Ghost text** carries the later editing. Posts were revised
  after the draft was last committed, and that revised text is what the
  registered DOI resolves to.

So the merge takes prose from the published version and structure from the
original: aligned code, figures and display maths come from the draft, aligned
prose comes from Ghost, and blocks that exist on only one side are reported
rather than silently resolved.

Every decision is written to ``inventory/merge-report/<slug>.md`` so the result
can be checked rather than trusted.

Usage:
    python3 scripts/merge_originals.py --repo ~/+Underworld/underworld3-pixi
    python3 scripts/merge_originals.py --repo ... --slug particles-in-underworld3
"""

import argparse
import difflib
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
REPORT = ROOT / "inventory" / "merge-report"

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

FENCE = re.compile(r"^```")


def published_corpus():
    """slug -> flattened published text, for locating draft material."""
    export = ROOT / "inventory" / "ghost-export" / "posts.json"
    corpus = {}
    for post in json.loads(export.read_text(encoding="utf-8"))["posts"]:
        text = re.sub(r"<[^>]+>", " ", post.get("html") or "")
        corpus[post["slug"]] = " ".join(html.unescape(text).split()).lower()
    return corpus


def locate(text, corpus, slug):
    """Where, if anywhere, this draft block was published.

    A block missing from the merge is not necessarily lost. It may survive in
    the same article in another form -- a caption that became a `<figcaption>`
    rather than a paragraph -- or it may have been published in a different
    article when a draft was split. Only what appears nowhere is genuinely
    unpublished, and that is an editorial decision rather than a merge bug.
    """
    probe = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    probe = " ".join(probe.split())[:60]
    if len(probe) < 25:
        return "too short to locate"
    if probe in corpus.get(slug, ""):
        return "same article, different form"
    elsewhere = [s for s, body in corpus.items() if s != slug and probe in body]
    if elsewhere:
        return "published in %s" % ", ".join(elsewhere)
    return "NOT PUBLISHED"


def split_frontmatter(text):
    match = re.match(r"^(---\n.*?\n---\n)(.*)$", text, re.S)
    return (match.group(1), match.group(2)) if match else ("", text)


def blocks(text):
    """Split markdown into (kind, text) blocks, keeping fences intact."""
    out, buf, fence = [], [], None
    for line in text.split("\n"):
        if fence is not None:
            buf.append(line)
            if FENCE.match(line):
                body = "\n".join(buf)
                kind = "directive" if re.match(r"^```\{", body) else "code"
                out.append((kind, body))
                buf, fence = [], None
            continue
        if FENCE.match(line):
            if buf:
                out.append(classify("\n".join(buf)))
                buf = []
            buf, fence = [line], True
            continue
        if line.strip() == "":
            if buf:
                out.append(classify("\n".join(buf)))
                buf = []
            continue
        buf.append(line)
    if buf:
        out.append(classify("\n".join(buf)) if fence is None else ("code", "\n".join(buf)))
    return [(k, t) for k, t in out if t.strip()]


def classify(text):
    stripped = text.strip()
    if stripped.startswith("#"):
        return ("heading", stripped)
    if stripped.startswith("$$") or stripped.startswith("\\["):
        return ("math", stripped)
    if re.match(r"^!\[|^\[!\[", stripped):
        return ("image", stripped)
    if stripped in ("---", "***"):
        return ("rule", stripped)
    return ("prose", stripped)


def key(kind, text):
    """Comparison key: prose on words, structure on its opening line."""
    if kind in ("prose", "heading"):
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"[^a-zA-Z0-9 ]", " ", text)
        return " ".join(text.lower().split())[:70]
    return " ".join(text.split())[:70]


MATH_SPAN = re.compile(r"(?<!\$)\$([^$\n]{2,}?)\$(?!\$)")
DISPLAY_SPAN = re.compile(r"\$\$(.+?)\$\$", re.S)


def shape(span):
    """A maths span reduced to its alphanumerics.

    Ghost's editor removed characters rather than adding them -- backslashes,
    carets, braces -- so a damaged span and its intact original share this
    skeleton. It is what lets the two be paired without guessing.
    """
    return re.sub(r"[^A-Za-z0-9]", "", span)


def repair_math(published_text, draft_text, repairs):
    r"""Restore inline maths in published prose from the draft.

    Ghost damaged LaTeX on the way in: `\,` was published as a bare comma,
    `\|` as `|`, and in places the caret vanished, so `d_i^2` became `d_i2` --
    an exponent silently lost. Prose is taken from the published article because
    that is the version of record, but its *maths* is the draft's wherever the
    two describe the same expression.
    """
    if not draft_text:
        return published_text
    by_shape = {}
    for span in MATH_SPAN.findall(draft_text):
        by_shape.setdefault(shape(span), span)

    def replace(match):
        published_span = match.group(1)
        draft_span = by_shape.get(shape(published_span))
        if draft_span is None or draft_span == published_span:
            return match.group(0)
        repairs.append((published_span, draft_span))
        return "$%s$" % draft_span

    return MATH_SPAN.sub(replace, published_text)


MARKUP = set("\\^_{} ")


def only_markup_restored(published_span, draft_span):
    """True when the draft differs from the published span by markup alone.

    Counting markup characters is not enough. The draft's ``10^{-6}`` (thermal
    diffusivity) and the published ``10^6`` ("wrong by a factor of") reduce to
    the same skeleton and the draft has more braces, so a count-based rule
    swapped one for the other and changed the meaning of a sentence.

    The real question is whether the draft can be obtained from the published
    span by inserting *only* markup -- a backslash, a caret, a brace. Anything
    else, a minus sign above all, is a different expression rather than a
    repaired one, and is left alone.
    """
    import difflib
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, published_span, draft_span).get_opcodes():
        if tag == "equal":
            continue
        if tag in ("delete", "replace"):
            if published_span[i1:i2].strip():
                return False
        if tag in ("insert", "replace"):
            if any(ch not in MARKUP for ch in draft_span[j1:j2]):
                return False
    return True


def repair_document(text, draft_text, repairs):
    """Restore every damaged maths span in a merged article.

    The per-block repair only reaches prose that aligned with a draft block.
    Damage also survives in blocks that had no counterpart, so this runs over
    the finished document against *all* the draft's maths. Matching is by
    skeleton, and a span is only replaced when the draft's version is strictly
    richer -- more LaTeX, same alphanumerics -- so an edited equation is never
    reverted to a superseded one.
    """
    by_shape = {}
    for pattern in (DISPLAY_SPAN, MATH_SPAN):
        for span in pattern.findall(draft_text):
            by_shape.setdefault(shape(span), span)

    def replace(match, wrapper):
        published_span = match.group(1)
        draft_span = by_shape.get(shape(published_span))
        if draft_span is None or draft_span.strip() == published_span.strip():
            return match.group(0)
        if not only_markup_restored(published_span, draft_span):
            return match.group(0)
        repairs.append((published_span.strip(), draft_span.strip()))
        return wrapper % draft_span

    text = DISPLAY_SPAN.sub(lambda m: replace(m, "$$%s$$"), text)
    text = MATH_SPAN.sub(lambda m: replace(m, "$%s$"), text)
    return text


def merge(original, published):
    """Return (merged blocks, decisions)."""
    o_blocks, p_blocks = blocks(original), blocks(published)
    o_keys = [key(k, t) for k, t in o_blocks]
    p_keys = [key(k, t) for k, t in p_blocks]

    merged, decisions, math_repairs = [], [], []
    matcher = difflib.SequenceMatcher(None, o_keys, p_keys)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for oi, pj in zip(range(i1, i2), range(j1, j2)):
                kind, text = o_blocks[oi]
                merged.append(o_blocks[oi])
                if o_blocks[oi][1] != p_blocks[pj][1]:
                    decisions.append(("kept-original", kind,
                                      "identical after normalising; kept the draft's formatting",
                                      o_blocks[oi][1], p_blocks[pj][1]))
        elif tag == "replace":
            # Same position, different content. Prose was edited after drafting,
            # so the published wording wins. Structure keeps the draft's form:
            # its code is fenced and tagged, its figures are real directives,
            # its maths is LaTeX rather than whatever survived the HTML round
            # trip.
            o_slice, p_slice = o_blocks[i1:i2], p_blocks[j1:j2]
            for oi, pj in zip(range(i1, i2), range(j1, j2)):
                o_kind, o_text = o_blocks[oi]
                p_kind, p_text = p_blocks[pj]
                if o_kind == p_kind and o_kind in ("code", "directive", "math", "image"):
                    merged.append((o_kind, o_text))
                    decisions.append(("kept-original", o_kind,
                                      "structure from the draft", o_text, p_text))
                else:
                    fixed = p_text
                    if p_kind == "prose":
                        fixed = repair_math(p_text, o_text if o_kind == "prose" else "",
                                            math_repairs)
                    merged.append((p_kind, fixed))
                    decisions.append(("took-published", p_kind,
                                      "text edited after drafting", o_text, fixed))
            for extra in o_slice[len(p_slice):]:
                decisions.append(("dropped-from-draft", extra[0],
                                  "in the draft, not in the published article", extra[1], ""))
            for extra in p_slice[len(o_slice):]:
                merged.append(extra)
                decisions.append(("added-in-ghost", extra[0],
                                  "added after drafting", "", extra[1]))
        elif tag == "insert":
            for pj in range(j1, j2):
                merged.append(p_blocks[pj])
                decisions.append(("added-in-ghost", p_blocks[pj][0],
                                  "added after drafting", "", p_blocks[pj][1]))
        elif tag == "delete":
            for oi in range(i1, i2):
                kind, text = o_blocks[oi]
                # Structure the published article still needs -- a figure or a
                # code listing -- is kept; draft prose that never shipped is not.
                if kind in ("code", "directive", "math", "image"):
                    merged.append((kind, text))
                    decisions.append(("kept-original", kind,
                                      "structure absent from the HTML render", text, ""))
                else:
                    decisions.append(("dropped-from-draft", kind,
                                      "in the draft, not in the published article", text, ""))
    return merged, decisions, math_repairs


def write_report(slug, decisions, path, corpus, math_repairs):
    counts = {}
    for action, *_ in decisions:
        counts[action] = counts.get(action, 0) + 1

    lines = ["# Merge report — `%s`" % slug, ""]
    lines.append("Prose from the published article, structure from the drafted original.")
    lines.append("")
    for action in ("took-published", "kept-original", "added-in-ghost", "dropped-from-draft"):
        if counts.get(action):
            lines.append("- **%s**: %d" % (action, counts[action]))
    lines.append("")
    lines.append("## Blocks dropped from the draft")
    lines.append("")
    lines.append("These were in the drafted original but are not prose in the merged "
                 "article. Each is checked against the whole published corpus, because "
                 "a block can survive in another form — a caption that became a "
                 "`<figcaption>` — or be published in a different article when a draft "
                 "was split. Only **NOT PUBLISHED** is a real editorial decision.")
    lines.append("")
    dropped = [d for d in decisions if d[0] == "dropped-from-draft"]
    if not dropped:
        lines.append("*None.*")
    unpublished = []
    for _, kind, _, old, _ in dropped:
        where = locate(old, corpus, slug)
        if where == "NOT PUBLISHED":
            unpublished.append((kind, old))
        else:
            lines.append("- *(%s, %s)* %s" % (kind, where, " ".join(old.split())[:150]))
    if unpublished:
        lines.append("")
        lines.append("### Never published — decide whether to restore")
        lines.append("")
        for kind, old in unpublished:
            lines.append("- *(%s)* %s" % (kind, " ".join(old.split())[:300]))
    lines.append("")
    lines.append("## Prose taken from the published article")
    lines.append("")
    lines.append("The draft wording is shown first, the published wording second.")
    lines.append("")
    for action, kind, _why, old, new in decisions:
        if action != "took-published":
            continue
        lines.append("- draft: %s" % (" ".join(old.split())[:180] or "*(none)*"))
        lines.append("  <br>published: %s" % (" ".join(new.split())[:180]))
    lines.append("")
    lines.append("## Maths repaired from the draft")
    lines.append("")
    lines.append("Ghost's editor removed characters from LaTeX on the way in. Where the "
                 "published prose was kept, its maths was restored from the draft.")
    lines.append("")
    if not math_repairs:
        lines.append("*None.*")
    for published_span, draft_span in math_repairs:
        lines.append("- published `%s`" % published_span[:110])
        lines.append("  <br>restored `%s`" % draft_span[:110])
    lines.append("")
    lines.append("## Structure kept from the draft")
    lines.append("")
    kept = [d for d in decisions if d[0] == "kept-original"
            and d[1] in ("code", "directive", "math", "image")]
    lines.append("%d block(s): %s" % (len(kept), ", ".join(sorted({d[1] for d in kept})) or "none"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="checkout holding publications/blog-posts; "
                                       "defaults to the preserved copy in sources/")
    parser.add_argument("--slug", action="append", help="limit to these slugs")
    args = parser.parse_args()

    source_dir = (pathlib.Path(args.repo).expanduser() / "publications" / "blog-posts"
                  if args.repo else ROOT / "sources" / "blog-posts")
    if not source_dir.exists():
        sys.exit("no blog-posts directory at %s" % source_dir)
    REPORT.mkdir(parents=True, exist_ok=True)
    corpus = published_corpus()
    math_fixed = {}

    print("%-52s %6s %6s %6s %6s %s"
          % ("article", "pub", "orig", "added", "cut", "never published"))
    print("-" * 100)

    for filename, slug in sorted(PAIRS.items(), key=lambda kv: kv[1]):
        if args.slug and slug not in args.slug:
            continue
        original = source_dir / filename
        target = ARTICLES / slug / ("%s.md" % slug)
        if not original.exists() or not target.exists():
            print("%-52s  MISSING" % slug[:52])
            continue

        frontmatter, published_body = split_frontmatter(target.read_text(encoding="utf-8"))
        _, original_body = split_frontmatter(original.read_text(encoding="utf-8"))
        # The draft repeats its title as an H1; the front matter already has it.
        original_body = re.sub(r"^\s*#\s+[^\n]*\n", "", original_body, count=1)

        merged, decisions, math_repairs = merge(original_body, published_body)
        body = "\n\n".join(text for _kind, text in merged).strip() + "\n"
        body = repair_document(body, original_body, math_repairs)
        target.write_text(frontmatter + body, encoding="utf-8")
        write_report(slug, decisions, REPORT / ("%s.md" % slug), corpus, math_repairs)

        counts = {}
        for action, *_ in decisions:
            counts[action] = counts.get(action, 0) + 1
        math_fixed[slug] = len(math_repairs)
        never = sum(1 for a, _k, _w, old, _n in decisions
                    if a == "dropped-from-draft" and locate(old, corpus, slug) == "NOT PUBLISHED")
        print("%-52s %6d %6d %6d %6d %s"
              % (slug[:52], counts.get("took-published", 0), counts.get("kept-original", 0),
                 counts.get("added-in-ghost", 0), counts.get("dropped-from-draft", 0),
                 ("**%d**" % never) if never else "-"))

    total_math = sum(math_fixed.values())
    if total_math:
        print("\n%d inline maths span(s) repaired from the drafts:" % total_math)
        for slug, n in sorted(math_fixed.items(), key=lambda kv: -kv[1]):
            if n:
                print("  %-52s %d" % (slug[:52], n))
    print("\nper-article decisions: inventory/merge-report/")


if __name__ == "__main__":
    main()
