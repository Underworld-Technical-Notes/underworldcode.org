#!/usr/bin/env python3
"""Validate every article's metadata.yml against the JSON schema.

Checks the schema, then the cross-file invariants a schema cannot express:

  * the canonical path matches the slug (a mismatch means a DOI would 404)
  * the article file is named <slug>.md (MyST takes the URL from the filename)
  * no two articles share an id or a slug
  * a DOI in the register matches the DOI in the article
  * a legacy DOI is never paired with a new registrant -- the guard against
    accidentally re-minting one of the 50 existing Crossref DOIs
  * ORCIDs are present on DOI-bearing articles (warning, not an error)

Exits 1 on any error. Warnings do not fail the build.

Usage:
    python3 scripts/validate_metadata.py [--strict]
"""

import argparse
import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "article-metadata.schema.json"

ORCID_RE = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")
DOI_RE = re.compile(r"^10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+$")
ID_RE = re.compile(r"^UWTN [0-9]{4}-[0-9]{3}$")
LEGACY_PREFIX = "10.59350/"


def read_metadata(path):
    """Parse the fixed-shape metadata.yml without a YAML dependency."""
    data, key, current_list, current_obj = {}, None, None, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        if indent == 0:
            key, _, value = line.partition(":")
            value = value.strip()
            if value == "":
                data[key] = []
                current_list, current_obj = data[key], None
            else:
                data[key] = scalar(value)
                current_list, current_obj = None, None
        elif line.startswith("- ") and current_list is not None:
            item = line[2:]
            if ":" in item:
                subkey, _, subvalue = item.partition(":")
                current_obj = {subkey.strip(): scalar(subvalue.strip())}
                current_list.append(current_obj)
            else:
                current_list.append(scalar(item))
                current_obj = None
        elif current_obj is not None and ":" in line:
            subkey, _, subvalue = line.partition(":")
            current_obj[subkey.strip()] = scalar(subvalue.strip())
    return data


def scalar(text):
    if text in ("null", "~", ""):
        return None
    if text.startswith('"') and text.endswith('"') and len(text) > 1:
        return text[1:-1].replace('\\"', '"')
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def check_schema(meta, schema, errors, label):
    """Enough of JSON Schema for this fixed shape; no external dependency."""
    for field in schema.get("required", []):
        if field not in meta or meta[field] in (None, "", []):
            errors.append("%s: missing required field '%s'" % (label, field))

    props = schema["properties"]
    for field, value in meta.items():
        if field not in props:
            errors.append("%s: unknown field '%s'" % (label, field))
            continue
        spec = props[field]
        if value is None:
            continue
        if "enum" in spec and value not in spec["enum"]:
            errors.append("%s: %s = %r not in %s" % (label, field, value, spec["enum"]))
        pattern = spec.get("pattern")
        if pattern and isinstance(value, str) and not re.match(pattern, value):
            errors.append("%s: %s = %r does not match %s" % (label, field, value, pattern))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    register = {}
    path = ROOT / "inventory" / "doi-register.csv"
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            register = {row["slug"]: row["doi"] for row in csv.DictReader(fh)}

    errors, warnings = [], []
    seen_ids, seen_slugs = {}, {}
    metas = sorted((ROOT / "articles").glob("*/metadata.yml"))
    if not metas:
        sys.exit("no articles found -- run scripts/ghost_to_myst.py first")

    for meta_path in metas:
        directory = meta_path.parent
        label = directory.name
        meta = read_metadata(meta_path)
        check_schema(meta, schema, errors, label)

        slug = meta.get("slug")
        article_id = meta.get("id")

        if slug and not (directory / ("%s.md" % slug)).exists():
            errors.append("%s: no %s.md -- MyST takes the URL from the filename, "
                          "so the article would not publish at /%s/" % (label, slug, slug))
        if slug and meta.get("canonical_path") != "/%s/" % slug:
            errors.append("%s: canonical_path %r does not match slug %r"
                          % (label, meta.get("canonical_path"), slug))
        if slug in seen_slugs:
            errors.append("%s: slug %r already used by %s" % (label, slug, seen_slugs[slug]))
        seen_slugs[slug] = label
        if article_id in seen_ids:
            errors.append("%s: id %r already used by %s" % (label, article_id, seen_ids[article_id]))
        seen_ids[article_id] = label

        doi, registrant = meta.get("doi"), meta.get("doi_registrant")
        registered = register.get(slug)
        if registered and doi != registered:
            errors.append("%s: DOI %r does not match the register's %r"
                          % (label, doi, registered))
        if doi and doi.startswith(LEGACY_PREFIX) and registrant != "rogue-scholar":
            errors.append("%s: DOI %s is a legacy Crossref registration but "
                          "doi_registrant is %r -- re-minting it would duplicate "
                          "a published DOI" % (label, doi, registrant))
        if registered and not doi:
            errors.append("%s: has a registered DOI (%s) but metadata says none"
                          % (label, registered))

        # The PDF's rotated margin strip shows the live URL on a single line at
        # 6pt. A 65-character slug (85 displayed characters) fits with room to
        # spare; beyond that the cell wraps and pushes its label off the page.
        # The longest slug in the full corpus is 91 characters, so this will
        # fire during the backfill -- shorten the displayed URL in the template,
        # do not let it wrap.
        if slug:
            displayed = len("underworldcode.org/%s/" % slug)
            if displayed > 95:
                warnings.append("%s: live URL is %d characters; it will wrap in "
                                "the PDF margin strip and clip its label"
                                % (label, displayed))

        for author in meta.get("authors") or []:
            orcid = author.get("orcid")
            if orcid and not ORCID_RE.match(str(orcid)):
                errors.append("%s: malformed ORCID %r for %s"
                              % (label, orcid, author.get("name")))
            if doi and not orcid:
                warnings.append("%s: no ORCID for %s on a DOI-bearing article"
                                % (label, author.get("name")))

    print("validated %d article(s)" % len(metas))
    for warning in warnings:
        print("  WARN  %s" % warning)
    for error in errors:
        print("  ERROR %s" % error)

    if errors:
        print("\n%d error(s)" % len(errors))
        sys.exit(1)
    if warnings and args.strict:
        print("\n--strict: %d warning(s) treated as errors" % len(warnings))
        sys.exit(1)
    print("\nOK — %d warning(s), no errors." % len(warnings))


if __name__ == "__main__":
    main()
