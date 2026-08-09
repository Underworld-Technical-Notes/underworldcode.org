#!/usr/bin/env python3
"""Convert Ghost posts to MyST articles.

**Migration scaffolding, not permanent machinery.** This reverse-engineers
intent from a rendered HTML corpus: whether an image was meant as a numbered
figure, a badge or an inline graphic has to be inferred from its markup and its
size. New notes are authored from ``templates/article-template``, where that
intent is stated outright, so none of this guessing applies to them. Legacy
articles that resist the general rules are handled individually in
``corrections.yml`` rather than by making the rules cleverer.

Walks the HTML rather than pattern-matching it, so nested structure survives.
The converter is deliberately **strict**: any tag it does not explicitly handle
is recorded and reported. A converter that silently drops content is the
dangerous failure mode here -- these articles carry DOIs.

Sanitising by allowlist: `script`, `iframe`, `object`, `embed` and `form` are
dropped and reported. The source site was compromised; nothing executable
crosses into the new one.

Layout, one directory per article:

    articles/<slug>/<slug>.md      MyST source (filename sets the URL)
    articles/<slug>/metadata.yml   machine-validated article metadata
    articles/<slug>/figures/       local copies of the article's images

MyST derives a page's URL from its **filename**, not its path, so
``articles/<slug>/<slug>.md`` publishes at ``/<slug>/`` -- exactly the URL the
registered DOIs already point at. That naming is load-bearing; do not "tidy" it
to ``index.md``.

Usage:
    python3 scripts/ghost_to_myst.py --since 2025-08-05
    python3 scripts/ghost_to_myst.py --slug how-underworld3-turns-sympy-into-c
"""

import argparse
import collections
import html
import json
import pathlib
import re
import shutil
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPORT = ROOT / "inventory" / "ghost-export"
MIRROR = ROOT / "assets"
RECOVERED = ROOT / "inventory" / "recovered-figures"
ARTICLES = ROOT / "articles"
SITE = "https://www.underworldcode.org"

DROP = {"script", "iframe", "object", "embed", "form"}


def load_authors():
    """Slug -> {name, orcid, affiliation} from authors.yml.

    Parsed with a small reader rather than PyYAML to keep Stage 0/1 stdlib-only.
    The file is a fixed two-level shape; anything more complex belongs in the
    pixi environment, not here.
    """
    path = ROOT / "authors.yml"
    registry, current = {}, None
    if not path.exists():
        return registry
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        key, _, value = line.strip().partition(":")
        value = value.strip()
        if indent == 2 and not value:
            current = key
            registry[current] = {}
        elif indent == 4 and current:
            registry[current][key] = None if value in ("null", "") else value
    return registry


AUTHORS = load_authors()


def load_corrections():
    """slug -> [(find, replace, why)] from corrections.yml.

    Declared fixes for defects that break the build or resolve to nothing.
    The migration keeps the original prose; these are recorded here so every
    change is visible in review rather than applied by hand.
    """
    path = ROOT / "corrections.yml"
    corrections, slug, entry = {}, None, None
    if not path.exists():
        return corrections
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0 and line.endswith(":"):
            slug = line[:-1]
            corrections[slug] = []
        elif line.startswith("- find:"):
            entry = {"find": _scalar(line.split(":", 1)[1]), "replace": "", "why": ""}
            corrections[slug].append(entry)
        elif entry is not None and line.startswith("replace:"):
            entry["replace"] = _scalar(line.split(":", 1)[1])
        elif entry is not None and line.startswith("why:"):
            entry["why"] = _scalar(line.split(":", 1)[1])
    return {k: [(e["find"], e["replace"], e["why"]) for e in v] for k, v in corrections.items()}


def _scalar(text):
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    return text


CORRECTIONS = load_corrections()


def load_classification():
    """slug -> {article_type, subjects, methods} from classification.yml.

    Kept outside articles/, which `pixi run migrate` regenerates, so an
    editorial judgement is not lost by re-running the conversion.
    """
    path = ROOT / "classification.yml"
    entries, slug = {}, None
    if not path.exists():
        return entries
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith(" ") and raw.rstrip().endswith(":"):
            slug = raw.rstrip()[:-1]
            entries[slug] = {"article_type": "technical-note",
                             "subjects": [], "methods": []}
        elif slug and ":" in raw:
            key, _, value = raw.strip().partition(":")
            value = value.strip()
            if key in ("subjects", "methods"):
                inner = value.strip("[]").strip()
                entries[slug][key] = [x.strip() for x in inner.split(",") if x.strip()]
            elif key == "article_type" and value:
                entries[slug][key] = value
    return entries


CLASSIFICATION = load_classification()


def load_article_types():
    """type -> {stream, archival} from article-types.yml."""
    path = ROOT / "article-types.yml"
    types, current = {}, None
    if not path.exists():
        return types
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith(" ") and raw.rstrip().endswith(":"):
            current = raw.rstrip()[:-1]
            types[current] = {}
        elif current and ":" in raw:
            key, _, value = raw.strip().partition(":")
            types[current][key] = value.strip()
    return types


ARTICLE_TYPES = load_article_types()


def is_archival(slug):
    """Whether this article gets an archival PDF.

    Unknown types are treated as archival: erring towards producing a fixed
    rendition is the safe direction, and the build reports the type as
    unclassified elsewhere.
    """
    kind = CLASSIFICATION.get(slug, {}).get("article_type") or "technical-note"
    return ARTICLE_TYPES.get(kind, {}).get("archival", "true") != "false"


