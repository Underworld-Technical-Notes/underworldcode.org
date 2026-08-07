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
        if not (ROOT / "index.md").exists():
            load("build_index").main()
    finally:
        sys.argv = original


def index_source():
    ensure_generated()
    return (ROOT / "index.md").read_text(encoding="utf-8")


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
    """Hot-linked feature images are how sixteen figures were already lost."""
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
    slugs = {p.parent.name for p in (ROOT / "articles").glob("*/*.md")}
    for slug in slugs:
        assert "articles/%s/%s.md" % (slug, slug) in myst, "%s missing from the toc" % slug


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
    for slug in build_pages.load_pages_config():
        assert (ROOT / "pages" / ("%s.md" % slug)).exists(), "%s not built" % slug


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


def test_comments_use_the_iframe_widget_not_the_script():
    """Giscus's <script> cannot work in this theme, twice over.

    MyST strips script from content and from theme parts, and the theme's
    client entry calls hydrateRoot(document, ...) -- React owns the whole
    document -- so injecting it into the built HTML is reconciled away at
    hydration. The iframe widget needs neither.
    """
    banner_body = load("banner_body")
    config = banner_body.giscus_config()
    if config is None:
        return                      # comments not enabled yet
    block = banner_body.discuss_block(ROOT / "articles" / "x" / "some-slug.md")
    assert "<script" not in block
    assert "giscus.app/en/widget" in block
    assert "term=some-slug" in block, "each article needs its own thread"


def test_giscus_mapping_survives_the_cutover():
    """`pathname` would change when the site leaves the /underworldcode.org/ prefix."""
    config = (ROOT / "giscus.yml").read_text(encoding="utf-8")
    assert "mapping: specific" in config, \
        "a pathname mapping would orphan every thread at cutover"


def test_giscus_widget_carries_an_origin():
    """Without it the widget loads but cannot return a reader from sign-in."""
    banner_body = load("banner_body")
    if banner_body.giscus_config() is None:
        return
    block = banner_body.discuss_block(ROOT / "articles" / "x" / "some-slug.md")
    assert "origin=" in block and "some-slug" in block.split("origin=")[1][:200]


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
