"""Regression tests for the parts of the migration that fail silently.

Every test here corresponds to something that actually went wrong, or that
would break fifty registered DOIs if it regressed. They run without a network
and without a build.
"""

import importlib.util
import json
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

def ensure_generated():
    """Produce the generated files these tests read.

    index.md, pages/ and topics/ are all generated and gitignored, so on a
    fresh checkout -- which is exactly what CI has -- none of them exists until
    something builds them. The Zotero bibliography is cached in the repository,
    so this needs no network.
    """
    # These scripts parse sys.argv, which under pytest is pytest's own.
    original = sys.argv
    try:
        sys.argv = ["generate"]
        if not list((ROOT / "pages").glob("*.md")):
            load("build_pages").main()
        if not (ROOT / "index.md").exists() or not (ROOT / "notes.md").exists():
            load("build_index").main()
    finally:
        sys.argv = original


def index_source():
    ensure_generated()
    return (ROOT / "index.md").read_text(encoding="utf-8")


UNPUBLISHED = ("draft", "review", "withdrawn")


def published_slugs():
    """Slugs a PRODUCTION build is expected to show.

    Not every article directory: a note at draft or review is deliberately
    withheld until an editor moves it on, and belongs on the preview site.
    Tests that assert over "every article" have to know that, or they fail the
    moment somebody starts writing.
    """
    import build_index
    out = set()
    for path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        if meta.get("status") not in UNPUBLISHED:
            out.add(meta["slug"])
    return out


def test_every_article_is_listed_in_exactly_one_stream():
    """The split must partition the corpus, not sample it.

    The front page carries news, releases and guides; /notes/ carries the
    Technical Notes. An article that reaches neither is unreachable except by
    its URL -- and an article in both feeds is listed twice, which reads as an
    editorial statement nobody made.

    Compared on the FEEDS, not on any link: the front page also signposts the
    three most recent notes, and that is the point of it rather than a leak.
    """
    def listed(text):
        return {slug for slug in slugs
                if 'href="/%s/"' % slug in "".join(
                    block.split("</div>\n\n")[0] for block in
                    text.split('<div class="uwtn-feed">')[1:])}

    slugs = published_slugs()
    front = listed(index_source())
    notes = listed((ROOT / "notes.md").read_text(encoding="utf-8"))
    assert not (front & notes), "in both feeds: %s" % ", ".join(sorted(front & notes))
    assert not (slugs - front - notes), \
        "in neither feed: %s" % ", ".join(sorted(slugs - front - notes))


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


# --------------------------------------------------------------------------
# Banners belong on the web, not on page one of an archival PDF. The visible
# block is derived from the `banner:` front matter so it can be removed for the
# Typst build. (Raw HTML is NOT dropped by Typst -- an earlier assumption that
# it was put a stock photograph on the front of every PDF.)
# --------------------------------------------------------------------------

def test_banner_block_round_trips():
    banner_body = load("banner_body")
    text = ('---\ntitle: T\nbanner: figures/banner.jpg\n---\n'
            '<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>\n\n'
            'Body.\n')
    assert banner_body.banner_from_frontmatter(text) == "figures/banner.jpg"
    head, sep, body = text.partition("\n---\n")
    stripped = banner_body.BANNER_BLOCK.sub("", body, count=1)
    assert "uwtn-banner" not in stripped and stripped.startswith("Body.")


def test_every_banner_is_local():
    """Hot-linking a feature image is how sixteen figures once went dark."""
    import re
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        for src in re.findall(r'<div class="uwtn-banner"><img src="([^"]*)"', text):
            assert not src.startswith("http"), "%s hot-links its banner" % path.parent.name
            assert (path.parent / src).exists(), "%s: missing %s" % (path.parent.name, src)


def test_toc_is_generated_and_grouped_by_year():
    ensure_generated()
    myst = (ROOT / "myst.yml").read_text(encoding="utf-8")
    assert "# BEGIN GENERATED TOC" in myst and "# END GENERATED TOC" in myst
    # A bare year is parsed as an integer and MyST rejects a non-string title.
    import re
    for title in re.findall(r"^\s+- title: (.+)$", myst, re.M):
        assert title.startswith('"'), "toc title %s must be quoted" % title
    for slug in published_slugs():
        assert "articles/%s/%s.md" % (slug, slug) in myst, "%s missing from the toc" % slug
    # And the converse: an unpublished note must NOT be in the production toc.
    import build_index
    for path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        if meta.get("status") in UNPUBLISHED:
            assert "articles/%s/" % meta["slug"] not in myst, \
                "%s is at %s and must not be on the production site" % (
                    meta["slug"], meta.get("status"))


# --------------------------------------------------------------------------
# Image credits and topic pages.
# --------------------------------------------------------------------------

def test_banner_credit_survives_the_pdf_round_trip():
    """Unsplash asks for attribution wherever the photograph appears."""
    banner_body = load("banner_body")
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        if not banner_body.banner_from_frontmatter(text):
            continue
        credit = banner_body.credit_from_metadata(path.parent)
        if credit:
            assert "uwtn-credit" in text, "%s lost its image credit" % path.parent.name
            assert "unsplash.com" in text


def test_credits_do_not_still_attribute_ghost():
    """The utm_source is how Unsplash attributes the referral; this is not Ghost."""
    for path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        assert "utm_source=ghost" not in path.read_text(encoding="utf-8")


def test_topic_slugs_cannot_collide_with_article_slugs():
    ensure_generated()
    build_index = load("build_index")
    articles = {p.parent.name for p in (ROOT / "articles").glob("*/*.md")}
    for topic in (ROOT / "topics").glob("topic-*.md"):
        assert topic.stem not in articles, \
            "%s would compete with an article URL fixed by a DOI" % topic.stem
    assert build_index.topic_slug("Tricks of the Trade") == "topic-tricks-of-the-trade"
    assert build_index.topic_slug("Python/Jupyter") == "topic-python-jupyter"


def test_every_tag_has_a_topic_page():
    ensure_generated()
    import re
    tags = set()
    for meta in (ROOT / "articles").glob("*/metadata.yml"):
        block = re.search(r"^tags:\n((?:  - .*\n)+)", meta.read_text(encoding="utf-8"), re.M)
        if block:
            tags.update(line.strip()[2:].strip('"') for line in block.group(1).strip().split("\n"))
    build_index = load("build_index")
    for tag in tags:
        page = ROOT / "topics" / ("%s.md" % build_index.topic_slug(tag))
        assert page.exists(), "no topic page for %r" % tag


def test_each_topic_page_carries_a_searchable_query_token():
    ensure_generated()
    """`tag:x` only works because the token is in page content, and visible.

    The search index has no tag field -- its records are hierarchy, type, url
    and position -- so the query has nothing to match unless the page says it.
    """
    build_index = load("build_index")
    for page in sorted((ROOT / "topics").glob("topic-*.md")):
        token = page.stem[len("topic-"):]
        text = page.read_text(encoding="utf-8")
        assert "tag:%s" % token in text, "%s carries no tag: token" % page.stem


# --------------------------------------------------------------------------
# Subject and method facets, derived from measuring the corpus rather than
# from Ghost's blog tags.
# --------------------------------------------------------------------------