def load_restored_captions():
    """slug -> {figure filename: caption} from restored-captions.yml.

    The Ghost import dropped some captions on the way in. Where the pre-Ghost
    site still has them they are put back -- but only where the figure has no
    caption at all, so this can never overwrite what Ghost did carry across.
    """
    path = ROOT / "restored-captions.yml"
    entries, slug = {}, None
    if not path.exists():
        return entries
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith(" ") and raw.rstrip().endswith(":"):
            slug = raw.rstrip()[:-1]
            entries[slug] = {}
        elif slug and ":" in raw:
            name, _, caption = raw.strip().partition(":")
            entries[slug][name.strip()] = _scalar(caption.strip())
    return entries


RESTORED_CAPTIONS = load_restored_captions()


def load_attribution():
    """slug -> [author key] from attribution.yml.

    Ghost's author field records who ran the import, not always who wrote the
    article. Where a more authoritative source exists -- chiefly the pre-Ghost
    Jekyll site, which carries a byline in each post's front matter -- it is
    recorded here and wins. Like classification.yml this lives outside
    articles/, so re-running the conversion does not undo it.
    """
    path = ROOT / "attribution.yml"
    entries, slug = {}, None
    if not path.exists():
        return entries
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith(" ") and raw.rstrip().endswith(":"):
            slug = raw.rstrip()[:-1]
            entries[slug] = []
        elif slug and raw.strip().startswith("- "):
            entries[slug].append(raw.strip()[2:].strip())
    return entries


ATTRIBUTION = load_attribution()


def article_authors(rec):
    """[(name, orcid, affiliation)] for an article, override first."""
    override = ATTRIBUTION.get(rec["slug"])
    if override:
        return [(AUTHORS[k]["name"], AUTHORS[k].get("orcid"),
                 AUTHORS[k].get("affiliation")) for k in override]
    return [author_entry(a) for a in (rec.get("authors") or [])]


def author_entry(author):
    """Merge a Ghost author record with the registry."""
    slug = author.get("slug") or ""
    known = AUTHORS.get(slug, {})
    name = known.get("name") or author.get("name") or ""
    orcid = known.get("orcid")
    if not orcid:
        # Ghost keeps Louis's ORCID in the "website" field; nobody else has one.
        website = author.get("website") or ""
        if "orcid.org" in website:
            orcid = website.rstrip("/").rsplit("/", 1)[-1]
    return name, orcid, known.get("affiliation")


# Magic bytes -> the extension the file should have had.
SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"RIFF", ".webp"),
]


def asset_name(src):
    """The filename a figure is stored and referenced under.

    Normally the name from the URL -- but Ghost accepted uploads whose extension
    disagrees with their contents, and one of these is a JPEG called `.png`. A
    browser sniffs the bytes and shows it anyway; Typst trusts the extension,
    fails to decode, and the whole PDF export dies with "Invalid PNG signature".
    So the extension is corrected from the magic bytes, here rather than at copy
    time, because the markdown has to refer to it by the same name.
    """
    name = urllib.parse.unquote(src.rsplit("/", 1)[-1].split("?")[0])
    # Medium's CDN names files things like `1*1wKV7RUPKbbw4RLT_G.png`. The
    # asterisk is legal on disk and in a URL, and GitHub's artifact upload
    # rejects the whole build over it -- so the characters Windows and the
    # Actions runner both refuse are replaced here, once, at the only point
    # where the name is decided.
    name = re.sub(r'[*:?"<>|]', "-", name)
    stem, dot, ext = name.rpartition(".")
    if not dot:
        return name
    path, error = cached_asset(src)
    if error or not path.exists():
        return name
    try:
        head = path.open("rb").read(12)
    except OSError:
        return name
    for signature, correct in SIGNATURES:
        if head.startswith(signature):
            if ("." + ext.lower()) not in (correct, ".jpeg" if correct == ".jpg" else correct):
                return stem + correct
            return name
    return name


AT_SIGN = re.compile(r"@(?=[A-Za-z0-9])")


def clean_excerpt(text):
    """Ghost's excerpt, fit to be an abstract.

    Ghost builds an excerpt by taking the first 300-odd characters of the post,
    markup and all, and cutting wherever that lands. For a note whose first
    paragraph contains an equation the result is raw LaTeX in the abstract --
    `\\begin{equation}` and all -- rendered literally on the PDF's title page,
    followed by a word chopped in half.

    So: drop display maths rather than flatten it, strip the markup, and end at
    the last complete sentence.
    """
    text = re.sub(r"\\begin\{.*?\\end\{[a-zA-Z*]+\}", " ", text, flags=re.S)
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.S)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[*_`$\\{}]", "", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = " ".join(text.split())
    # Ghost's cut leaves a half-word; a shorter abstract that ends is better
    # than a longer one that stops.
    if text and text[-1] not in ".!?":
        cut = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
        if cut > 80:
            text = text[:cut + 1]
    return text


def escape_at_signs(text):
    """Escape `@` in prose, so MyST does not read it as a citation.

    `@rbeucher` is a GitHub handle, `@underworld-community` is an organisation
    and `anyone@underworldcode.org` is an email address. MyST reads all three as
    citation keys, finds no bibliography, and the Typst export fails outright --
    three articles produced no PDF at all because of it. Nothing in the legacy
    corpus cites by key, so every `@` in it is prose.

    Code is unaffected: `_write` is not used inside <pre>.
    """
    return AT_SIGN.sub(r"\\@", text)


DOI_IN_URL = re.compile(r"10\.\d{4,9}/", re.I)


INLINE_WRAP = {
    "strong": "**", "b": "**",
    "em": "*", "i": "*",
    "code": "`",
}


