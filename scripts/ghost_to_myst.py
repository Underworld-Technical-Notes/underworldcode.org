#!/usr/bin/env python3
"""Convert Ghost posts to MyST articles.

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
        self.unbolded_captions = 0

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
            self._flush()
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
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
            self._write("  \n" if not self._pre else "\n")
        elif tag == "hr":
            self._flush()
            self._emit("---")
        elif tag in ("ul", "ol"):
            self._flush()
            self._list.append([tag, 0])
        elif tag == "li":
            self._flush()
            if self._list:
                self._list[-1][1] += 1
                depth = len(self._list) - 1
                kind, n = self._list[-1]
                marker = "- " if kind == "ul" else "%d. " % n
                self._buf.append("  " * depth + marker)
        elif tag == "figure":
            self._flush()
            self._fig = {"src": "", "alt": "", "caption": ""}
        elif tag == "img":
            src = attrs.get("src", "")
            alt = attrs.get("alt", "") or ""
            if self._fig is not None:
                self._fig["src"], self._fig["alt"] = src, alt
            else:
                self._flush()
                self._fig = {"src": src, "alt": alt, "caption": ""}
                self._close_figure()
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
            self._flush()
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
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
            if text:
                self._buf.append("[%s](%s)" % (text, href) if href else text)
        elif tag in ("ul", "ol"):
            self._flush()
            if self._list:
                self._list.pop()
        elif tag == "li":
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
        else:
            self._write(data)

    # -- figures ---------------------------------------------------------

    def _close_figure(self):
        if not self._fig or not self._fig["src"]:
            self._fig = None
            return
        src = self._fig["src"]
        name = urllib.parse.unquote(src.rsplit("/", 1)[-1].split("?")[0])
        alt = " ".join(self._fig["alt"].split())
        caption = " ".join(self._fig["caption"].split())
        self.figures.append((src, name, alt, caption))

        block = ["```{figure} figures/%s" % name]
        if alt:
            block.append(":alt: %s" % alt)
        if caption:
            # A caption bolded end to end is not emphasis -- it conveys nothing
            # and fights the lighter caption style. Strip the outer bold only
            # when it wraps the whole caption, so partial emphasis (panel
            # labels and the like) survives untouched.
            stripped = caption.strip()
            if (stripped.startswith("**") and stripped.endswith("**")
                    and stripped.count("**") == 2):
                caption = stripped[2:-2].strip()
                self.unbolded_captions += 1
            block.append("")
            block.append(caption)
        block.append("```")
        self._emit("\n".join(block))
        self._fig = None

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


def write_metadata(path, rec, doi, figures, article_id):
    authors = rec.get("authors") or []
    lines = [
        "# Article metadata. Validated in CI against schemas/article-metadata.schema.json.",
        "id: %s" % yaml_str(article_id),
        "slug: %s" % rec["slug"],
        "title: %s" % yaml_str(rec.get("title") or ""),
        "article_type: technical-note",
        "status: migrated",
        "authors:",
    ]
    for author in authors:
        name, orcid, affiliation = author_entry(author)
        lines.append("  - name: %s" % yaml_str(name))
        lines.append("    orcid: %s" % (orcid or "null"))
        if affiliation:
            lines.append("    affiliation: %s" % yaml_str(affiliation))
    lines += [
        "publication_date: %s" % ((rec.get("published_at") or "")[:10] or "null"),
        "version: 1.0.0",
        "doi: %s" % (doi or "null"),
        # The 50 legacy DOIs are Crossref registrations made by Rogue Scholar under
        # a prefix we do not control. They are never re-minted; new notes get a DOI
        # from the repository provider instead. This field keeps the two eras apart.
        "doi_registrant: %s" % ("rogue-scholar" if doi else "null"),
        "license: CC-BY-4.0",
        "canonical_path: /%s/" % rec["slug"],
        "legacy_paths:",
        "  - /%s/" % rec["slug"],
        "tags:",
    ]
    for tag in (rec.get("tags") or []):
        lines.append("  - %s" % yaml_str(tag.get("name") or ""))
    lines += [
        "figures: %d" % len(figures),
        "source: ghost-migration",
        "ghost_uuid: %s" % (rec.get("uuid") or "null"),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def frontmatter(rec, doi, article_id):
    authors = rec.get("authors") or []
    lines = ["---", "title: %s" % yaml_str(rec.get("title") or "")]
    subtitle = (rec.get("custom_excerpt") or "").strip()
    if subtitle:
        lines.append("description: %s" % yaml_str(" ".join(subtitle.split())))
    lines.append("date: %s" % ((rec.get("published_at") or "")[:10]))
    if authors:
        lines.append("authors:")
        for author in authors:
            name, orcid, affiliation = author_entry(author)
            lines.append("  - name: %s" % yaml_str(name))
            if orcid:
                lines.append("    orcid: %s" % orcid)
            if affiliation:
                lines.append("    affiliations:")
                lines.append("      - %s" % yaml_str(affiliation))
    if doi:
        lines.append("doi: %s" % doi)
    lines.append("license: CC-BY-4.0")
    tags = [t.get("name") for t in (rec.get("tags") or []) if t.get("name")]
    if tags:
        lines.append("keywords:")
        lines += ["  - %s" % yaml_str(t) for t in tags]
    abstract = " ".join((rec.get("custom_excerpt") or rec.get("excerpt") or "").split())
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


def copy_figure(src, name, dest_dir):
    """Place a figure beside the article.

    Site-hosted images come from the local mirror. External ones are fetched
    once and cached: an archival PDF has to be self-contained, and a figure
    loaded from someone else's server is a figure that will disappear -- as
    fifteen of this corpus's own figures already have.
    """
    parts = urllib.parse.urlsplit(src)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if parts.netloc in ("www.underworldcode.org", "underworldcode.org") or not parts.netloc:
        rel = parts.path.lstrip("/")
        source = MIRROR / rel
        if source.exists():
            shutil.copy2(source, dest_dir / name)
            return "copied"
        return "MISSING from mirror: %s" % rel

    cache = MIRROR / "external" / parts.netloc / parts.path.lstrip("/")
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(src, headers={"User-Agent": "uwtn-migration/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                cache.write_bytes(response.read())
        except Exception as exc:  # noqa: BLE001
            return "EXTERNAL, could not fetch (%s): %s" % (type(exc).__name__, src)
    shutil.copy2(cache, dest_dir / name)
    return "localised from %s" % parts.netloc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", help="only posts published on or after YYYY-MM-DD")
    parser.add_argument("--slug", action="append", help="convert specific slug(s)")
    args = parser.parse_args()

    payload = json.loads((EXPORT / "posts.json").read_text(encoding="utf-8"))
    dois = {}
    register = ROOT / "inventory" / "doi-register.csv"
    if register.exists():
        import csv
        with register.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                dois[row["slug"]] = row["doi"]

    selected = []
    for rec in payload["posts"]:
        slug = rec["slug"]
        if re.match(r"^(rce(-\d+)?|sysinfo-[0-9a-f]+)$", slug):
            continue
        if args.slug and slug not in args.slug:
            continue
        if args.since and (rec.get("published_at") or "")[:10] < args.since:
            continue
        selected.append(rec)
    selected.sort(key=lambda r: r.get("published_at") or "")
    ids = article_ids(payload["posts"])

    print("converting %d article(s)\n" % len(selected), file=sys.stderr)
    all_unknown, all_dropped, problems = collections.Counter(), collections.Counter(), []
    applied, stale = [], []
    unbolded = 0

    for rec in selected:
        slug = rec["slug"]
        dest = ARTICLES / slug
        dest.mkdir(parents=True, exist_ok=True)

        source = rec.get("html") or ""
        for find, replace, _why in CORRECTIONS.get(slug, []):
            if find in source:
                source = source.replace(find, replace)
                applied.append((slug, find))
            else:
                stale.append((slug, find))

        conv = GhostToMyst(slug)
        conv.feed(source)
        conv.close()
        body = conv.markdown()

        doi = dois.get(slug, "")
        (dest / ("%s.md" % slug)).write_text(
            frontmatter(rec, doi, ids.get(slug, "")) + body, encoding="utf-8")
        write_metadata(dest / "metadata.yml", rec, doi, conv.figures, ids.get(slug, ""))

        fig_notes = []
        for src, name, _alt, _cap in conv.figures:
            result = copy_figure(src, name, dest / "figures")
            if not result.startswith(("copied", "localised")):
                fig_notes.append("%s -- %s" % (name, result))
                problems.append((slug, result))

        all_unknown.update(conv.unknown)
        unbolded += conv.unbolded_captions
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