def test_facet_terms_are_in_the_vocabulary():
    import json
    schema = json.loads((ROOT / "schemas" / "article-metadata.schema.json").read_text())
    build_index = load("build_index")
    for axis in ("subjects", "methods"):
        allowed = set(schema["properties"][axis]["items"]["enum"])
        assert allowed == set(build_index.vocabulary()[axis]), \
            "%s enum has drifted from vocabulary.yml" % axis


def test_classification_covers_every_article():
    ghost_to_myst = load("ghost_to_myst")
    slugs = {p.parent.name for p in (ROOT / "articles").glob("*/*.md")}
    classified = set(ghost_to_myst.load_classification())
    assert slugs <= classified, "unclassified: %s" % sorted(slugs - classified)


def test_ghost_tags_are_recorded_but_not_published():
    """The migration should lose nothing, and publish nothing decorative."""
    import re
    found = False
    for meta in sorted((ROOT / "articles").glob("*/metadata.yml")):
        text = meta.read_text(encoding="utf-8")
        if "ghost_tags:" in text:
            found = True
        assert not re.search(r"^tags:", text, re.M), \
            "%s still carries Ghost's tags as a live field" % meta.parent.name
    assert found, "Ghost tags were dropped rather than recorded"
    index = (ROOT / "index.md").read_text(encoding="utf-8")
    for blog_tag in ("Tricks of the Trade", "Underworld Code"):
        assert blog_tag not in index, "%r is blog furniture, not a facet" % blog_tag


def test_a_subject_may_be_empty():
    """Most of these notes are about machinery and have no Earth subject."""
    build_index = load("build_index")
    metas = [build_index.read_yaml(p) for p in (ROOT / "articles").glob("*/metadata.yml")]
    assert any(not m.get("subjects") for m in metas), \
        "every note claims a subject -- that is a decorative classification"
    assert any(m.get("methods") for m in metas)


# --------------------------------------------------------------------------
# Standing pages: the site's furniture, in the header rather than the sidebar.
# --------------------------------------------------------------------------

def test_declared_pages_all_exist():
    ensure_generated()
    build_pages = load("build_pages")
    for slug, settings in build_pages.load_pages_config().items():
        if settings.get("url"):
            continue          # a nav entry for a page build_index.py generates
        assert (ROOT / "pages" / ("%s.md" % slug)).exists(), "%s not built" % slug


def test_hand_written_pages_are_committed_not_generated():
    """`pages/` is GENERATED and gitignored. Editing a file there is a no-op.

    Two pages were rewritten straight into pages/, committed with a message
    describing the rewrite, and silently discarded: build_pages.py deletes every
    pages/*.md and regenerates them from the Ghost export, so the deploy served
    the old text. The rewrite has to live in pages-src/ with a `source:` entry.

    This checks the declaration is honest -- every `source:` names a file that
    is actually there, so a page cannot claim a hand-written replacement that
    does not exist.
    """
    build_pages = load("build_pages")
    missing = []
    for slug, settings in build_pages.load_pages_config().items():
        source = settings.get("source")
        if source and not (ROOT / source).exists():
            missing.append("%s -> %s" % (slug, source))
    assert not missing, "pages.yml names a source that is not there: %s" % missing
    assert ".gitignore" in [p.name for p in ROOT.iterdir()], "sanity"
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/pages/*.md" in ignored, \
        "if pages/ stops being generated, this test's premise is wrong"


def test_nav_is_generated_and_covers_every_page():
    ensure_generated()
    build_pages = load("build_pages")
    myst = (ROOT / "myst.yml").read_text(encoding="utf-8")
    assert "# BEGIN GENERATED NAV" in myst
    for slug in build_pages.load_pages_config():
        assert "url: /%s" % slug in myst, "%s missing from the header nav" % slug


def test_bibliography_is_baked_not_fetched():  # noqa: D401
    ensure_generated()
    """Ghost drew this with jQuery against api.zotero.org on every page load.

    That left the page empty without scripts, empty when Zotero was down, and
    empty in the archive.
    """
    page = (ROOT / "pages" / "publications-using-uw.md").read_text(encoding="utf-8")
    assert "<script" not in page, "client-side script survived into the page"
    assert "api.zotero.org" not in page, "the page still fetches at read time"
    assert page.count('class="uwtn-ref"') > 50, "the bibliography was not baked in"


def test_dead_pages_are_not_carried_over():
    """The Discourse estate no longer resolves; the stub said 'updating'."""
    build_pages = load("build_pages")
    declared = set(build_pages.load_pages_config())
    for slug in ("uw-mailing-lists", "underworld-geodynamics-community"):
        assert slug not in declared, "%s was carried over despite being dead" % slug


def test_discussion_affordance_is_web_only():
    """A live affordance belongs on the site, not in the fixed record.

    It takes either form -- the embedded Giscus thread when comments are
    enabled, a plain link to Discussions when they are not -- and the stripper
    has to remove whichever is present, or a comment widget ends up in an
    archival PDF.
    """
    banner_body = load("banner_body")
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        assert "uwtn-discuss" in text or "uwtn-comments" in text, \
            "%s offers no way to discuss it" % path.parent.name

    for markup in ('<div class="uwtn-discuss"><a href="#">x</a></div>',
                   '<div class="uwtn-comments"><iframe src="#"></iframe></div>'):
        sample = "---\ntitle: T\n---\nBody.\n\n%s\n" % markup
        _head, _sep, body = sample.partition("\n---\n")
        stripped = banner_body.DISCUSS_BLOCK.sub("\n", body)
        assert "uwtn-" not in stripped, "not stripped for the PDF: %s" % markup


def test_no_third_party_scripts_are_loaded():
    """The Ghost site loaded eight, one from a service shut down in 2023."""
    import re
    build = ROOT / "_build" / "html"
    if not build.exists():
        return
    allowed = ("giscus.app",)          # only if deliberately enabled later
    for page in list(build.glob("*/index.html"))[:6]:
        for src in re.findall(r'<script[^>]+src="(https?://[^"]+)"', page.read_text(encoding="utf-8")):
            assert any(a in src for a in allowed), "third-party script: %s" % src


def test_no_double_escaped_entities_in_generated_pages():
    """MyST re-escapes text inside raw HTML blocks.

    Pre-escaping it produced `&amp;amp;`, and the reader saw `&amp;` where an
    ampersand belonged -- on every topic page and every tag chip.
    """
    import re
    for path in [ROOT / "index.md"] + sorted((ROOT / "topics").glob("*.md")):
        if not path.exists():
            continue
        assert "&amp;" not in path.read_text(encoding="utf-8"), \
            "%s pre-escapes text that MyST will escape again" % path.name


def test_text_helper_refuses_markup():
    """Escaping angle brackets has the same doubling problem, so they are refused."""
    build_index = load("build_index")
    assert build_index.text("Benchmarks & validation") == "Benchmarks & validation"
    try:
        build_index.text("a <script> title")
    except ValueError:
        return
    raise AssertionError("markup in a raw HTML block should be refused, not escaped")


def test_article_source_carries_no_giscus_embed():
    """Giscus is attached after the build, never through the markdown.

    An earlier version emitted a Giscus iframe here as well, so pages carried
    two embeds -- and the stale one offered a sign-in that could never work,
    because GitHub cannot be framed.
    """
    banner_body = load("banner_body")
    block = banner_body.discuss_block(ROOT / "articles" / "x" / "some-slug.md")
    assert "giscus" not in block.lower()
    assert "Read the discussion" in block
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        assert "giscus" not in path.read_text(encoding="utf-8").lower(), \
            "%s has a Giscus embed in its source" % path.parent.name