class GhostToMyst(HTMLParser):
    """Render Ghost's article HTML as MyST markdown."""

    def __init__(self, slug):
        super().__init__(convert_charrefs=True)
        self.slug = slug
        self.out = []
        self.unknown = collections.Counter()
        self.dropped = collections.Counter()
        self.figures = []          # (src, alt, caption)
        self._skip_depth = 0       # inside a dropped element
        self._pre = False          # inside <pre>
        self._pre_lang = ""
        self._buf = []             # current block's inline text
        self._list = []            # stack of ('ul'|'ol', counter)
        self._href = None
        self._link_text = []
        self._fig = None           # {'src','alt','caption'}
        self._in_caption = False
        self._after_break = False
        self.unbolded_captions = 0
        self.inline_images = 0
        self.linked_images = 0
        self.galleries = 0
        self.raw_references = 0
        self._in_references = False
        self._in_list_item = False
        self._after_marker = False
        self.restored_captions = 0

    # -- helpers ---------------------------------------------------------

    def _emit(self, text):
        self.out.append(text)

    def _flush(self, prefix=""):
        text = "".join(self._buf).strip()
        self._buf = []
        if text:
            self._emit(prefix + text)
        return text

    def _write(self, text):
        if self._skip_depth:
            return
        # The newline between `<li>` and the `<p>` inside it would otherwise
        # land between the bullet and its text, splitting the item in two.
        if self._after_marker:
            if not text.strip():
                return
            text = text.lstrip("\n\r\t ")
            self._after_marker = False
        text = escape_at_signs(text)
        if self._in_caption and self._fig is not None:
            self._fig["caption"] += text
        elif self._href is not None:
            self._link_text.append(text)
        else:
            self._buf.append(text)

    # -- parser callbacks ------------------------------------------------

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self._skip_depth:
            self._skip_depth += 1
            return
        if tag in DROP:
            self.dropped[tag] += 1
            self._skip_depth = 1
            return

        if tag == "p":
            # A <p> INSIDE a list item must not flush. Ghost writes
            # `<li><p>text</p><ul>...</ul></li>` for a nested list, and flushing
            # here emitted the bullet marker on its own and then the text as a
            # loose paragraph -- an empty bullet followed by an orphaned
            # citation, repeated down a whole reading list.
            if not self._in_list_item:
                self._flush()
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self._in_references = False   # cleared by the next heading of any level
            self._buf.append("#" * int(tag[1]) + " ")
        elif tag == "pre":
            self._flush()
            self._pre = True
            self._pre_lang = ""
        elif tag == "code":
            if self._pre:
                cls = attrs.get("class", "")
                match = re.search(r"language-([\w+-]+)", cls)
                self._pre_lang = match.group(1) if match else ""
            else:
                self._write("`")
        elif tag in INLINE_WRAP and not self._pre:
            self._write(INLINE_WRAP[tag])
        elif tag == "span":
            if "italic" in attrs.get("class", ""):
                self._write("*")
        elif tag == "a":
            self._href = attrs.get("href", "")
            self._link_text = []
        elif tag == "br":
            # A <br> is a line break, never a paragraph break. Ghost writes a
            # real newline after it, and letting that through turns one block
            # into two -- which splits `<p>$$<br>...<br>$$</p>` into three,
            # so the equation stops being an equation.
            self._write("  \n" if not self._pre else "\n")
            self._after_break = True
        elif tag == "hr":
            self._flush()
            self._emit("---")
        elif tag in ("ul", "ol"):
            self._flush()
            self._list.append([tag, 0])
        elif tag == "li":
            self._flush()
            self._in_list_item = True
            if self._list:
                self._list[-1][1] += 1
                depth = len(self._list) - 1
                kind, n = self._list[-1]
                marker = "- " if kind == "ul" else "%d. " % n
                self._buf.append("  " * depth + marker)
                self._after_marker = True
        elif tag == "figure":
            self._flush()
            # panels: one entry per <img>. Ghost's gallery card puts several
            # images inside a single <figure>, and keeping only the last one
            # silently deleted nine images from this corpus before anyone
            # noticed. MyST renders a multi-image figure as labelled panels
            # under one numbered caption, in HTML and in the PDF alike, which
            # is what a gallery meant in the first place.
            self._fig = {"panels": [], "caption": ""}
        elif tag == "img":
            src = attrs.get("src", "")
            alt = " ".join((attrs.get("alt") or "").split())
            if self._fig is not None:
                # Inside <figure>: a numbered figure with a caption.
                self._fig["panels"].append((src, alt))
            else:
                # A bare <img> is a badge or an inline graphic, not a figure --
                # numbering it would put "Figure 1:" under a JOSS status badge.
                name = self._asset_name(src)
                self.figures.append((src, name, alt, ""))
                self.inline_images += 1
                # Small graphics keep their own size; anything large is left to
                # scale to the measure, so genuine photographs are unaffected.
                path, _err = cached_asset(src)
                width = intrinsic_width(path)
                small = width is not None and width <= 400

                if self._href is not None:
                    # A linked badge. Neither MyST construct does everything,
                    # verified by rendering both in isolation:
                    #
                    #   [![alt](img)](url)      keeps the link, ignores width --
                    #                           and with a doi.org target MyST
                    #                           rewrites the whole thing into a
                    #                           citation, destroying the image.
                    #   {image} + :target:      honours :width:, but :target: is
                    #                           silently dropped by BOTH the HTML
                    #                           and Typst renderers.
                    #
                    # Size wins for badges: a 168x20 status badge stretched to
                    # the full measure is a visible defect on the page, while a
                    # badge that is not clickable is a minor loss -- these ones
                    # display their own DOI. :target: is still emitted so the
                    # link survives in the source and would work if mystmd ever
                    # honours it. Large linked images take the markdown form
                    # below instead, keeping their link.
                    href = self._clean_href(self._href)
                    self._flush()
                    block = ["```{image} figures/%s" % name]
                    if alt:
                        block.append(":alt: %s" % alt)
                    block.append(":target: %s" % href)
                    if small:
                        block.append(":width: %dpx" % width)
                    block.append("```")
                    # `:target:` is silently ignored by BOTH renderers, so the
                    # badge became decoration with no destination -- a "launch
                    # binder" button that does nothing, in a PDF where nobody
                    # can guess the URL.
                    #
                    # A markdown linked image is clickable but cannot be sized
                    # (a {width=} attribute leaks through as literal text), and
                    # for a doi.org target MyST destroys the image and turns it
                    # into a citation. So the destination goes UNDERNEATH, where
                    # it can be read whether or not it can be clicked.
                    #
                    # A DOI is written as code rather than a link: any link to
                    # doi.org becomes a citation, which would pull a second
                    # References section onto articles that already have one.
                    if DOI_IN_URL.search(href):
                        block.append("")
                        block.append("`%s`" % href)
                    else:
                        block.append("")
                        block.append("[%s](%s)" % (link_label(href), href))
                    self._emit("\n".join(block))
                    self._href, self._link_text = None, []
                    self.linked_images += 1
                elif small:
                    self._flush()
                    block = ["```{image} figures/%s" % name]
                    if alt:
                        block.append(":alt: %s" % alt)
                    block.append(":width: %dpx" % width)
                    block.append("```")
                    self._emit("\n".join(block))
                else:
                    self._write("![%s](figures/%s)" % (alt, name))
        elif tag == "figcaption":
            self._in_caption = True
        elif tag == "sup":
            self._write("^")
        elif tag in ("div", "blockquote"):
            self._flush()
        else:
            self.unknown[tag] += 1

    def handle_endtag(self, tag):
        if self._skip_depth:
            self._skip_depth -= 1
            return

        if tag == "p":
            if not self._in_list_item:
                self._flush()
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            # A hand-written reference list starts here. Ghost gave authors no
            # citation system, so this heading plus a run of links is how every
            # reference in this corpus was written.
            heading = "".join(self._buf).lstrip("# ").strip().lower()
            self._in_references = heading.rstrip(":") in ("references", "bibliography")
            self._flush()
        elif tag == "pre":
            code = "".join(self._buf).strip("\n")
            self._buf = []
            self._emit("```%s\n%s\n```" % (self._pre_lang, code))
            self._pre = False
        elif tag == "code" and not self._pre:
            self._write("`")
        elif tag in INLINE_WRAP and not self._pre:
            self._write(INLINE_WRAP[tag])
        elif tag == "span":
            pass  # closing handled loosely; italic spans are well formed here
        elif tag == "a":
            text = "".join(self._link_text).strip()
            href = self._clean_href(self._href or "")
            self._href = None
            if not text:
                pass
            else:
                self._buf.append("[%s](%s)" % (text, href) if href else text)
        elif tag in ("ul", "ol"):
            self._flush()
            if self._list:
                self._list.pop()
        elif tag == "li":
            self._in_list_item = False
            self._flush()
        elif tag == "figcaption":
            self._in_caption = False
        elif tag == "figure":
            self._close_figure()

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._pre:
            self._buf.append(data)
            return
        if self._after_break:
            self._after_break = False
            if not data.strip():
                return              # the source newline that follows a <br>
            data = data.lstrip("\n\r")
        self._write(data)

    # -- figures ---------------------------------------------------------

    @staticmethod
    def _asset_name(src):
        return asset_name(src)

    def _close_figure(self):
        if not self._fig or not self._fig["panels"]:
            self._fig = None
            return
        panels = self._fig["panels"]
        caption = " ".join(self._fig["caption"].split())
        if not caption and len(panels) == 1:
            restored = RESTORED_CAPTIONS.get(self.slug, {}).get(
                self._asset_name(panels[0][0]))
            if restored:
                caption = restored
                self.restored_captions += 1
        for src, alt in panels:
            self.figures.append((src, self._asset_name(src), alt, caption))

        if len(panels) > 1:
            self.galleries += 1
            self._emit(self._panel_block(panels, caption))
            self._fig = None
            return

        src, alt = panels[0]
        name = self._asset_name(src)
        block = ["```{figure} figures/%s" % name]
        if alt:
            block.append(":alt: %s" % alt)
        if caption:
            # A caption bolded end to end is not emphasis -- it conveys nothing
            # and fights the lighter caption style. Strip the outer bold only
            # when it wraps the whole caption, so partial emphasis (panel
            # labels and the like) survives untouched.
            block.append("")
            block.append(self._unbold(caption))
        block.append("```")
        self._emit("\n".join(block))
        self._fig = None

    def _panel_block(self, panels, caption):
        """A multi-image figure, as panels under one numbered caption.

        Colon fences, not backticks: the panel images are markdown inside the
        directive body, and a backtick fence would take them literally.
        """
        block = [":::{figure}"]
        for src, alt in panels:
            block.append("![%s](figures/%s)" % (alt, self._asset_name(src)))
        if caption:
            block.append("")
            block.append(self._unbold(caption))
        block.append(":::")
        return "\n".join(block)

    def _unbold(self, caption):
        """Drop bold that wraps a caption end to end. See _close_figure."""
        stripped = caption.strip()
        if (stripped.startswith("**") and stripped.endswith("**")
                and stripped.count("**") == 2):
            self.unbolded_captions += 1
            return stripped[2:-2].strip()
        return caption

    @staticmethod
    def _clean_href(href):
        """Strip Ghost's ?ref= tracking; make same-site links root-relative."""
        href = html.unescape(href)
        parts = urllib.parse.urlsplit(href)
        query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != "ref"]
        if parts.netloc in ("www.underworldcode.org", "underworldcode.org"):
            parts = parts._replace(scheme="", netloc="")
        return urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment)
        )

    def markdown(self):
        self._flush()
        body = "\n\n".join(b for b in (x.strip() for x in self.out) if b)
        body = re.sub(r"\n{3,}", "\n\n", body)
        # Drop the hard-break markers that hug display delimiters, so the block
        # is plain `$$\n...\n$$` rather than `$$  \n...  \n$$`.
        body = re.sub(r"\$\$[ \t]*\n", "$$\n", body)
        body = re.sub(r"[ \t]+\n(\$\$)", r"\n\1", body)
        return body + "\n"


