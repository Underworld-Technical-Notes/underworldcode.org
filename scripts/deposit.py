#!/usr/bin/env python3
"""Deposit a note's archival package, and mint its DOI.

    validate -> create draft -> reserve DOI -> write it into metadata.yml
    -> rebuild the PDF -> upload the package -> STOP
    -> (separately, with --publish) publish

**Dry run by default.** Nothing reaches the network unless `--live` is given,
and nothing is published unless `--publish` is given as well. Everything except
the final publish is reversible: a draft can be deleted, a reserved DOI expires
with it, files can be replaced.

The order is the whole reason Figshare was chosen. The DOI is reserved *before*
the PDF is built, so it can be printed on the title page of the document it
identifies. A provider that only mints on publication cannot do that.

**Resumable, because a half-finished deposit is the dangerous state.** The
record id and the reserved DOI are written into `metadata.yml` as soon as they
exist. A run that dies after reserving picks up from there instead of reserving
a second DOI for the same note -- and a note that already has a record id is
refused outright, with a new version offered instead.

Usage:
    python3 scripts/deposit.py --slug <slug>              # dry run, no network
    python3 scripts/deposit.py --slug <slug> --live       # draft + DOI + upload
    python3 scripts/deposit.py --slug <slug> --live --publish
    python3 scripts/deposit.py --slug <slug> --live --delete-draft
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
sys.path.insert(0, str(ROOT / "scripts"))

API = "https://api.figshare.com/v2"

# Verified against docs.figshare.com/swagger.json.
LICENSE_CC_BY_4 = 1
DEFINED_TYPE = "online resource"

CHUNK = 8 * 1024 * 1024


class DepositError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# The provider interface. Figshare is the only implementation today; the point
# of the seam is that the Zenodo comparison stays possible without rewriting
# the command around it.
# ---------------------------------------------------------------------------

class Provider:
    def create_draft(self, meta): raise NotImplementedError
    def reserve_doi(self, record_id): raise NotImplementedError
    def update_metadata(self, record_id, meta): raise NotImplementedError
    def upload(self, record_id, path): raise NotImplementedError
    def get_record(self, record_id): raise NotImplementedError
    def publish(self, record_id): raise NotImplementedError
    def new_version(self, record_id): raise NotImplementedError
    def delete_draft(self, record_id): raise NotImplementedError


class Figshare(Provider):
    def __init__(self, token):
        if not token:
            raise DepositError(
                "no FIGSHARE_TOKEN in the environment. In CI it comes from the "
                "repository secret; locally, export it for the length of the "
                "session rather than putting it in a file.")
        self.token = token

    # -- transport ----------------------------------------------------------

    def _call(self, method, path, body=None, raw=None, url=None):
        target = url or (API + path)
        data = raw if raw is not None else (
            json.dumps(body).encode() if body is not None else None)
        request = urllib.request.Request(target, data=data, method=method)
        request.add_header("Authorization", "token %s" % self.token)
        if raw is None and body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise DepositError("%s %s -> HTTP %s: %s"
                               % (method, target, exc.code, detail)) from None
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except ValueError:
            return {"raw": payload}

    # -- operations ---------------------------------------------------------

    def resolve_authors(self, meta):
        """Match each author to an existing Figshare user by ORCID.

        Figshare refuses to create a second author entity for an ORCID that
        already belongs to a user: "There can't be 2 users having the same
        orcid." Several of this series' authors have Figshare accounts, so most
        deposits would fail on the first call.

        Linking to the real account is better than working around it. The
        deposit then belongs to that person's Figshare identity, which is the
        same identity the ORCID auto-population works from.
        """
        resolved = []
        for author in meta.get("authors") or []:
            orcid = author.get("orcid")
            entry = {"name": str(author.get("name") or "")}
            if orcid:
                entry["orcid_id"] = orcid
                try:
                    matches = self._call("POST", "/account/authors/search",
                                         body={"search_for": orcid})
                except DepositError:
                    matches = []
                for match in matches if isinstance(matches, list) else []:
                    if str(match.get("orcid_id") or "") == orcid and match.get("id"):
                        entry = {"id": match["id"]}
                        break
            resolved.append(entry)
        return resolved

    def find_draft(self, meta):
        """An unpublished draft for this note that we lost track of.

        Belt and braces for the case that actually happened: the deposit
        succeeded, and the commit that records the id failed, so Figshare held a
        draft the repository knew nothing about. Creating another one would give
        the note two records and, on publish, two DOIs -- the exact failure the
        record id exists to prevent, arriving through the one path the record id
        cannot cover.

        Matched on the exact title among unpublished articles.
        """
        title = str(meta.get("title") or "")
        try:
            listing = self._call("GET", "/account/articles?page_size=1000")
        except DepositError:
            return None
        matches = [a for a in (listing if isinstance(listing, list) else [])
                   if str(a.get("title") or "") == title
                   and not a.get("published_date")]
        if len(matches) > 1:
            raise DepositError(
                "%d unpublished drafts already have the title %r (ids %s). "
                "Delete the extras in Figshare before depositing."
                % (len(matches), title,
                   ", ".join(str(a.get("id")) for a in matches)))
        return matches[0].get("id") if matches else None

    def create_draft(self, meta):
        existing = self.find_draft(meta)
        if existing:
            return int(existing)
        body = article_body(meta)
        body["authors"] = self.resolve_authors(meta)
        try:
            result = self._call("POST", "/account/articles", body=body)
        except DepositError as exc:
            # The search should have caught this, but the error names the user
            # it collided with, so use it rather than making a person go and
            # look the id up by hand.
            match = re.search(r"Similar user_id: (\d+)", str(exc))
            if not match:
                raise
            body["authors"] = [{"id": int(match.group(1))}
                               if len(body["authors"]) == 1 else a
                               for a in body["authors"]]
            result = self._call("POST", "/account/articles", body=body)
        location = result.get("location") or ""
        record_id = location.rstrip("/").rsplit("/", 1)[-1]
        if not record_id.isdigit():
            raise DepositError("could not read a record id from %r" % result)
        return int(record_id)

    def reserve_doi(self, record_id):
        result = self._call("POST", "/account/articles/%d/reserve_doi" % record_id)
        doi = result.get("doi")
        if not doi:
            raise DepositError("reserve_doi returned no doi: %r" % result)
        return doi

    def update_metadata(self, record_id, meta):
        body = article_body(meta)
        body["authors"] = self.resolve_authors(meta)
        self._call("PUT", "/account/articles/%d" % record_id, body=body)

    def get_record(self, record_id):
        return self._call("GET", "/account/articles/%d" % record_id)

    def upload(self, record_id, path):
        data = path.read_bytes()
        result = self._call("POST", "/account/articles/%d/files" % record_id,
                            body={"name": path.name, "size": len(data),
                                  "md5": hashlib.md5(data).hexdigest()})
        file_url = result["location"]
        info = self._call("GET", "", url=file_url)
        parts = self._call("GET", "", url=info["upload_url"])["parts"]
        for part in parts:
            chunk = data[part["startOffset"]:part["endOffset"] + 1]
            self._call("PUT", "", raw=chunk,
                       url="%s/%d" % (info["upload_url"], part["partNo"]))
        self._call("POST", "", url=file_url)
        return info.get("id") or file_url.rsplit("/", 1)[-1]

    def publish(self, record_id):
        return self._call("POST", "/account/articles/%d/publish" % record_id)

    def new_version(self, record_id):
        # Publishing an already-published article is what creates a version.
        return self.publish(record_id)

    def delete_draft(self, record_id):
        self._call("DELETE", "/account/articles/%d" % record_id)


def load_categories():
    """facet -> [Figshare category id], plus the defaults, from categories.yml.

    Figshare validates categories on publish, so getting this wrong surfaces at
    the worst moment. The ids were read from the public /v2/categories endpoint.
    """
    path = ROOT / "categories.yml"
    data, section, facet = {"default": [], "subjects": {}, "methods": {}}, None, None
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.rstrip().endswith(":"):
            section, facet = line.rstrip()[:-1], None
        elif line.startswith("  ") and not line.startswith("    ") and ":" in line:
            facet, _, inline = line.strip().partition(":")
            if section in ("subjects", "methods"):
                data[section][facet] = [int(x) for x in re.findall(r"\d+", inline)]
        elif line.strip().startswith("- "):
            value = int(re.search(r"\d+", line).group(0))
            if section == "default":
                data["default"].append(value)
            elif facet is not None:
                data[section].setdefault(facet, []).append(value)
    return data


CATEGORIES = load_categories()


def categories_for(meta):
    """Every category this note belongs in, deduplicated, order preserved."""
    ids = list(CATEGORIES.get("default") or [])
    for axis in ("subjects", "methods"):
        for facet in (meta.get(axis) or []):
            ids += CATEGORIES.get(axis, {}).get(facet, [])
    seen, out = set(), []
    for value in ids:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def article_body(meta):
    """The Figshare fields, from our metadata.

    Authorship and custodianship are separate: the account owns the deposit,
    each record credits its real authors. The `authors` list here is a
    placeholder -- the provider replaces it with resolved Figshare identities,
    which it cannot do without the network.
    """
    authors = []
    for author in meta.get("authors") or []:
        entry = {"name": str(author.get("name") or "")}
        if author.get("orcid"):
            entry["orcid_id"] = author["orcid"]
        authors.append(entry)

    body = {
        "title": str(meta.get("title") or meta.get("slug")),
        "description": meta.get("abstract") or description_of(meta),
        "authors": authors,
        "license": LICENSE_CC_BY_4,
        "defined_type": DEFINED_TYPE,
        "keywords": [t for t in (list(meta.get("subjects") or [])
                                 + list(meta.get("methods") or [])) if t],
        "categories": categories_for(meta),
        "is_metadata_record": False,
    }

    # The two DOIs identify different objects -- a living page and a fixed
    # document -- and the relation is DECLARED rather than left to be inferred.
    # Without this, two DOIs for one note is the duplication the design exists
    # to prevent; with it, it is an ordinary variant relation.
    if meta.get("legacy_doi"):
        body["related_materials"] = [{
            "identifier": meta["legacy_doi"],
            "identifier_type": "DOI",
            "relation": "IsVariantFormOf",
            "title": "The web version of this note, as first published",
            "is_linkout": True,
        }]
    return body


def description_of(meta):
    """The article's own summary.

    In order: the front matter `description`, then the abstract, then the first
    paragraph of the article. A deposit whose description reads "a note from
    the series" tells a reader nothing and is what search will index, so the
    fallbacks go on until they find real prose.
    """
    slug = meta.get("slug")
    source = ARTICLES / slug / ("%s.md" % slug)
    if not source.exists():
        return "A note from Underworld Technical Notes."
    text = source.read_text(encoding="utf-8")
    head, _, body = text.partition("\n---\n")

    for pattern in (r"^description:\s*(.+)$", r"^\s+abstract:\s*(.+)$"):
        match = re.search(pattern, head, re.M)
        if match:
            return plain(match.group(1).strip().strip('"'))

    for block in body.split("\n\n"):
        block = block.strip()
        if not block or block.startswith(("<", "#", "```", ":::", "|", "$$")):
            continue
        block = plain(block)
        if len(block) < 80:
            continue           # too little prose survived; try the next one
        return block
    return "A note from Underworld Technical Notes."


def plain(text):
    """Markup out, prose in.

    Whatever the source, this lands on a provider's page as plain text: link
    syntax renders as literal brackets and LaTeX as literal backslashes.
    Display maths is dropped rather than flattened, because a description that
    trails off mid-equation is worse than a shorter one.
    """
    text = re.sub(r"\\begin\{.*?\\end\{[a-zA-Z*]+\}", " ", text, flags=re.S)
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[*_`$\\{}]", "", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return " ".join(text.split())[:900]


# ---------------------------------------------------------------------------
# metadata.yml is the record of what happened, so it is written as soon as
# anything irreversible-ish exists rather than at the end.
# ---------------------------------------------------------------------------

def set_field(slug, key, value):
    path = ARTICLES / slug / "metadata.yml"
    text = path.read_text(encoding="utf-8")
    line = "%s: %s" % (key, value)
    if re.search(r"^%s:.*$" % re.escape(key), text, re.M):
        text = re.sub(r"^%s:.*$" % re.escape(key), line, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    path.write_text(text, encoding="utf-8")


def load(slug):
    import build_index
    path = ARTICLES / slug / "metadata.yml"
    if not path.exists():
        sys.exit("no such article: %s" % slug)
    return build_index.read_yaml(path)


def check_eligible(slug, meta):
    """Refuse anything that would mint a DOI it should not.

    Three separate guards, because they fail differently: a note that already
    has a record, a note whose type gets no archival rendition, and the fifty
    legacy registrations that must never be re-minted.
    """
    if meta.get("repository_record_id"):
        raise DepositError(
            "%s already has repository_record_id %s. Depositing again would "
            "create a SECOND record and a second DOI for one note. Use "
            "--new-version to publish a new version of the existing record."
            % (slug, meta["repository_record_id"]))

    import build_index
    build_index.TYPES.update(build_index.article_types())
    if not build_index.is_archival(meta):
        raise DepositError(
            "%s is a %s, which gets no archival rendition -- see "
            "article-types.yml. There is nothing to deposit."
            % (slug, meta.get("article_type")))

    if meta.get("archive_doi") and not meta.get("repository_record_id"):
        raise DepositError(
            "%s has an archive_doi but no record id, so the duplicate guard has "
            "nothing to check. Resolve by hand before depositing." % slug)

    package = ROOT / "dist" / ("%s.zip" % slug)
    return package


def run(slug, provider, live, publish, new_version, delete_draft):
    import archive_package

    meta = load(slug)
    check_eligible(slug, meta)

    steps = []
    record_id = meta.get("repository_record_id")

    if not live:
        body = article_body(meta)
        print("DRY RUN -- nothing sent. Would deposit:\n")
        print(json.dumps(body, indent=2)[:2400])
        target, count, digest = archive_package.build(slug, ROOT / "dist")
        print("\npackage: %s  (%d files, %.1f KB, sha256 %s)"
              % (target.name, count, target.stat().st_size / 1024, digest[:16]))
        print("\nwould then: create draft -> reserve DOI -> write it into "
              "metadata.yml -> rebuild the PDF -> upload -> stop.")
        return

    if delete_draft:
        if not record_id:
            raise DepositError("%s has no record to delete" % slug)
        provider.delete_draft(int(record_id))
        set_field(slug, "repository_record_id", "null")
        set_field(slug, "archive_doi", "null")
        print("deleted draft %s and cleared it from metadata.yml" % record_id)
        return

    if not record_id:
        adopted = provider.find_draft(meta)
        record_id = provider.create_draft(meta)
        set_field(slug, "repository_record_id", record_id)
        # Said accurately, because "created" when it in fact adopted an existing
        # record is the sort of log line that sends somebody looking for a
        # duplicate that is not there.
        steps.append("%s draft %s"
                     % ("adopted existing" if adopted else "created", record_id))
    else:
        record_id = int(record_id)
        steps.append("resuming draft %s" % record_id)

    doi = meta.get("archive_doi")
    if not doi:
        doi = provider.reserve_doi(record_id)
        set_field(slug, "archive_doi", doi)
        steps.append("reserved %s" % doi)
        print("\n".join("  " + s for s in steps))
        print("\nThe DOI is now in metadata.yml. REBUILD THE PDF before "
              "uploading, so the DOI is on its title page:\n"
              "    pixi run build\n"
              "then run this again to upload.")
        return

    provider.update_metadata(record_id, load(slug))
    steps.append("updated metadata")

    package, _count, digest = archive_package.build(slug, ROOT / "dist")
    file_id = provider.upload(record_id, package)
    steps.append("uploaded %s (sha256 %s) as file %s"
                 % (package.name, digest[:16], file_id))

    if publish or new_version:
        result = provider.publish(record_id)
        steps.append("PUBLISHED: %s" % (result.get("location") or record_id))
        set_field(slug, "status", "published")
    else:
        steps.append("stopped before publish -- everything so far is reversible")

    print("\n".join("  " + s for s in steps))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--live", action="store_true",
                        help="actually talk to the provider")
    parser.add_argument("--publish", action="store_true",
                        help="the one irreversible step")
    parser.add_argument("--new-version", action="store_true",
                        help="publish a new version of an existing record")
    parser.add_argument("--delete-draft", action="store_true",
                        help="delete an unpublished draft and forget it")
    args = parser.parse_args()

    if args.publish and not args.live:
        sys.exit("--publish needs --live. Refusing to guess.")

    provider = Figshare(os.environ.get("FIGSHARE_TOKEN")) if args.live else None
    try:
        run(args.slug, provider, args.live, args.publish, args.new_version,
            args.delete_draft)
    except DepositError as exc:
        sys.exit("REFUSED: %s" % exc)


if __name__ == "__main__":
    main()