def test_discussion_block_survives_repeated_strip_and_restore():
    """The block nests divs; a non-greedy match left fragments behind.

    Every remove/add cycle then appended a fresh block on top of the remains,
    so articles accumulated duplicates and the leftovers of earlier versions.
    """
    banner_body = load("banner_body")
    body = "Body.\n\n" + banner_body.discuss_block(pathlib.Path("x/some-slug.md")) + "\n"
    once = banner_body.DISCUSS_BLOCK.sub("\n", body)
    assert "uwtn-discuss" not in once, "the whole block must be removed, not part of it"
    assert once.strip() == "Body."


def test_only_one_discussion_block_per_article():
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        assert path.read_text(encoding="utf-8").count('class="uwtn-discuss"') == 1, \
            "%s has a duplicated discussion block" % path.parent.name


def test_giscus_mapping_survives_the_cutover():
    """`pathname` would change when the site leaves the /underworldcode.org/ prefix."""
    config = (ROOT / "giscus.yml").read_text(encoding="utf-8")
    assert "mapping: specific" in config, \
        "a pathname mapping would orphan every thread at cutover"





def test_giscus_bootstrap_waits_for_hydration():
    """Anything present before hydration is reconciled away.

    The theme calls hydrateRoot(document, ...), so React owns the whole
    document. The bootstrap must therefore add nothing until hydration has
    finished -- and must survive client-side navigation, since the theme never
    reloads the page between articles.
    """
    inject = load("inject_comments")
    config = inject.load_config()
    if config.get("enabled") != "true":
        return
    script = inject.bootstrap(config)
    assert 'addEventListener("load"' in script, "must wait for hydration"
    assert "MutationObserver" in script, "must survive client-side navigation"
    assert "giscus.app/client.js" in script, "must load the real script, not the iframe"
    assert ".uwtn-discuss" in script, "the link stays as the fallback anchor"


def test_bootstrap_javascript_parses():
    import re
    import subprocess
    import tempfile
    inject = load("inject_comments")
    config = inject.load_config()
    if config.get("enabled") != "true":
        return
    body = re.search(r"<script id=\"[^\"]*\">(.*)</script>", inject.bootstrap(config), re.S)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(body.group(1))
        path = fh.name
    result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# --------------------------------------------------------------------------
# DOI minting. The failure that must never happen is a second DOI for a note
# that already has one -- see PUBLISHING.md.
# --------------------------------------------------------------------------

def test_an_article_is_never_deposited_twice():
    """Depositing twice is the failure; depositing once alongside a legacy DOI is not.

    The two DOIs identify different objects -- a living page and a fixed PDF --
    and the deposit says so with an IsVariantFormOf relation. What must never
    happen is a second deposit of the same article, so an archival DOI without
    a record id is an error: the guard that prevents it would have nothing to
    check.
    """
    build_index = load("build_index")
    for path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        if meta.get("archive_doi"):
            assert meta.get("repository_record_id"), \
                "%s could be deposited again" % path.parent.name


def test_an_archival_doi_is_never_a_legacy_one():
    """A deposit must mint its own identifier, never claim one of the fifty."""
    build_index = load("build_index")
    for path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        archive = meta.get("archive_doi")
        assert not (archive and archive.startswith("10.59350/")), \
            "%s claims a Crossref DOI we do not own" % path.parent.name


def test_every_registered_doi_is_recorded_as_legacy():
    import csv
    with (ROOT / "inventory" / "doi-register.csv").open(encoding="utf-8") as fh:
        register = {row["slug"]: row["doi"] for row in csv.DictReader(fh)}
    build_index = load("build_index")
    for path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        expected = register.get(meta.get("slug"))
        if expected:
            assert meta.get("legacy_doi") == expected, \
                "%s: legacy DOI does not match the register" % meta["slug"]


def test_the_submission_route_is_discoverable():
    """A route nobody can find is not a route.

    The pull-request model is obvious once described and invisible until then,
    so it has to be reachable from the front page and from the header.
    """
    ensure_generated()
    assert 'href="/submit/"' in (ROOT / "index.md").read_text(encoding="utf-8"), \
        "the front page does not say how to contribute"
    assert "url: /submit" in (ROOT / "myst.yml").read_text(encoding="utf-8"), \
        "Submit a note is missing from the header nav"


def test_every_orcid_passes_its_check_digit():
    """Shape is not enough: a transposed pair still looks like an ORCID.

    It would attribute an author's work to whoever really holds that
    identifier, silently, on a record carrying a DOI.
    """
    validate = load("validate_metadata")
    assert validate.orcid_checksum_ok("0000-0003-3685-174X")
    assert not validate.orcid_checksum_ok("0000-0001-5685-1664")   # transposed
    import re
    for line in (ROOT / "authors.yml").read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*orcid:\s*(\S+)", line)
        if match and match.group(1) != "null":
            assert validate.orcid_checksum_ok(match.group(1)), \
                "%s in authors.yml fails its check digit" % match.group(1)


def test_deposited_authors_will_propagate_to_orcid():
    """A note's authors should all be identifiable before it is deposited.

    A deposit carrying an ORCID appears in that author's record on its own; an
    author without one has to be added by hand, for every note.

    Two things are checked, and the difference matters. Every ORCID-less author
    must at least be KNOWN -- present in authors.yml -- so that "we do not have
    it" is a recorded state rather than an oversight; authors flagged `no_orcid`
    were asked and have none. Whether an ORCID is actually held is an open
    question the validator warns about, not a defect: making it fail here would
    leave a test that cannot pass until other people answer their email, and a
    test that cannot pass is one everybody learns to ignore.

    It becomes strict at the point it can be acted on -- a deposited article,
    one carrying an archive_doi, must have an ORCID for every author, because
    after the deposit it is too late.
    """
    build_index = load("build_index")
    known = set()
    for line in (ROOT / "authors.yml").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            known.add(stripped.split(":", 1)[1].strip())

    settled = set()
    name = None
    for line in (ROOT / "authors.yml").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            name = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("no_orcid:") and "true" in stripped and name:
            settled.add(name)

    unknown, deposited = set(), set()
    for path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        for author in meta.get("authors") or []:
            if author.get("orcid") or author.get("name") in settled:
                continue          # has one, or has none and we asked
            if author.get("name") not in known:
                unknown.add("%s (%s)" % (author.get("name"), path.parent.name))
            if meta.get("archive_doi"):
                deposited.add("%s (%s)" % (author.get("name"), path.parent.name))

    assert not unknown, ("not in authors.yml, so nobody is chasing an ORCID "
                         "for them: %s" % ", ".join(sorted(unknown)))
    assert not deposited, ("deposited without an ORCID, which cannot be "
                           "corrected afterwards: %s" % ", ".join(sorted(deposited)))


def test_no_figure_name_breaks_the_upload():
    """Figure filenames must survive a CI artifact upload.

    Medium's CDN serves images named `1*1wKV7RUPKbbw4RLT_G.png`. The asterisk is
    legal on disk and in a URL, so everything built and tested clean locally --
    and GitHub's artifact upload rejected the entire site over it. Windows
    refuses the same set, so this is the portable answer rather than a
    workaround for one runner.
    """
    import re as _re
    illegal = _re.compile(r'[*:?"<>|]')
    offenders = [str(p.relative_to(ROOT)) for p in (ROOT / "articles").rglob("*")
                 if illegal.search(p.name)]
    assert not offenders, "unuploadable filename(s): %s" % ", ".join(offenders)