def article_ids(all_posts):
    """slug -> 'UWTN YYYY-NNN', numbered by publication order within each year.

    Derived from every post Ghost holds, not just the ones being converted, so
    migrating older articles later cannot renumber ones already published. An
    article ID that appears in a deposited PDF must never change.
    """
    ordered = sorted(
        (p for p in all_posts if not re.match(r"^(rce(-\d+)?|sysinfo-[0-9a-f]+)$", p["slug"])),
        key=lambda p: (p.get("published_at") or ""),
    )
    counters, ids = {}, {}
    for post in ordered:
        year = (post.get("published_at") or "0000")[:4]
        counters[year] = counters.get(year, 0) + 1
        ids[post["slug"]] = "UWTN %s-%03d" % (year, counters[year])
    return ids


def yaml_str(value):
    """Quote a scalar for YAML only when it needs it."""
    text = str(value)
    if text == "":
        return '""'
    if re.search(r'[:#\[\]{}",&*?|<>=!%@`]|^\s|\s$|^-', text):
        return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"')
    return text


DEPOSIT_FIELDS = ("archive_doi", "repository_record_id", "archived_at")


def preserved_deposit_fields(path):
    """Identifiers the deposit wrote, which conversion must never destroy.

    metadata.yml is regenerated from the Ghost export, so a re-run would
    otherwise clear `repository_record_id` -- and that field is the entire guard
    against minting a second DOI for a note that already has one. Losing it does
    not look like damage: the file still validates, the site still builds, and
    the next deposit quietly creates a rival record.

    This is the one direction the conversion is not the source of truth in.
    """
    if not path.exists():
        return {}
    kept = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(":")
        if key in DEPOSIT_FIELDS and value.strip() not in ("", "null", "~"):
            kept[key] = value.strip()
    return kept


