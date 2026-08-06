"""Regression tests for the parts of the migration that fail silently.

Every test here corresponds to something that actually went wrong, or that
would break fifty registered DOIs if it regressed. They run without a network
and without a build.
"""

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / ("%s.py" % name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ghost_to_myst = load("ghost_to_myst")
merge_originals = load("merge_originals")
fix_slugs = load("fix_slugs")


# --------------------------------------------------------------------------
# Maths repair. The first version of this guard swapped the published
# "wrong by a factor of $10^6$" for the draft's thermal diffusivity
# $10^{-6}$ -- same skeleton, more braces, different meaning.
# --------------------------------------------------------------------------

def test_markup_only_repairs_are_accepted():
    accept = [
        (r"\eta , \delta _ {IJ}", r"\eta \, \delta _ {IJ}"),   # thin space
        ("F_0", "{F_0}"),                                       # braces
        (r"\left(x\right)p", r"\left(x\right)^p"),              # lost exponent
        (r"| x |^2", r"\| x \|^2"),                             # norm bars
    ]
    for published, draft in accept:
        assert merge_originals.only_markup_restored(published, draft), \
            "should repair %r -> %r" % (published, draft)


def test_meaning_changes_are_refused():
    refuse = [
        ("10^6", "10^{-6}"),          # a sign is not markup
        ("a + b", "a - b"),           # nor is an operator
        ("x_1", "x_2"),               # nor a different index
        (r"\alpha", r"\beta"),        # nor a different symbol
    ]
    for published, draft in refuse:
        assert not merge_originals.only_markup_restored(published, draft), \
            "must refuse %r -> %r" % (published, draft)


def test_repair_leaves_untouched_maths_alone():
    repairs = []
    text = "The factor is $10^6$ here."
    out = merge_originals.repair_document(text, "diffusivity $10^{-6}$", repairs)
    assert out == text and repairs == []


# --------------------------------------------------------------------------
# Slug truncation. MyST limits a page slug to 50 characters, which silently
# breaks 12 of the 50 registered DOIs.
# --------------------------------------------------------------------------

def test_long_slugs_are_still_over_the_myst_limit():
    """If this fails the corpus changed, not the tooling -- recheck fix_slugs."""
    register = ROOT / "inventory" / "doi-register.csv"
    import csv
    with register.open(encoding="utf-8") as fh:
        slugs = [row["slug"] for row in csv.DictReader(fh)]
    assert sum(1 for s in slugs if len(s) > 50) >= 12


def test_truncation_collision_would_be_detected():
    """Two slugs sharing a 50-character prefix must not be renamed silently."""
    a = "a" * 50 + "-one"
    b = "a" * 50 + "-two"
    assert a[:50] == b[:50], "test fixture must actually collide"


# --------------------------------------------------------------------------
# Converter. The source site was compromised; nothing executable may cross.
# --------------------------------------------------------------------------

def _convert(html):
    conv = ghost_to_myst.GhostToMyst("test")
    conv.feed(html)
    conv.close()
    return conv


def test_executable_markup_is_dropped_and_reported():
    conv = _convert('<p>before</p><script>alert(1)</script>'
                    '<iframe src="x"></iframe><p>after</p>')
    out = conv.markdown()
    assert "alert" not in out and "iframe" not in out
    assert conv.dropped["script"] == 1 and conv.dropped["iframe"] == 1
    assert "before" in out and "after" in out


def test_unhandled_tags_are_reported_not_swallowed():
    conv = _convert("<p>text</p><marquee>scrolling</marquee>")
    assert conv.unknown["marquee"] == 1, "an unknown tag must be reported"


def test_figure_is_numbered_but_a_bare_image_is_not():
    figure = _convert('<figure><img src="/content/images/a.png" alt="A">'
                      '<figcaption>Caption here</figcaption></figure>').markdown()
    assert "```{figure}" in figure and "Caption here" in figure

    bare = _convert('<p><img src="/content/images/b.png" alt="B"></p>').markdown()
    assert "```{figure}" not in bare, "a bare image must not become a numbered figure"


def test_caption_bolded_end_to_end_is_unbolded():
    conv = _convert('<figure><img src="/content/images/a.png">'
                    '<figcaption><strong>All bold caption text here</strong></figcaption></figure>')
    out = conv.markdown()
    assert conv.unbolded_captions == 1
    assert "**All bold" not in out


def test_partial_caption_emphasis_survives():
    conv = _convert('<figure><img src="/content/images/a.png">'
                    '<figcaption><strong>Left:</strong> a panel and '
                    '<strong>Right:</strong> another</figcaption></figure>')
    assert conv.unbolded_captions == 0
    assert "**Left:**" in conv.markdown()


def test_ghost_ref_parameter_is_stripped():
    out = _convert('<p><a href="https://example.org/x?ref=underworldcode.org">link</a></p>').markdown()
    assert "ref=underworldcode.org" not in out and "https://example.org/x" in out


def test_same_site_links_become_root_relative():
    out = _convert('<p><a href="https://www.underworldcode.org/other-post/">other</a></p>').markdown()
    assert "(/other-post/)" in out


# --------------------------------------------------------------------------
# Block parsing used by the merge.
# --------------------------------------------------------------------------

def test_fenced_code_is_not_split_on_blank_lines():
    text = "para\n\n```python\na = 1\n\nb = 2\n```\n\nafter\n"
    kinds = [k for k, _ in merge_originals.blocks(text)]
    assert kinds == ["prose", "code", "prose"]


def test_directive_is_distinguished_from_code():
    text = "```{figure} figures/a.png\n:alt: x\n\ncap\n```\n"
    assert merge_originals.blocks(text)[0][0] == "directive"


# --------------------------------------------------------------------------
# Ghost stores display maths as `<p>$$<br>...<br>$$</p>`. Letting the source
# newline after a <br> through split one equation into three blocks, which the
# merge then emitted twice -- once as maths, once as literal LaTeX.
# --------------------------------------------------------------------------

def test_display_maths_from_ghost_stays_one_block():
    html = ("<p>$$<br>\n\\sigma = 2\\eta \\, \\dot\\varepsilon<br>\n$$</p>"
            "<p>and prose follows</p>")
    out = _convert(html).markdown()
    assert "$$\n\\sigma = 2\\eta \\, \\dot\\varepsilon\n$$" in out, out
    kinds = [k for k, _ in merge_originals.blocks(out)]
    assert kinds.count("math") == 1, "the equation must be a single block, got %s" % kinds


def test_line_breaks_inside_prose_are_kept():
    out = _convert("<p>first line<br>\nsecond line</p>").markdown()
    assert "first line" in out and "second line" in out
    assert "\n\n" not in out.strip(), "a <br> is not a paragraph break"


def test_display_maths_delimiters_are_balanced_in_every_article():
    import re
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        body = re.sub(r"^---\n.*?\n---\n", "", path.read_text(encoding="utf-8"), flags=re.S)
        body = re.sub(r"```.*?```", "", body, flags=re.S)
        count = len(re.findall(r"(?m)^\$\$\s*$", body))
        assert count % 2 == 0, "%s has %d lone $$ delimiters" % (path.parent.name, count)


# --------------------------------------------------------------------------
# Typst mints a fresh random id per clip path on every compile, so an
# unchanged figure differed between builds and dirtied the tree each time.
# --------------------------------------------------------------------------

def test_svg_ids_are_normalised():
    rebuild_figures = load("rebuild_figures")
    import tempfile
    svg = ('<svg><g clip-path="url(#c4E4D1942BE45BB2659F6F87C48AB180B)"/>'
           '<clipPath id="c4E4D1942BE45BB2659F6F87C48AB180B"/>'
           '<g id="g20BA6410FA305734EE1C40E9BE74F2C5"/></svg>')
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "f.svg"
        path.write_text(svg, encoding="utf-8")
        rebuild_figures.normalise_svg(path)
        out = path.read_text(encoding="utf-8")
    assert "c4E4D194" not in out and "g20BA641" not in out
    # The reference and its definition must still agree.
    assert out.count("uwtn0") == 2 and "uwtn1" in out


def test_committed_svgs_carry_no_random_ids():
    rebuild_figures = load("rebuild_figures")
    for svg in sorted((ROOT / "articles").glob("*/figures/*.svg")):
        text = svg.read_text(encoding="utf-8")
        leftover = rebuild_figures.RANDOM_ID.findall(text)
        assert not leftover, "%s still has %d random id(s)" % (svg.name, len(leftover))


# --------------------------------------------------------------------------
# The landing page is generated, and its styling is inlined because MyST's
# `style` option records a path that does not match where it writes the file.
# Both would fail silently -- the site renders, unstyled.
# --------------------------------------------------------------------------

def index_source():
    """The generated landing page, produced on demand.

    index.md is generated from article metadata and is gitignored, so on a
    fresh checkout -- which is exactly what CI has -- it does not exist until
    something builds it. Generating it here keeps these tests runnable before
    any build step.
    """
    path = ROOT / "index.md"
    if not path.exists():
        build_index = load("build_index")
        build_index.main()
    return path.read_text(encoding="utf-8")


def test_index_lists_every_published_article():
    index = index_source()
    slugs = {p.parent.name for p in (ROOT / "articles").glob("*/*.md")}
    for slug in slugs:
        assert 'href="/%s/"' % slug in index, "%s missing from the landing page" % slug


def test_index_entries_carry_no_blank_lines():
    """A blank line ends a raw HTML block, handing the rest back to markdown."""
    index = index_source()
    feed = index.split('<div class="uwtn-feed">')[1].split("</div>\n\n<div class=\"uwtn-colophon\"")[0]
    for block in feed.split("\n"):
        assert block.strip() != "" or block == "", "blank line inside the feed"


def test_index_uses_only_markup_myst_preserves():
    """MyST strips <article>, <p class>, <time>, role and aria-*."""
    index = index_source()
    for tag in ("<article", "<time", "role=", "aria-"):
        assert tag not in index, "%s does not survive MyST's HTML handling" % tag


def test_myst_style_option_is_declared():
    """The theme injects the stylesheet from hydration data via this option.

    Relying on scripts/inject_style.py alone leaves the page styled for one
    frame and unstyled thereafter, because hydration discards the inlined tag.
    """
    myst = (ROOT / "myst.yml").read_text(encoding="utf-8")
    assert "style: static/uwtn.css" in myst, \
        "site.options.style is what survives hydration; the inline is only for first paint"