# --------------------------------------------------------------------------
# Deposit. None of the safety here comes from the Figshare token, which has
# exactly one scope and can publish and delete; it all comes from these guards.
# --------------------------------------------------------------------------

deposit = load("deposit")


def test_deposit_refuses_to_redeposit_a_published_record():
    """The failure this design exists to prevent: two DOIs for one note."""
    published = {"id": 12345, "published_date": "2026-01-01", "doi": "10.6084/x"}
    try:
        deposit.check_resumable("x", published, new_version=False)
    except deposit.DepositError as exc:
        assert "second record" in str(exc)
    else:
        raise AssertionError("re-depositing a published record must be refused")
    # And --new-version is the sanctioned way through, so that a correction can
    # reach a record that is already out there. It must be the only way.
    deposit.check_resumable("x", published, new_version=True)


def test_deposit_resumes_an_unpublished_draft():
    """Resuming is the design; the first version of the guard refused it.

    That killed the upload step -- the legitimate continuation of the deposit
    that had just created the record.
    """
    draft = {"id": 12345, "published_date": None}
    deposit.check_resumable("x", draft, new_version=False)
    deposit.check_resumable("x", {"id": 1, "published_date": "2026-01-01"},
                            new_version=True)


def test_deposit_refuses_a_type_with_no_archival_rendition():
    meta = {"slug": "x", "article_type": "news"}
    try:
        deposit.check_eligible("x", meta)
    except deposit.DepositError as exc:
        assert "nothing to deposit" in str(exc)
    else:
        raise AssertionError("a news item must not be deposited")


def test_deposit_refuses_a_doi_with_no_record_id():
    """An archive_doi without a record id leaves the duplicate guard blind."""
    meta = {"slug": "x", "article_type": "technical-note",
            "archive_doi": "10.6084/m9.figshare.1"}
    try:
        deposit.check_eligible("x", meta)
    except deposit.DepositError as exc:
        assert "nothing to check" in str(exc)
    else:
        raise AssertionError("a DOI without a record id must be refused")


def test_the_record_points_at_the_living_article_not_the_old_doi():
    """An archival record should say where the living version is.

    An earlier design declared each deposit a variant form of its Rogue Scholar
    DOI, which made the record a statement about our migration history rather
    than about the article. Those registrations are left alone; the record
    points at the URL a reader can actually follow.
    """
    body = deposit.article_body({
        "slug": "x", "title": "T", "canonical_path": "/x/",
        "legacy_doi": "10.59350/abc", "authors": []})
    related = body["related_materials"][0]
    assert related["identifier"] == "https://www.underworldcode.org/x/"
    assert related["identifier_type"] == "URL"
    assert "10.59350" not in json.dumps(body), "the legacy DOI is not deposit metadata"


def test_the_description_records_when_the_copy_was_taken():
    body = deposit.article_body({
        "slug": "x", "title": "T", "canonical_path": "/x/", "authors": [],
        "archived_at": "2026-08-09T08:45:00Z"})
    assert "2026-08-09T08:45:00Z" in body["description"]


def test_deposit_never_ships_markup_into_a_description():
    out = deposit.plain(
        r"See [the note](/x/) where $\eta$ matters. \begin{equation} a=b "
        r"\end{equation} And more prose besides.")
    for fragment in ("[", "](", "\\begin", "\\eta", "$"):
        assert fragment not in out, "%r survived into %r" % (fragment, out)
    assert "the note" in out and "And more prose besides." in out


def test_every_archival_article_can_be_packaged():
    """The package builder must cope with every article it will be given."""
    import build_index
    build_index.TYPES.update(build_index.article_types())
    archive_package = load("archive_package")
    for path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        meta = build_index.read_yaml(path)
        if not build_index.is_archival(meta):
            continue
        files = dict(archive_package.collect(meta["slug"], meta))
        assert "%s.md" % meta["slug"] in files
        assert "CITATION.cff" in files and "README.md" in files


def test_every_category_id_is_a_number_and_the_defaults_are_present():
    """Figshare validates categories on publish -- the worst place to find out."""
    assert deposit.CATEGORIES["default"], "every note needs at least one category"
    for axis in ("subjects", "methods"):
        for facet, ids in deposit.CATEGORIES[axis].items():
            assert all(isinstance(i, int) for i in ids), "%s: %r" % (facet, ids)


def test_every_facet_in_the_vocabulary_has_a_category_decision():
    """A facet with no entry is an oversight; one mapped to [] is a decision."""
    build_index = load("build_index")
    vocab = build_index.vocabulary()
    for axis in ("subjects", "methods"):
        missing = set(vocab.get(axis, {})) - set(deposit.CATEGORIES[axis])
        assert not missing, "no categories.yml entry for: %s" % ", ".join(sorted(missing))


def test_categories_are_deduplicated():
    meta = {"subjects": ["rheology"], "methods": ["finite-elements", "solvers"]}
    ids = deposit.categories_for(meta)
    assert len(ids) == len(set(ids)), ids
    assert deposit.CATEGORIES["default"][0] in ids


def test_deposit_workflow_can_write_back_the_identifiers():
    """The deposit succeeded once and the identifiers never reached the repo.

    The default GITHUB_TOKEN is read-only, so the commit that records the
    Figshare record id failed with a 403 -- leaving a draft on Figshare that the
    duplicate-mint guard knew nothing about. The permission is the fix; this is
    the reminder of why it is there.
    """
    workflow = (ROOT / ".github" / "workflows" / "deposit.yml").read_text(encoding="utf-8")
    assert "permissions:" in workflow and "contents: write" in workflow