def write_metadata(path, rec, doi, figures, article_id, banner=None, credit=None):
    kept = preserved_deposit_fields(path)
    authors = article_authors(rec)
    lines = [
        "# Article metadata. Validated in CI against schemas/article-metadata.schema.json.",
        "id: %s" % yaml_str(article_id),
        "slug: %s" % rec["slug"],
        "title: %s" % yaml_str(rec.get("title") or ""),
        "article_type: %s" % (CLASSIFICATION.get(rec["slug"], {}).get(
            "article_type") or "technical-note"),
        "status: migrated",
        "authors:",
    ]
    for name, orcid, affiliation in authors:
        lines.append("  - name: %s" % yaml_str(name))
        lines.append("    orcid: %s" % (orcid or "null"))
        if affiliation:
            lines.append("    affiliation: %s" % yaml_str(affiliation))
    lines += [
        "publication_date: %s" % ((rec.get("published_at") or "")[:10] or "null"),
        "version: 1.0.0",
        # Two DOIs, two objects. legacy_doi resolves to this page and is not
        # ours to re-point; archive_doi will resolve to the deposited PDF and is
        # the one to circulate. Depositing is not duplicate publication because
        # the record declares itself a variant form of the legacy DOI.
        "legacy_doi: %s" % (doi or "null"),
        "archive_doi: %s" % kept.get("archive_doi", "null"),
        "archived_at: %s" % kept.get("archived_at", "null"),
        "license: CC-BY-4.0",
        "canonical_path: /%s/" % rec["slug"],
        "legacy_paths:",
        "  - /%s/" % rec["slug"],
    ]
    # Ghost's tags ("Tricks of the Trade", "Underworld Code") are blog
    # furniture; the subject and method facets replace them. They are recorded
    # so the migration loses nothing, but nothing is built from them.
    facets = CLASSIFICATION.get(rec["slug"], {})
    for axis in ("subjects", "methods"):
        lines.append("%s:" % axis)
        for term in facets.get(axis) or []:
            lines.append("  - %s" % term)
    lines.append("ghost_tags:")
    for tag in (rec.get("tags") or []):
        lines.append("  - %s" % yaml_str(tag.get("name") or ""))
    lines += [
        "banner: %s" % (yaml_str("figures/" + banner) if banner else "null"),
        "banner_credit: %s" % (yaml_str(credit) if credit else "null"),
        "figures: %d" % len(figures),
        "source: ghost-migration",
        "ghost_uuid: %s" % (rec.get("uuid") or "null"),
    ]
    if kept.get("repository_record_id"):
        lines.append("repository_record_id: %s" % kept["repository_record_id"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def banner_credit(rec):
    """The photographer credit Ghost stored with the feature image.

    Ghost's Unsplash integration writes a caption like
    ``Photo by <a href="...">Name</a> on <a href="...">Unsplash</a>``, so the
    attribution Unsplash's licence asks for is already in the export -- no API
    key needed. The ``utm_source=ghost`` in those links is rewritten: this is no
    longer Ghost, and the parameter is how Unsplash attributes referrals.
    """
    caption = rec.get("feature_image_caption") or ""
    if "unsplash.com" not in caption:
        return None
    text = re.sub(r"<span[^>]*>|</span>", "", caption)
    text = text.replace("utm_source=ghost", "utm_source=underworld-technical-notes")
    text = " ".join(html.unescape(text).split())
    # Keep only the anchors and plain words; anything else is Ghost's chrome.
    if not re.fullmatch(r"[^<>]*(?:<a href=\"[^\"]*\">[^<]*</a>[^<>]*)+", text):
        return None
    return text


def localise_banner(rec, dest_dir):
    """Bring the post's feature image alongside the article.

    Ghost hot-links these to images.unsplash.com. They are decorative, but the
    same hot-linking is why sixteen figures in this corpus had to be hunted down
    from other sources, so they are fetched once and stored with the article.

    Returns the local filename, or None.
    """
    src = rec.get("feature_image") or ""
    if not src:
        return None
    path, error = cached_asset(src)
    if error or not path.exists():
        return None
    head = path.read_bytes()[:12]
    if head[:3] == b"\xff\xd8\xff":
        suffix = ".jpg"
    elif head[:8] == b"\x89PNG\r\n\x1a\n":
        suffix = ".png"
    elif head[:4] == b"RIFF":
        suffix = ".webp"
    else:
        return None            # not an image we recognise; skip rather than guess
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = "banner" + suffix
    shutil.copy2(path, dest_dir / name)
    return name


def banner_block(banner, credit):
    """The visible banner, with its credit revealed on hover."""
    parts = ['<div class="uwtn-banner"><img src="%s" alt="">' % banner]
    if credit:
        parts.append('<div class="uwtn-credit">%s</div>' % credit)
    parts.append("</div>")
    return "".join(parts)


def frontmatter(rec, doi, article_id, banner=None):
    authors = article_authors(rec)
    lines = ["---", "title: %s" % yaml_str(rec.get("title") or "")]
    subtitle = (rec.get("custom_excerpt") or "").strip()
    if subtitle:
        lines.append("description: %s"
                     % yaml_str(" ".join(subtitle.split()).replace("@", "&#64;")))
    lines.append("date: %s" % ((rec.get("published_at") or "")[:10]))
    if authors:
        lines.append("authors:")
        for name, orcid, affiliation in authors:
            lines.append("  - name: %s" % yaml_str(name))
            if orcid:
                lines.append("    orcid: %s" % orcid)
            if affiliation:
                lines.append("    affiliations:")
                lines.append("      - %s" % yaml_str(affiliation))
    if doi:
        # Until a deposit exists this is the legacy DOI; the publish command
        # replaces it with the archival one, which is what should be cited.
        lines.append("doi: %s" % doi)
    lines.append("license: CC-BY-4.0")
    if banner:
        # Gives the theme an og:image for sharing. The visible banner is a raw
        # HTML block in the body, which the HTML build renders and the Typst
        # build drops -- decorative on the web, absent from the archival PDF.
        lines.append("banner: figures/%s" % banner)
    tags = [t.get("name") for t in (rec.get("tags") or []) if t.get("name")]
    if tags:
        lines.append("keywords:")
        lines += ["  - %s" % yaml_str(t) for t in tags]
    # An email address in the excerpt reads as a citation key and takes the
    # whole PDF export down with it -- but this one ends up inside a quoted YAML
    # scalar, where a backslash is doubled and so stops escaping anything. The
    # numeric character reference survives quoting and renders as "@".
    # custom_excerpt ONLY.
    #
    # A custom excerpt is a standfirst somebody wrote -- a lead-in to the
    # article, in the newspaper sense. Ghost's `excerpt` is not written at all:
    # it is the first 300-odd characters of the body, cut wherever that lands.
    # Used as an abstract it duplicates the opening paragraph the reader is
    # about to read, and stops mid-word -- one ended at "doi:10.10".
    #
    # 26 of these notes have a standfirst and 27 do not. The 27 lose nothing by
    # having no abstract: their first paragraph follows immediately.
    abstract = clean_excerpt(rec.get("custom_excerpt") or "").replace("@", "&#64;")
    # An archival PDF only where the content is load-bearing. An announcement is
    # dated by nature, and a citable snapshot of "version 2.10 is out" serves
    # nobody -- see article-types.yml, which is the one place that decides.
    if is_archival(rec["slug"]):
        lines += [
            "exports:",
            "  - format: typst",
            "    template: ../../templates/pdf",
            "    output: %s.pdf" % rec["slug"],
            "    article_id: %s" % yaml_str(article_id),
            "    article_version: 1.0.0",
        ]
    if abstract:
        lines += ["parts:", "  abstract: %s" % yaml_str(abstract)]
    lines += ["---", ""]
    return "\n".join(lines)


def cached_asset(src):
    """Local path for an image, fetching and caching an external one.

    Site-hosted images come from the Stage 0 mirror. External ones are cached
    once: an archival PDF has to be self-contained, and a figure loaded from
    someone else's server is a figure that will disappear -- as fifteen of this
    corpus's own figures already have.
    """
    parts = urllib.parse.urlsplit(src)
    if parts.netloc in ("www.underworldcode.org", "underworldcode.org") or not parts.netloc:
        return MIRROR / parts.path.lstrip("/"), None

    cache = MIRROR / "external" / parts.netloc / parts.path.lstrip("/")
    if cache.exists():
        return cache, None
    cache.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(src, headers={"User-Agent": "uwtn-migration/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            cache.write_bytes(response.read())
    except Exception as exc:  # noqa: BLE001
        return cache, "%s: %s" % (type(exc).__name__, exc)
    return cache, None


BOOKMARK = re.compile(r'<figure[^>]*kg-bookmark-card.*?</figure>', re.S)


def simplify_bookmark_cards(source):
    """Turn Ghost's link-preview cards into ordinary links.

    A bookmark card is chrome: the target site's favicon, its social thumbnail,
    its meta description and its publisher name, wrapped in one big anchor. Fed
    to the converter as-is it becomes a numbered figure of a favicon next to a
    book cover, followed by a link whose text is every one of those fields run
    together. Neither survives into print, and the real content -- what was
    linked to, and what it is -- is one sentence.

    Done here rather than in the parser because the card is a fixed Ghost
    structure: matching it is honest pattern-matching, whereas threading four
    nested div classes through a streaming parser is not.
    """
    def replace(match):
        card = match.group(0)
        href = re.search(r'href="([^"]+)"', card)
        title = re.search(r'kg-bookmark-title">(.*?)</div>', card, re.S)
        desc = re.search(r'kg-bookmark-description">(.*?)</div>', card, re.S)
        if not href or not title:
            return card
        text = '<p><a href="%s">%s</a>' % (href.group(1), title.group(1).strip())
        if desc:
            text += " &mdash; %s" % desc.group(1).strip()
        return text + "</p>"
    return BOOKMARK.sub(replace, source)


SVG_MASK = re.compile(r'\s*mask="url\(#[^)]*\)"')


def link_label(href):
    """Readable text for a badge's destination.

    The URL itself, shortened to host and first path segment: enough to say
    where it goes, short enough not to wrap in the margin of a PDF.
    """
    parts = urllib.parse.urlsplit(href)
    label = parts.netloc.replace("www.", "")
    segments = [s for s in parts.path.split("/") if s]
    if segments:
        label += "/" + segments[0]
    return label


def strip_svg_mask(path):
    """Remove `mask="url(#...)"` from a badge SVG.

    A shields.io badge draws its label twice -- once in #010101 as a shadow,
    once in #fff -- over coloured rectangles inside a masked group. The mask is
    there only to round the corners. Where a renderer does not honour it the
    group vanishes, the coloured rectangles with it, and what is left is white
    text on a white page with a grey shadow behind it: illegible, and exactly
    what it looked like on the site.

    Dropping the mask costs the rounded corners and guarantees the colours.
    These are badges; the corners are not the point.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    if "mask=\"url(" not in text:
        return
    path.write_text(SVG_MASK.sub("", text), encoding="utf-8")


def intrinsic_width(path):
    """Pixel width of an SVG or PNG, or None.

    MyST scales an image to the text measure unless told otherwise, which turns
    a 168x20 status badge into a full-width banner. Sizing from the file keeps
    small graphics small without hard-coding a guess -- and without shrinking
    the linked images that are genuinely photographs.
    """
    try:
        head = path.read_bytes()[:1024]
    except OSError:
        return None
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(head[16:20], "big")
    match = re.search(rb"<svg[^>]*?\bwidth=['\"](\d+(?:\.\d+)?)", head)
    if match:
        return int(float(match.group(1)))
    return None


def copy_figure(src, name, dest_dir):
    """Place a figure beside the article.

    Site-hosted images come from the local mirror. External ones are fetched
    once and cached: an archival PDF has to be self-contained, and a figure
    loaded from someone else's server is a figure that will disappear -- as
    sixteen of this corpus's own figures nearly did.

    Those sixteen are checked for first. They point at a host that no longer
    exists, so the mirror has nothing for them and the fetch would fail; the
    replacements are held in `inventory/recovered-figures/<slug>/<name>`, keyed
    by the name the article refers to rather than by where it was found. See
    inventory/lost-figures.md for where each one came from.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    recovered = RECOVERED / dest_dir.parent.name / name
    if recovered.exists():
        shutil.copy2(recovered, dest_dir / name)
        return "recovered"

    source, error = cached_asset(src)
    if error:
        return "EXTERNAL, could not fetch (%s)" % error
    if not source.exists():
        return "MISSING from mirror: %s" % src
    shutil.copy2(source, dest_dir / name)
    if name.lower().endswith(".svg"):
        strip_svg_mask(dest_dir / name)
    external = urllib.parse.urlsplit(src).netloc
    if external and "underworldcode.org" not in external:
        return "localised from %s" % external
    return "copied"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", help="only posts published on or after YYYY-MM-DD")
    parser.add_argument("--slug", action="append", help="convert specific slug(s)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite articles that already exist (see below)")
    args = parser.parse_args()

    payload = json.loads((EXPORT / "posts.json").read_text(encoding="utf-8"))
    dois = {}
    register = ROOT / "inventory" / "doi-register.csv"
    if register.exists():
        import csv
        with register.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                dois[row["slug"]] = row["doi"]

    selected, existing = [], []
    for rec in payload["posts"]:
        slug = rec["slug"]
        if re.match(r"^(rce(-\d+)?|sysinfo-[0-9a-f]+)$", slug):
            continue
        if args.slug and slug not in args.slug:
            continue
        if args.since and (rec.get("published_at") or "")[:10] < args.since:
            continue
        # Conversion is the FIRST step, not the only one: an article may since
        # have had its text merged from the author's original, its figures
        # rebuilt as vectors, or a caption restored by hand. Re-running the
        # converter over it silently throws all of that away, which is a quiet
        # and expensive kind of damage. Existing articles are therefore skipped
        # unless asked for explicitly, and --force means "and re-run the rest of
        # the pipeline afterwards".
        if (ARTICLES / slug).exists() and not args.force:
            existing.append(slug)
            continue
        selected.append(rec)
    if existing:
        print("skipping %d article(s) that already exist; --force to overwrite"
              % len(existing), file=sys.stderr)
    selected.sort(key=lambda r: r.get("published_at") or "")
    ids = article_ids(payload["posts"])

    print("converting %d article(s)\n" % len(selected), file=sys.stderr)
    all_unknown, all_dropped, problems = collections.Counter(), collections.Counter(), []
    applied, stale = [], []
    unbolded = 0
    inline = 0
    linked = 0
    galleries = 0
    restored = 0
    raw_refs = 0

    for rec in selected:
        slug = rec["slug"]
        dest = ARTICLES / slug
        dest.mkdir(parents=True, exist_ok=True)

        banner = localise_banner(rec, dest / "figures")
        source = rec.get("html") or ""
        for find, replace, _why in CORRECTIONS.get(slug, []):
            if find in source:
                source = source.replace(find, replace)
                applied.append((slug, find))
            else:
                stale.append((slug, find))
        source = simplify_bookmark_cards(source)

        conv = GhostToMyst(slug)
        conv.feed(source)
        conv.close()
        body = conv.markdown()

        doi = dois.get(slug, "")
        credit = banner_credit(rec) if banner else None
        if banner:
            body = (banner_block("figures/" + banner, credit) + "\n\n") + body
        (dest / ("%s.md" % slug)).write_text(
            frontmatter(rec, doi, ids.get(slug, ""), banner) + body, encoding="utf-8")
        write_metadata(dest / "metadata.yml", rec, doi, conv.figures, ids.get(slug, ""),
                       banner, credit)

        fig_notes = []
        for src, name, _alt, _cap in conv.figures:
            result = copy_figure(src, name, dest / "figures")
            if not result.startswith(("copied", "localised", "recovered")):
                fig_notes.append("%s -- %s" % (name, result))
                problems.append((slug, result))

        all_unknown.update(conv.unknown)
        unbolded += conv.unbolded_captions
        inline += conv.inline_images
        galleries += conv.galleries
        restored += conv.restored_captions
        raw_refs += conv.raw_references
        linked += conv.linked_images
        all_dropped.update(conv.dropped)

        flags = []
        if conv.unknown:
            flags.append("unknown tags: %s" % dict(conv.unknown))
            problems.append((slug, "unknown tags %s" % dict(conv.unknown)))
        if conv.dropped:
            flags.append("DROPPED: %s" % dict(conv.dropped))
        if fig_notes:
            flags.append("; ".join(fig_notes))
        print("  %-54s %5d words  %2d fig  %s"
              % (slug[:54], len(body.split()), len(conv.figures),
                 " | ".join(flags) if flags else "ok"), file=sys.stderr)

    print("\n--- conversion ---", file=sys.stderr)
    print("  %d article(s) written to articles/" % len(selected), file=sys.stderr)
    if all_dropped:
        print("  sanitiser dropped: %s" % dict(all_dropped), file=sys.stderr)
    if all_unknown:
        print("  UNHANDLED TAGS: %s -- extend the converter" % dict(all_unknown), file=sys.stderr)
    if problems:
        print("  %d problem(s) needing attention:" % len(problems), file=sys.stderr)
        for slug, note in problems:
            print("    %-52s %s" % (slug[:52], note), file=sys.stderr)
    if linked:
        print("  %d linked image(s) emitted as {image} with :target:" % linked,
              file=sys.stderr)
    if restored:
        print("  %d caption(s) restored from the pre-Ghost site" % restored,
              file=sys.stderr)
    if raw_refs:
        print("  %d reference link(s) left as written rather than turned into "
              "citations" % raw_refs, file=sys.stderr)
    if galleries:
        print("  %d gallery card(s) emitted as multi-panel figures" % galleries,
              file=sys.stderr)
    if inline:
        print("  %d inline image(s) kept inline rather than numbered as figures"
              % inline, file=sys.stderr)
    if unbolded:
        print("  %d caption(s) bolded end-to-end in the source: outer bold removed"
              % unbolded, file=sys.stderr)
    if applied:
        print("  %d declared correction(s) applied:" % len(applied), file=sys.stderr)
        for slug, find in applied:
            print("    %-40s %s" % (slug[:40], find), file=sys.stderr)
    if stale:
        print("  STALE correction(s) -- no longer match the source:", file=sys.stderr)
        for slug, find in stale:
            print("    %-40s %s" % (slug[:40], find), file=sys.stderr)
    if not all_unknown and not problems:
        print("  no unhandled tags, no missing figures", file=sys.stderr)


if __name__ == "__main__":
    main()
