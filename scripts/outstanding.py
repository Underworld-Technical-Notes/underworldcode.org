#!/usr/bin/env python3
"""What is half-finished right now.

Every step of publishing a note is deliberate -- a person merges the
request to deposit, a person merges the identifiers that come back -- and
that is the right design. Its failure mode is that a step can simply not
happen, and nothing says so. A deposit sat unrecorded for a fortnight
because the only thing that would have complained was the NEXT deposit,
which is exactly when it is least welcome.

So this names the half-finished states. It reads metadata and, if `gh` is
available, open pull requests; it changes nothing.

    reserved, not published   a DOI is reserved and the deposit never
                              finished: either the request is still open
                              (normal, and named), or it was closed and the
                              draft is now unused
    timestamps not recorded   a publication-timestamp pull request is open;
                              bookkeeping only, since the identifiers already
                              reached main through the request
    note ahead of its copy    `version` has moved past `archived_version`:
                              the note has outrun what is on the DOI
    never deposited           archival, published, and has no DOI
    guard blind               an `archive_doi` with no `repository_record_id`

Exit 1 if anything is outstanding, so a scheduled run can raise it.

Usage:
    python3 scripts/outstanding.py            # report
    python3 scripts/outstanding.py --json     # for a workflow
    python3 scripts/outstanding.py --no-net   # metadata only
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
sys.path.insert(0, str(ROOT / "scripts"))


def field(text, key):
    m = re.search(r"^%s:\s*(.+?)\s*$" % re.escape(key), text, re.M)
    if not m:
        return None
    v = m.group(1).strip().strip('"').strip("'")
    return None if v in ("null", "~", "") else v


def open_branches(prefix):
    """Open pull requests whose branch starts with `prefix`.

    Returns None -- not [] -- when `gh` cannot answer, so the report can
    say "not checked" rather than "nothing outstanding". The difference
    matters: this exists because silence was mistaken for good news.
    """
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--limit", "100",
             "--json", "number,title,headRefName,createdAt"],
            capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        prs = json.loads(out.stdout or "[]")
    except ValueError:
        return None
    return [p for p in prs if p["headRefName"].startswith(prefix)]


def survey(check_net=True):
    import build_index
    build_index.TYPES.update(build_index.article_types())

    findings = {"unrecorded": None, "queued": None,
                "stale": [], "undeposited": [], "blind": [], "reserved": []}

    for md in sorted(ARTICLES.glob("*/metadata.yml")):
        slug = md.parent.name
        text = md.read_text(encoding="utf-8")
        meta = build_index.read_yaml(md)
        doi = field(text, "archive_doi")
        rid = field(text, "repository_record_id")
        version = field(text, "version")
        archived = field(text, "archived_version")

        if doi and not rid:
            findings["blind"].append(slug)
        if not build_index.is_archival(meta):
            continue
        if not doi:
            if field(text, "status") == "published":
                findings["undeposited"].append(slug)
            continue
        # A reserved record that never got published. Normal while its
        # request is open -- that is the gate doing its job -- and a stuck
        # draft once it is not, which nothing else would ever mention.
        if not field(text, "archive_published_at"):
            findings["reserved"].append((slug, doi))
            continue
        # archived_version is absent on nothing after the backfill, but a
        # note deposited by an older workflow would have none; say so
        # rather than guessing it matches.
        if version and archived and version != archived:
            findings["stale"].append((slug, archived, version))
        elif version and not archived:
            findings["stale"].append((slug, "unrecorded", version))

    if check_net:
        findings["unrecorded"] = open_branches("deposit/identifiers-")
        every = open_branches("deposit/")
        findings["queued"] = (None if every is None else
                              [p for p in every
                               if not p["headRefName"].startswith(
                                   "deposit/identifiers-")])
    return findings


def report(f):
    lines, outstanding = [], 0

    def head(title, n):
        lines.append("")
        lines.append("%s (%s)" % (title, n))

    if f["unrecorded"] is None:
        head("timestamps not recorded", "not checked -- gh unavailable")
    elif f["unrecorded"]:
        head("timestamps not recorded", len(f["unrecorded"]))
        for p in f["unrecorded"]:
            lines.append("  #%-5d %s  (opened %s)"
                         % (p["number"], p["title"][:60], p["createdAt"][:10]))
        lines.append("  -> bookkeeping: the identifiers are already on main, "
                     "so nothing is at risk while these wait")
        outstanding += len(f["unrecorded"])

    if f["reserved"]:
        asked = {}
        for p in (f["queued"] or []):
            asked[p["title"].replace("Deposit: ", "").strip()] = p["number"]
        head("reserved, not published", len(f["reserved"]))
        for slug, doi in f["reserved"]:
            if slug in asked:
                lines.append("  %-46s %s  request #%d open"
                             % (slug[:46], doi, asked[slug]))
            else:
                lines.append("  %-46s %s  NO OPEN REQUEST -- draft unused"
                             % (slug[:46], doi))
        lines.append("  -> merge the request to publish, or clear an unused "
                     "draft with --delete-draft")
        outstanding += len(f["reserved"])

    # A request open against a note with nothing reserved: a leftover from the
    # shared-queue design, or a reserve that failed. Either way it is asking
    # for something that will not happen when merged.
    reserved_slugs = {slug for slug, _doi in f["reserved"]}
    orphan = [p for p in (f["queued"] or [])
              if p["title"].replace("Deposit: ", "").strip()
              not in reserved_slugs]
    if orphan:
        head("request open, nothing reserved", len(orphan))
        for p in orphan:
            lines.append("  #%-5d %s  (opened %s)"
                         % (p["number"], p["title"][:60], p["createdAt"][:10]))
        lines.append("  -> close these; the note is offered again on its own")
        outstanding += len(orphan)

    if f["stale"]:
        head("note ahead of its archival copy", len(f["stale"]))
        for slug, was, now in f["stale"]:
            lines.append("  %-52s deposited %s, now %s" % (slug[:52], was, now))
        lines.append("  -> deposit a new version, or the DOI serves the "
                     "older text")
        outstanding += len(f["stale"])

    if f["undeposited"]:
        head("published, never deposited", len(f["undeposited"]))
        for slug in f["undeposited"]:
            lines.append("  %s" % slug)
        outstanding += len(f["undeposited"])

    if f["blind"]:
        head("archive_doi with no record id", len(f["blind"]))
        for slug in f["blind"]:
            lines.append("  %s" % slug)
        outstanding += len(f["blind"])

    if not outstanding:
        lines.append("Nothing outstanding.")
    return "\n".join(lines).lstrip("\n"), outstanding


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-net", action="store_true",
                    help="metadata only; do not ask gh about pull requests")
    args = ap.parse_args()

    f = survey(check_net=not args.no_net)
    text, n = report(f)
    if args.json:
        print(json.dumps({"outstanding": n, "report": text, "findings": f},
                         indent=2, default=list))
    else:
        print(text)
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