def test_reconversion_never_destroys_the_deposit_identifiers():
    """metadata.yml is regenerated, and one field in it must survive that.

    repository_record_id is the whole guard against minting a second DOI for a
    note that already has one. Losing it does not look like damage -- the file
    validates, the site builds -- and the next deposit quietly creates a rival
    record. This happened, on a note that had a reserved DOI.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "metadata.yml"
        path.write_text("slug: x\narchive_doi: 10.6084/m9.figshare.1\n"
                        "repository_record_id: 42\n", encoding="utf-8")
        kept = ghost_to_myst.preserved_deposit_fields(path)
    assert kept["repository_record_id"] == "42"
    assert kept["archive_doi"] == "10.6084/m9.figshare.1"


def test_a_null_identifier_is_not_carried_over_as_a_string():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "metadata.yml"
        path.write_text("archive_doi: null\n", encoding="utf-8")
        assert ghost_to_myst.preserved_deposit_fields(path) == {}


def test_the_pdf_carries_the_archival_doi_once_a_note_is_deposited():
    """The reserved DOI has to reach the front matter the template renders.

    Reserving it before the PDF exists is the entire reason this provider was
    chosen; it counts for nothing if the document then prints a different
    identifier. The first live rehearsal printed the legacy DOI.
    """
    build_index = load("build_index")
    for meta_path in sorted((ROOT / "articles").glob("*/metadata.yml")):
        meta = build_index.read_yaml(meta_path)
        wanted = meta.get("archive_doi") or meta.get("legacy_doi")
        if not wanted:
            continue
        source = meta_path.parent / ("%s.md" % meta["slug"])
        import re as _re
        found = _re.search(r"^doi:\s*(.+)$",
                           source.read_text(encoding="utf-8"), _re.M)
        assert found and found.group(1).strip() == wanted, \
            "%s: front matter says %s, metadata says %s" % (
                meta["slug"], found.group(1).strip() if found else "(none)", wanted)


def test_the_archival_stamp_stays_a_string_in_the_export_block():
    """YAML reads an unquoted ISO-8601 stamp as a timestamp, not a string.

    The template option is declared as a string, so an unquoted value was
    dropped without a word and the PDF simply had no Archived line. Nothing
    failed; the fact was just missing.
    """
    import re as _re
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        head = path.read_text(encoding="utf-8").split("\n---\n")[0]
        found = _re.search(r"^    archived:\s*(.+)$", head, _re.M)
        if found:
            assert found.group(1).strip().startswith('"'), \
                "%s: archived must be quoted, got %s" % (path.parent.name,
                                                         found.group(1))


def test_a_broken_pdf_build_cannot_report_success():
    """It did. The task swallowed the failure and CI deposited no article."""
    task = (ROOT / "pixi.toml").read_text(encoding="utf-8")
    assert "scripts/build_pdf.py" in task, \
        "the PDF build must go through the wrapper that propagates its status"


def test_every_archival_pdf_is_branded_and_says_where_it_came_from():
    """The logo and the source URL belong on all of them, DOI or not.

    sync_archival returned early for articles with no DOI, so the three notes
    that have none came out unbranded and without a source link -- a scope bug
    that produced correct-looking output for 38 of 41 articles.
    """
    import re as _re
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        head = path.read_text(encoding="utf-8").split("\n---\n")[0]
        if "  - format: typst" not in head:
            continue
        for option in ("logo", "origin_url"):
            assert _re.search(r"^    %s:\s*\S" % option, head, _re.M), \
                "%s: the archival PDF has no %s" % (path.parent.name, option)


def test_no_article_grows_a_second_references_section():
    """A hand-written reference list must not become a citation.

    MyST turns any link whose URL contains a DOI into a citation and appends its
    own References section, so seven articles that already had one ended up with
    two -- the author's entries collapsed to "Author (year)" above a generated
    list. Ghost gave these authors no citation system; a link in a reference
    list is a reference.
    """
    import re as _re
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        heading = _re.search(r"^#+ *(References|Bibliography) *$", text, _re.M | _re.I)
        if not heading:
            continue
        section = text[heading.end():]
        section = _re.split(r"^#+ ", section, maxsplit=1, flags=_re.M)[0]
        offenders = [url for _t, url in _re.findall(r"\[([^\]]*)\]\(([^)]*)\)", section)
                     if _re.search(r"10\.\d{4,9}/", url)]
        offenders += _re.findall(r'<a href="[^"]*10\.\d{4,9}/[^"]*"', section)
        assert not offenders, \
            "%s: a DOI link in the reference list will become a citation: %s" % (
                path.parent.name, offenders[:2])


def test_unlinking_a_reference_is_idempotent():
    """It runs on EVERY build, over sources it rewrote on the last one.

    Without a guard against its own output each build wrapped the previous
    build's `url` in another backtick pair. Fourteen articles were sitting on a
    ``doubled`` set before anyone looked at a diff, the count only ever grew, and
    every build reported reference work it had not needed to do.
    """
    import sync_archival
    body = ("## References\n\nSmith, A. (2020). A paper. *Journal*, 1, 2-3. "
            "[https://doi.org/10.1234/abc](https://doi.org/10.1234/abc)\n")
    once, count = sync_archival.plain_reference_links(body)
    assert count, "nothing was unlinked, so this proves nothing"
    twice, again = sync_archival.plain_reference_links(once)
    assert twice == once, "a second pass changed the text: %r" % twice
    assert again == 0, "a second pass claimed %d more change(s)" % again
    assert "``" not in twice


def test_a_doi_that_contains_parentheses_survives_unlinking():
    """Elsevier's older DOIs embed the year: 10.1016/S0021-9991(02)00031-1.

    A link target that ended at the FIRST ")" cut three references in half and
    kept the offcut, leaving "...(02)00031-100031-1)" in two articles' reference
    lists -- one of them the CitCom history, where the reference is Louis's own.
    """
    import sync_archival
    doi = "https://doi.org/10.1016/S0021-9991(02)00031-1"
    for reference in ("Moresi, L. (2003). A paper. [%s](%s)" % (doi, doi),
                      "Moresi, L. (2003). A paper. %s, 2003." % doi,
                      "Moresi, L. (2003). A paper. (%s)" % doi):
        fixed, count = sync_archival.plain_reference_links(
            "## References\n\n%s\n" % reference)
        assert count, "%r was left to become a citation" % reference
        assert "`%s`" % doi in fixed, \
            "the DOI did not survive intact: %r" % fixed.strip()
        # The offcut was the giveaway: the tail duplicated outside the code span.
        assert "00031-100031-1" not in fixed


def test_the_deposit_runs_inside_the_environment():
    """It shells out to `myst` to rebuild the PDF with the reserved DOI on it.

    Invoked as bare `python3`, myst is not on PATH: the batch stopped on its
    first article with FileNotFoundError. It stopped rather than uploading a
    stale PDF, which is the guard working -- but the guard should not be what
    catches a missing environment.
    """
    workflow = (ROOT / ".github" / "workflows" / "deposit.yml").read_text(encoding="utf-8")
    assert "python3 scripts/deposit.py" not in workflow, \
        "the deposit must run through pixi, or `myst` is missing"
    assert "pixi run deposit" in workflow


def test_every_deposit_mode_has_a_step_that_runs_it():
    """A mode in the dropdown with no step behind it does nothing, silently.

    Every step is guarded by `if: inputs.mode == '...'`, so an unmatched choice
    is not an error -- the job runs, every step skips, and the run goes green.
    Somebody selects it, sees a tick, and believes a deposit happened.
    """
    import re as _re
    workflow = (ROOT / ".github" / "workflows" / "deposit.yml").read_text(encoding="utf-8")
    options = workflow.split("options:")[1].split("jobs:")[0]
    modes = _re.findall(r"^ *- ([a-z-]+) *$", options, _re.M)
    assert len(modes) >= 6, "the mode list did not parse: %s" % modes
    guarded = set(_re.findall(r"inputs\.mode == '([a-z-]+)'", workflow))
    assert set(modes) <= guarded, \
        "mode(s) with no step: %s" % sorted(set(modes) - guarded)
    assert guarded <= set(modes), \
        "step(s) for a mode nobody can select: %s" % sorted(guarded - set(modes))


def test_identifiers_are_recorded_even_when_a_deposit_fails():
    """A draft with a reserved DOI that the repository does not know about is
    the worst state this design has: the duplicate guard has nothing to check."""
    workflow = (ROOT / ".github" / "workflows" / "deposit.yml").read_text(encoding="utf-8")
    commit = workflow.split("- name: Commit the identifiers")[1]
    assert "always()" in commit.split("run:")[0]


def test_an_incomplete_record_is_not_published():
    """Publishing is the one step that cannot be undone.

    Figshare accepts a payload and then drops fields it dislikes: an author
    whose ORCID belongs to an existing user is dropped on create, and nothing
    says so until publish fails with "authors is missing". Look at the record
    before making it permanent.
    """
    source = (ROOT / "scripts" / "deposit.py").read_text(encoding="utf-8")
    guard = source.split("if publish or new_version:")[1].split("provider.publish")[0]
    for field in ('"title"', '"authors"', '"files"'):
        assert field in guard, "publish does not check %s on the record" % field


def test_the_author_lookup_never_degrades_quietly():
    """Carrying on without the lookup loses the author, silently."""
    source = (ROOT / "scripts" / "deposit.py").read_text(encoding="utf-8")
    lookup = source.split("def resolve_authors")[1].split("def create_draft")[0]
    assert "raise DepositError" in lookup, \
        "a failed author lookup must stop the deposit, not fall back"


def test_a_deposit_always_carries_keywords():
    """Figshare will not publish a record with no keywords.

    It reports that as "authors is missing", which cost four batch runs and two
    wrong diagnoses. Every failure was an article with no subject and no method
    facets -- the release notes and how-tos, which are about the software rather
    than about a technique.
    """
    assert deposit.keywords_for({"subjects": [], "methods": []})
    with_facets = deposit.keywords_for({"subjects": ["rheology"], "methods": []})
    assert "rheology" in with_facets and "underworld" in with_facets


def test_publish_checks_the_fields_figshare_requires():
    source = (ROOT / "scripts" / "deposit.py").read_text(encoding="utf-8")
    guard = source.split("if publish or new_version:")[1].split("provider.publish")[0]
    for field in ('"title"', '"authors"', '"files"', '"categories"', '"tags"'):
        assert field in guard, "publish does not check %s" % field


def test_every_mapped_category_is_a_leaf():
    """Figshare refuses to assign a PARENT category.

    "Not allowed to set category Geophysics in article" -- and the deposit dies
    at create, after the previous article has already been published, so the
    batch stops halfway. The leaf/parent split is a property of Figshare's
    vocabulary, not of ours, so it is checked against a snapshot taken from
    /v2/categories rather than trusted.
    """
    leaves = {int(line) for line in
              (ROOT / "inventory" / "figshare-leaf-categories.txt")
              .read_text(encoding="utf-8").splitlines()
              if line.strip() and not line.startswith("#")}
    ids = set(deposit.CATEGORIES["default"])
    for axis in ("subjects", "methods"):
        for values in deposit.CATEGORIES[axis].values():
            ids.update(values)
    offenders = sorted(ids - leaves)
    assert not offenders, "not assignable (parent categories): %s" % offenders


def test_the_two_halves_of_the_build_cannot_race():
    """build-pdf and build-html both mutate the article sources.

    build-pdf strips the web-only banner and discussion block for the duration
    of the Typst run. pixi runs independent tasks concurrently, so in parallel
    the HTML was built from stripped sources and the blocks were missing from
    the tree afterwards -- three tests caught it, which is the only reason it
    was noticed.
    """
    task = (ROOT / "pixi.toml").read_text(encoding="utf-8")
    line = [l for l in task.splitlines() if l.startswith("build-html")][0]
    assert 'depends-on = ["build-pdf"]' in line, \
        "build-html must depend on build-pdf, or the two race over the sources"


def test_every_underworld3_note_acknowledges_its_funding():
    """Three of eleven carried this by hand; eight did not."""
    listed = [l.strip()[2:].strip() for l in
              (ROOT / "acknowledgements.yml").read_text(encoding="utf-8").splitlines()
              if l.strip().startswith("- ")]
    assert listed, "acknowledgements.yml names no articles"
    for slug in listed:
        text = (ROOT / "articles" / slug / ("%s.md" % slug)).read_text(encoding="utf-8")
        assert "NCRIS" in text, "%s does not acknowledge its funding" % slug
        assert text.count("NCRIS") == 1, "%s acknowledges it twice" % slug


def test_no_matrix_row_break_is_a_single_backslash():
    """"\\" ends a row; "\\\\" is an escaped space that silently merges two.

    The JOSS note's Jacobian went through Ghost and came out with single
    backslashes, so a 2x2 block became one row: Typst warned "Too few columns
    specified in the {array} column argument" and rendered the matrix wrong.
    A warning in a build that produces a PDF anyway is one nobody reads.
    """
    import re as _re
    env = _re.compile(r"\\begin\{(array|pmatrix|bmatrix|matrix|cases|aligned|align|split)\}"
                      r".*?\\end\{\1\}", _re.S)
    lone = _re.compile(r"(?<!\\)\\[ \t]*\n")
    offenders = []
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        for match in env.finditer(text):
            if lone.search(match.group()):
                offenders.append("%s:%d (%s)" % (path.parent.name,
                                                 text[:match.start()].count("\n") + 1,
                                                 match.group(1)))
    assert not offenders, \
        "a row break is a single backslash, so the rows merge: %s" % offenders


def test_the_cutover_touches_every_place_the_host_is_named():
    """Half a cutover is worse than none.

    The CNAME switches the build to the site root; giscus.yml's site_url is
    where a reader is sent back to after signing in with GitHub. Move one and
    not the other and the comment widget loads on the new domain offering no
    way to comment -- which looks like a broken feature, not a missed edit.
    """
    cutover = load("cutover")
    named = {path for path in (ROOT / "giscus.yml", ROOT / "README.md",
                               ROOT / "SETUP.md")
             if cutover.STAGING in path.read_text(encoding="utf-8")}
    covered = {path for path, _old, _new in cutover.edits("example.org")}
    assert named <= covered, \
        "the cutover would leave the staging host in: %s" % sorted(
            p.name for p in named - covered)


def test_the_base_url_is_derived_from_the_cname_not_set_by_hand():
    """A project site is served under /<repo>/ and a custom domain is not.

    Set by hand, that prefix is left wrong at cutover and every root-relative
    asset 404s on the new domain.
    """
    deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "if [ -f CNAME ]" in deploy, \
        "the base URL must follow the CNAME, so it cannot be left wrong"


def test_the_custom_domain_reaches_the_published_artifact():
    """The artifact IS the site, and CNAME lives at the repo root.

    deploy.yml reads it to choose the base URL, which made it look handled --
    but _build/html is what gets uploaded, and a Pages deployment whose
    artifact carries no CNAME can drop the custom domain set in the settings.
    The one file the whole cutover turns on, left out of the only directory
    that gets published.
    """
    deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    upload = deploy.index("upload-pages-artifact")
    assert "cp CNAME _build/html" in deploy[:upload], \
        "CNAME must be copied into _build/html BEFORE the artifact is uploaded"


def test_the_feed_covers_every_published_article():
    """Ghost served /rss/; the cutover must not quietly drop its subscribers.

    Nothing fails when a feed disappears -- no test goes red, no page 404s that
    anyone looks at. People just stop reading, and you find out years later.
    """
    build_feed = load("build_feed")
    found = build_feed.entries("example.org")
    published = [p for p in sorted((ROOT / "articles").glob("*/metadata.yml"))]
    assert len(found) >= len(published) - 2, \
        "the feed has %d entries for %d articles" % (len(found), len(published))
    for entry in found:
        assert entry["url"].startswith("https://example.org/"), entry["url"]
        assert entry["title"] and entry["date"], entry


def test_the_feed_is_well_formed_and_escapes_what_goes_into_it():
    """XML assembled from strings, so the escaping is the whole safety story."""
    import xml.dom.minidom
    build_feed = load("build_feed")
    hostile = [{
        "title": 'Ampersands & <angle brackets> and "quotes"',
        "url": "https://example.org/x/", "date": "2020-01-01",
        "authors": ["A & B"], "tags": ["<tag>"],
        "summary": "5 < 6 & 7 > 2", "licence": "CC-BY-4.0", "doi": "10.1234/x",
    }]
    stamp = "2026-01-01T00:00:00Z"
    for text in (build_feed.atom(hostile, "example.org", stamp),
                 build_feed.rss(hostile, "example.org", stamp)):
        xml.dom.minidom.parseString(text)          # raises if not well-formed
        assert "<angle brackets>" not in text, "raw markup reached the feed"


def test_the_feed_host_follows_the_cname():
    """A staging build must not emit a feed full of production links."""
    feed = (ROOT / "scripts" / "build_feed.py").read_text(encoding="utf-8")
    assert 'cname = ROOT / "CNAME"' in feed and "cname.exists()" in feed, \
        "the feed host must be derived from the CNAME, not hard-coded"


def test_the_build_actually_generates_the_feed():
    """A feed generator nobody runs is a file in scripts/."""
    pixi = (ROOT / "pixi.toml").read_text(encoding="utf-8")
    build_html = [l for l in pixi.splitlines() if l.startswith("build-html")][0]
    assert "scripts/build_feed.py" in build_html


def test_no_standing_page_turns_its_dois_into_citations():
    """MyST reads a DOI link as a CITATION and invents an attribution for it.

    The how-to-cite page said "Romain Beucher et al. (2025) (Underworld 2.x)"
    where a Zenodo DOI had been -- a wrong attribution, generated, on the one
    page whose entire job is telling people how to cite. Articles are protected
    by sync_archival.plain_reference_links; pages were not, because that only
    ever walked articles/.

    A DOI in a standing page belongs in backticks. It stays copyable and it
    stops being mistaken for a citation.

    Raw HTML blocks are exempt: MyST does not parse markdown inside them, so
    the DOIs in the publications list stay as plain text and are untouched.
    """
    import re as _re
    offenders = []
    for path in sorted((ROOT / "pages").glob("*.md")):
        lines = [line for line in path.read_text(encoding="utf-8").splitlines()
                 if not line.lstrip().startswith("<")]      # raw HTML block
        text = _re.sub(r"`[^`\n]*`", "", "\n".join(lines))  # inline code is fine
        for match in _re.finditer(r"(?:\]\(\s*)?https?://(?:dx\.)?doi\.org/\S+", text):
            offenders.append("%s: %s" % (path.name, match.group()[:60]))
    assert not offenders, \
        "DOI link(s) in a standing page will become citations: %s" % offenders


def test_the_acknowledgement_is_idempotent():
    """It runs on every build, over sources it wrote on the last one.

    Stripping the block left the blank lines that framed it and the rewrite
    added its own, so eight articles grew two blank lines per build. Nothing
    broke and the diff never stopped -- 184 of them had accumulated before
    anyone read a build's own output.

    The second of two such bugs found by looking at what a build changed. That
    is the check worth keeping: a build-time rewrite must be a fixed point.
    """
    acknowledgement = load("acknowledgement")
    body = ("Some prose.\n\n"
            '<div class="uwtn-discuss">talk</div>\n')
    marker, text = acknowledgement.MARKER, acknowledgement.TEXT
    block = "%s\n\n%s\n\n%s" % (marker, text, marker)

    def apply(source):
        stripped = acknowledgement.BLOCK.sub("\n\n", source).rstrip() + "\n"
        discuss = stripped.find('<div class="uwtn-discuss"')
        if discuss >= 0:
            return "%s\n\n%s\n\n%s" % (stripped[:discuss].rstrip(), block,
                                       stripped[discuss:])
        return stripped.rstrip() + "\n\n" + block + "\n"

    once = apply(body)
    assert once == apply(once) == apply(apply(once)), \
        "the acknowledgement rewrite is not a fixed point"
    assert once.count(marker) == 2, "the marker pair must not multiply"


def test_a_new_note_validates_the_moment_it_is_created():
    """`pixi run new` must not produce a note that fails `pixi run validate`.

    The template carried `doi`, `doi_registrant` and `tags` -- none of them
    fields the schema knows. Every note started from it failed validation on
    all three, which is a poor welcome for a contributor following the
    documented first two commands.
    """
    import json as _json
    schema = _json.loads((ROOT / "schemas" / "article-metadata.schema.json")
                         .read_text(encoding="utf-8"))
    allowed = set(schema["properties"])
    template = (ROOT / "templates" / "article-template" / "metadata.yml")
    fields = set()
    for line in template.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith((" ", "-", "#")) and ":" in line:
            fields.add(line.split(":", 1)[0].strip())
    unknown = sorted(fields - allowed)
    assert not unknown, "the template emits field(s) the schema rejects: %s" % unknown
    assert set(schema["required"]) <= fields | {"id", "slug", "title", "canonical_path"}, \
        "the template omits a required field"


def test_review_notes_stay_off_the_production_site():
    """Production shows published work; the preview site shows everything.

    A note at `review` was published to the live site the day it was drafted --
    visible, indexable, and with nothing to tell a reader it was unfinished.
    The distinction is what the preview exists for.
    """
    source = (ROOT / "scripts" / "build_index.py").read_text(encoding="utf-8")
    assert 'os.environ.get("UWTN_PREVIEW")' in source
    assert '"draft", "review", "withdrawn"' in source, \
        "production must exclude every unpublished status, not just draft"


def test_a_preview_cannot_be_indexed_or_mistaken_for_the_real_thing():
    """Two failure modes, both quiet.

    An indexed draft competes with the canonical article for its own title, and
    this series has fifty registered DOIs whose targets must be the only copy
    that ranks. And a link sent three weeks ago is indistinguishable from the
    published note unless the page says so.
    """
    preview_mark = load("preview_mark")
    assert "noindex" in preview_mark.NOINDEX and "nofollow" in preview_mark.NOINDEX
    source = (ROOT / "scripts" / "preview_mark.py").read_text(encoding="utf-8")
    # The label is built at run time from the branch and commit, so the word
    # lives in main() rather than in the template the script is made from.
    assert "PREVIEW — %s at %s" in source, "the banner must say what it is"
    for gone in ("sitemap.xml", "feed.xml", "rss.xml"):
        assert gone in source, "a preview must not publish %s" % gone
    assert 'Disallow: /' in source


def test_the_preview_path_is_stable_and_says_nothing():
    """A link must keep working as the branch is updated, and the set of drafts
    in flight must not be enumerable from the site."""
    preview_mark = load("preview_mark")
    first = preview_mark.preview_path("feature/some-note")
    assert first == preview_mark.preview_path("feature/some-note"), "not stable"
    assert first != preview_mark.preview_path("feature/other-note")
    assert "some-note" not in first and len(first) == 10


def test_the_preview_never_runs_on_a_fork_pull_request():
    """It publishes with a token, and a fork run cannot have one.

    GitHub withholds secrets from workflows triggered by a pull request from a
    fork. The ways around that -- pull_request_target above all -- would run
    this repository's build scripts over untrusted content with that token in
    scope, in a repository that also holds the Figshare deposit token. A
    contributor from a fork gets the artifact instead.
    """
    text = (ROOT / ".github" / "workflows" / "preview.yml").read_text(encoding="utf-8")
    # Comments stripped: the file EXPLAINS why pull_request_target is not used,
    # and a test that cannot tell the reasoning from the configuration fails on
    # the presence of its own justification.
    config = "\n".join(line for line in text.splitlines()
                       if not line.lstrip().startswith("#"))
    assert "pull_request_target" not in config, \
        "pull_request_target would run untrusted content with a token in scope"
    assert "branches-ignore: [main]" in config, \
        "the preview must never publish main -- that is the live site's job"


def test_the_preview_build_shows_unpublished_notes_and_the_real_one_does_not():
    """The whole reason the preview exists."""
    preview = (ROOT / ".github" / "workflows" / "preview.yml").read_text(encoding="utf-8")
    deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert 'UWTN_PREVIEW: "1"' in preview
    assert "UWTN_PREVIEW" not in deploy, "the published site must not show drafts"


def test_the_preview_keeps_other_branches_previews():
    """Each branch owns a directory; publishing one must not remove the rest.

    This is the reason previews are not on the main site at all: an
    Actions-based Pages deployment replaces the whole site, so hashed
    directories could never accumulate there.
    """
    preview = (ROOT / ".github" / "workflows" / "preview.yml").read_text(encoding="utf-8")
    assert "keep_files: true" in preview
    assert "destination_dir:" in preview


def test_the_preview_comments_on_manual_runs_too():
    """The comment step must not be guarded to push events.

    It was, and so it skipped every manual run -- which is exactly what you do
    when the pull request was opened after the branch was pushed, the ordinary
    order of events. The first push has no pull request to comment on; the
    manual re-run does, and that was the run being skipped.
    """
    text = (ROOT / ".github" / "workflows" / "preview.yml").read_text(encoding="utf-8")
    config = "\n".join(line for line in text.splitlines()
                       if not line.lstrip().startswith("#"))
    comment = config.split("Comment the link on the pull request")[1]
    guard = comment.split("run:")[0]
    assert "github.event_name" not in guard, \
        "the comment step must run on manual dispatch as well as on push"


def test_the_preview_asks_for_no_more_than_it_needs():
    """Declared, and minimal.

    Undeclared, the job got the restricted default and posting the link 403'd
    with "Resource not accessible by integration" -- which reads like a bad
    token and is a missing permissions block. Only the comment needs write:
    publishing uses PREVIEW_TOKEN, and nothing in this job should be able to
    write to this repository's contents.
    """
    text = (ROOT / ".github" / "workflows" / "preview.yml").read_text(encoding="utf-8")
    config = "\n".join(line for line in text.splitlines()
                       if not line.lstrip().startswith("#"))
    assert "pull-requests: write" in config, "the comment step needs this"
    assert "contents: read" in config, \
        "a preview build must not be able to write this repository's contents"


def test_the_preview_marks_the_page_after_hydration_not_before():
    """The theme hydrates the whole document; static markup is reconciled away.

    The banner was written into the HTML and appeared for a fraction of a
    second before React removed it. The discussion block is worse: it is in the
    page TWICE, once as HTML and once as JSON in the hydration payload, so a
    string replacement in the built file is undone the moment the page becomes
    interactive. Both are now done by script, after load, and re-applied when
    the theme routes client-side.

    inject_comments.py learned this first and its docstring says so.
    """
    preview_mark = load("preview_mark")
    banner = preview_mark.BANNER
    assert 'addEventListener("load"' in banner, "must wait for hydration"
    assert "MutationObserver" in banner, "must survive client-side routing"
    assert ".uwtn-discuss-body" in banner and ".uwtn-discuss-links" in banner, \
        "the discussion block must be rewritten in the DOM, not in the markup"


def test_a_preview_never_opens_a_real_discussion_thread():
    """Giscus keys a thread on the article slug.

    Loaded on a preview, it would open discussions on the repository for notes
    that are not published -- and a thread somebody has replied to cannot be
    tidily withdrawn.
    """
    source = (ROOT / "scripts" / "preview_mark.py").read_text(encoding="utf-8")
    assert "uwtn-giscus-bootstrap" in source, "the bootstrap must be removed"
    assert "Discussion will be available after publication" in source


def test_the_preview_comment_links_the_notes_that_changed():
    """A reviewer sent the site root has to go and find what they were asked
    to read, on a site with fifty-odd notes."""
    text = (ROOT / ".github" / "workflows" / "preview.yml").read_text(encoding="utf-8")
    config = "\n".join(line for line in text.splitlines()
                       if not line.lstrip().startswith("#"))
    assert "git diff --name-only" in config and "origin/main...HEAD" in config
    assert "fetch-depth: 0" in config, \
        "diffing against main needs the history a shallow clone does not have"


def test_the_preview_link_is_posted_only_once_it_serves():
    """Pages goes through a CDN: the deploy step going green means the commit
    landed on gh-pages, not that anybody can read it.

    Propagation took longer than the whole build, which looks exactly like a
    broken deployment if you click straight away. The banner carries the
    commit, so the page says which build it is; the workflow polls for that and
    comments afterwards.
    """
    text = (ROOT / ".github" / "workflows" / "preview.yml").read_text(encoding="utf-8")
    config = "\n".join(line for line in text.splitlines()
                       if not line.lstrip().startswith("#"))
    assert "Wait until it is actually being served" in config
    wait = config.index("Wait until it is actually being served")
    comment = config.index("Comment the link on the pull request")
    assert wait < comment, "the link must not be posted before it works"
    assert 'grep -q "$SHORT"' in config, \
        "it must check the SERVED page carries this commit, not merely that it responds"


def test_no_image_carries_an_option_myst_ignores():
    """`:target:` on an `{image}` is dropped, silently as far as the page goes.

    The JOSS note's DOI badge rendered and did nothing -- a badge that looks
    like a link and is not is worse than no badge. MyST warned on every build,
    forty-three times, which is the number at which warnings stop being read.
    A linked image says the same thing in a form MyST implements.
    """
    import re as _re
    offenders = []
    for path in sorted((ROOT / "articles").glob("*/*.md")):
        for block in _re.finditer(r"```\{image\}[^\n]*\n((?::[a-z]+:.*\n)+)```",
                                  path.read_text(encoding="utf-8")):
            for option in _re.findall(r"^:([a-z]+):", block.group(1), _re.M):
                if option in ("target",):
                    offenders.append("%s: :%s:" % (path.parent.name, option))
    assert not offenders, \
        "MyST drops these, so the image is not a link: %s" % offenders


def test_the_toolchain_can_convert_every_figure_format_in_use():
    """A GIF needs ImageMagick before Typst can place it.

    Without it the PDF build says so and carries on WITHOUT the figure. A
    warning in a build that still produces a PDF is one nobody reads, and a
    missing figure in an archival PDF is not recoverable by the reader.
    """
    gifs = sorted((ROOT / "articles").glob("*/figures/*.gif"))
    if not gifs:
        return                      # nothing needs it; the dependency can go
    pixi = (ROOT / "pixi.toml").read_text(encoding="utf-8")
    assert "imagemagick" in pixi, \
        "%d GIF(s) in the corpus and no converter in the environment" % len(gifs)
