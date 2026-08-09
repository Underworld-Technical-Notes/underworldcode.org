#!/usr/bin/env python3
"""Build the archival package that gets deposited for a note.

One zip per article, containing everything needed to read it, cite it and
rebuild it, without this website:

    <slug>/
      <slug>.pdf          the archival rendition, with its DOI on the title page
      <slug>.md           the MyST source it was built from
      figures/            every figure, as referenced by the source
      metadata.json       the article's metadata, machine-readable
      CITATION.cff        how to cite it, in a format tools already read
      README.md           what this is, for a human opening the zip in ten years
      SHA256SUMS          a checksum for every file above

**Deterministic.** Same inputs, byte-identical zip: entries are sorted, and
every timestamp is pinned to the article's publication date rather than to the
moment the build ran. That is not tidiness -- it means a rebuild can be compared
against what was deposited, and a difference means the content changed rather
than that the clock moved.

The package is provider-neutral. Nothing here knows about Figshare.

Usage:
    python3 scripts/archive_package.py --slug <slug> [--out dist/]
    python3 scripts/archive_package.py --all
"""

import argparse
import hashlib
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
sys.path.insert(0, str(ROOT / "scripts"))

SITE = "https://www.underworldcode.org"

# Pinned so the zip is reproducible. Zip stores local time with 2-second
# granularity and no timezone, so the date is what survives; the time is fixed
# rather than meaningful.
ZIP_TIME = (0, 0, 0)


def read_metadata(slug):
    import build_index
    path = ARTICLES / slug / "metadata.yml"
    if not path.exists():
        sys.exit("no such article: %s" % slug)
    return build_index.read_yaml(path)


def citation_cff(meta):
    """CITATION.cff -- the format GitHub, Zenodo and Zotero already read.

    Hand-written rather than via a library: it is twenty lines of a fixed shape,
    and a dependency that has to be installed in CI to emit them is a poor
    trade.
    """
    lines = [
        "cff-version: 1.2.0",
        "message: If you use this note, please cite it.",
        "title: %s" % json.dumps(str(meta.get("title") or "")),
        "type: article",
        "authors:",
    ]
    for author in meta.get("authors") or []:
        name = str(author.get("name") or "").strip()
        family = name.rsplit(" ", 1)[-1] if " " in name else name
        given = name.rsplit(" ", 1)[0] if " " in name else ""
        lines.append("  - family-names: %s" % json.dumps(family))
        if given:
            lines.append("    given-names: %s" % json.dumps(given))
        if author.get("orcid"):
            lines.append("    orcid: https://orcid.org/%s" % author["orcid"])
        if author.get("affiliation"):
            lines.append("    affiliation: %s" % json.dumps(str(author["affiliation"])))
    lines.append("date-released: %s" % (meta.get("publication_date") or ""))
    lines.append("license: %s" % (meta.get("license") or "CC-BY-4.0"))
    lines.append("url: %s%s" % (SITE, meta.get("canonical_path") or "/"))
    doi = meta.get("archive_doi") or meta.get("legacy_doi")
    if doi:
        lines.append("doi: %s" % doi)
    if meta.get("archive_doi") and meta.get("legacy_doi"):
        # Both exist and identify different objects. Saying so in the citation
        # file is cheaper than expecting a reader to work it out.
        lines += [
            "identifiers:",
            "  - type: doi",
            "    value: %s" % meta["legacy_doi"],
            "    description: The web version of this note, as first published.",
        ]
    return "\n".join(lines) + "\n"


def readme(meta, files):
    doi = meta.get("archive_doi") or meta.get("legacy_doi") or "(not yet assigned)"
    authors = ", ".join(str(a.get("name") or "") for a in (meta.get("authors") or []))
    listing = "\n".join("  %s" % name for name in files)
    return """# %(title)s

%(authors)s
%(date)s
DOI: %(doi)s

Part of Underworld Technical Notes, a series about the Underworld geodynamics
code: methods, worked examples, benchmarks and design rationale.

This archive is the fixed version of the note. The web version at

    %(url)s

is the living one, and may since have picked up corrections, better links and
discussion. Where the two differ, this archive is what the DOI identifies.

## What is in here

%(listing)s

The PDF is the article. The markdown is the source it was built from, in MyST
Markdown; the figures are as the source references them. SHA256SUMS covers every
other file, so this archive can be checked against itself:

    shasum -a 256 -c SHA256SUMS

## Licence

%(license)s. You may share and adapt this work, including commercially,
provided you give credit.

## Rebuilding it

The full source of the series, including the tooling that produced this PDF,
is at https://github.com/Underworld-Technical-Notes/underworldcode.org
""" % {
        "title": meta.get("title") or meta.get("slug"),
        "authors": authors,
        "date": meta.get("publication_date") or "",
        "doi": doi,
        "url": SITE + str(meta.get("canonical_path") or "/"),
        "listing": listing,
        "license": meta.get("license") or "CC-BY-4.0",
    }


def collect(slug, meta):
    """[(name in the archive, bytes)], excluding SHA256SUMS."""
    directory = ARTICLES / slug
    files = []

    pdf = directory / ("%s.pdf" % slug)
    if pdf.exists():
        files.append(("%s.pdf" % slug, pdf.read_bytes()))

    source = directory / ("%s.md" % slug)
    files.append(("%s.md" % slug, source.read_bytes()))

    figures = directory / "figures"
    if figures.is_dir():
        for figure in sorted(figures.rglob("*")):
            if figure.is_file():
                files.append(("figures/" + str(figure.relative_to(figures)),
                              figure.read_bytes()))

    files.append(("metadata.json",
                  (json.dumps(meta, indent=2, sort_keys=True) + "\n").encode()))
    files.append(("CITATION.cff", citation_cff(meta).encode()))
    files.sort(key=lambda item: item[0])
    files.append(("README.md", readme(meta, [n for n, _b in files]).encode()))
    files.sort(key=lambda item: item[0])
    return files


def build(slug, out_dir):
    meta = read_metadata(slug)
    files = collect(slug, meta)

    sums = "".join("%s  %s\n" % (hashlib.sha256(data).hexdigest(), name)
                   for name, data in files)
    files.append(("SHA256SUMS", sums.encode()))
    files.sort(key=lambda item: item[0])

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / ("%s.zip" % slug)
    # ZIP_DEFLATED at a fixed level, and no compresslevel drift between Python
    # versions that would change the bytes without changing the content.
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in files:
            date = str(meta.get("publication_date") or "1970-01-01")
            stamp = tuple(int(part) for part in date.split("-")) + ZIP_TIME
            info = zipfile.ZipInfo("%s/%s" % (slug, name), date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)

    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return target, len(files), digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--slug")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--out", default="dist", help="output directory")
    args = parser.parse_args()

    out_dir = ROOT / args.out
    slugs = ([p.parent.name for p in sorted(ARTICLES.glob("*/metadata.yml"))]
             if args.all else [args.slug])

    for slug in slugs:
        target, count, digest = build(slug, out_dir)
        print("  %-52s %2d files  %7.1f KB  %s"
              % (slug[:52], count, target.stat().st_size / 1024, digest[:16]))
    print("%d package(s) in %s/" % (len(slugs), args.out))


if __name__ == "__main__":
    main()
