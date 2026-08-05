#!/usr/bin/env python3
"""Stage 0 compromise audit of the Ghost content corpus.

The site was compromised. Everything exported from it is therefore suspect, and
must be inspected before any of it is converted and republished. This script
reads the Content API payloads captured by ``inventory_site.py`` and reports, per
record, anything that could carry an attacker payload into the new site.

Checks:
    script / iframe / object / embed tags in the body
    inline event handlers (onerror=, onload=, ...) and javascript: URIs
    data: URIs and long base64 blobs
    Cyrillic homoglyphs in otherwise-Latin text (the known 'ссс' signature)
    non-empty codeinjection_head / codeinjection_foot
    outbound links to domains outside the expected set
    records written during the compromise window

Read-only. Writes a Markdown report and a JSON companion under ``inventory/``.

Usage:
    python3 scripts/audit_content.py [--window 2026-07-25:2026-08-05]
"""

import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPORT = ROOT / "inventory" / "ghost-export"
OUT = ROOT / "inventory"

CYRILLIC = re.compile(r"[Ѐ-ӿ]")
SCRIPTISH = re.compile(r"<\s*(script|iframe|object|embed|form)\b", re.I)
HANDLER = re.compile(r"\son(error|load|click|mouseover|focus|toggle)\s*=", re.I)
JS_URI = re.compile(r"""(?:href|src)\s*=\s*["']\s*javascript:""", re.I)
DATA_URI = re.compile(r"""(?:href|src)\s*=\s*["']\s*data:""", re.I)
B64_BLOB = re.compile(r"[A-Za-z0-9+/]{400,}={0,2}")

# Domains legitimately linked from Underworld content.
EXPECTED_DOMAINS = {
    "github.com", "www.github.com", "raw.githubusercontent.com", "gist.github.com",
    "doi.org", "dx.doi.org", "zenodo.org", "figshare.com", "orcid.org",
    "underworldcode.org", "www.underworldcode.org", "underworld2.readthedocs.io",
    "underworld3.readthedocs.io", "readthedocs.io", "joss.theoj.org",
    "mybinder.org", "hub.docker.com", "docker.com", "www.docker.com",
    "anaconda.org", "conda-forge.org", "pypi.org", "python.org", "www.python.org",
    "petsc.org", "www.mcs.anl.gov", "gmsh.info", "sympy.org", "www.sympy.org",
    "numpy.org", "scipy.org", "jupyter.org", "images.unsplash.com", "unsplash.com",
    "creativecommons.org", "auscope.org.au", "www.auscope.org.au", "anu.edu.au",
    "www.anu.edu.au", "sydney.edu.au", "www.sydney.edu.au", "monash.edu",
    "www.monash.edu", "agu.org", "copernicus.org", "www.frontiersin.org",
    "twitter.com", "x.com", "youtube.com", "www.youtube.com", "youtu.be",
    "en.wikipedia.org", "scholar.google.com", "researchgate.net",
    "www.researchgate.net", "nci.org.au", "pawsey.org.au", "www.pawsey.org.au",
}


def domain_of(url):
    match = re.match(r"https?://([^/]+)", url)
    return match.group(1).lower() if match else ""


def audit_record(rec):
    """Return a list of (severity, check, detail) findings for one record."""
    body = rec.get("html") or ""
    findings = []

    for name, pattern, severity in (
        ("script-like tag", SCRIPTISH, "high"),
        ("inline event handler", HANDLER, "high"),
        ("javascript: URI", JS_URI, "high"),
        ("data: URI", DATA_URI, "medium"),
    ):
        hits = pattern.findall(body)
        if hits:
            findings.append((severity, name, "%d occurrence(s)" % len(hits)))

    blobs = B64_BLOB.findall(body)
    if blobs:
        findings.append(("medium", "long base64 blob", "%d blob(s), longest %d chars"
                         % (len(blobs), max(len(b) for b in blobs))))

    for key in ("codeinjection_head", "codeinjection_foot"):
        value = rec.get(key)
        if value:
            findings.append(("high", key, repr(value)))

    # Cyrillic in a corpus that is entirely English -- the known injection signature.
    text = (rec.get("plaintext") or "") + " " + (rec.get("title") or "")
    cyr = CYRILLIC.findall(text)
    if cyr:
        findings.append(("high", "cyrillic in body text", "%d char(s): %r"
                         % (len(cyr), "".join(sorted(set(cyr)))[:20])))

    unexpected = sorted({
        domain_of(h) for h in re.findall(r'<a[^>]+href="(https?://[^"]+)"', body)
    } - EXPECTED_DOMAINS - {""})
    if unexpected:
        findings.append(("review", "outbound domain not in expected set",
                         ", ".join(unexpected[:12]) + (" ..." if len(unexpected) > 12 else "")))

    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", default="2026-07-25:2026-08-05",
                        help="compromise window as FROM:TO (inclusive, YYYY-MM-DD)")
    args = parser.parse_args()
    win_from, win_to = args.window.split(":")

    if not (EXPORT / "posts.json").exists():
        sys.exit("no export found -- run scripts/inventory_site.py first")

    records = []
    for kind in ("posts", "pages"):
        payload = json.loads((EXPORT / ("%s.json" % kind)).read_text(encoding="utf-8"))
        for rec in payload[kind]:
            rec["_kind"] = kind[:-1]
            records.append(rec)

    results, sev_counts, check_counts = [], collections.Counter(), collections.Counter()
    for rec in records:
        findings = audit_record(rec)
        updated = (rec.get("updated_at") or "")[:10]
        in_window = win_from <= updated <= win_to
        if in_window:
            findings.append(("review", "written during compromise window", "updated_at %s" % updated))
        if findings:
            results.append({
                "kind": rec["_kind"],
                "slug": rec.get("slug"),
                "title": rec.get("title"),
                "published": (rec.get("published_at") or "")[:10],
                "updated": updated,
                "findings": [{"severity": s, "check": c, "detail": d} for s, c, d in findings],
            })
            for severity, check, _ in findings:
                sev_counts[severity] += 1
                check_counts[check] += 1

    # When were records written? A tight cluster dates the injection.
    updates = collections.Counter((r.get("updated_at") or "")[:10] for r in records)

    lines = ["# Stage 0 compromise audit", ""]
    lines.append("Corpus: **%d records** (%d posts, %d pages) from the Ghost Content API."
                 % (len(records),
                    sum(1 for r in records if r["_kind"] == "post"),
                    sum(1 for r in records if r["_kind"] == "page")))
    lines.append("")
    lines.append("%d record(s) carry at least one finding." % len(results))
    lines.append("")
    lines.append("## Findings by check")
    lines.append("")
    lines.append("| check | records |")
    lines.append("|---|---:|")
    for check, count in check_counts.most_common():
        lines.append("| %s | %d |" % (check, count))
    lines.append("")
    lines.append("## Record write dates")
    lines.append("")
    lines.append("A tight cluster of `updated_at` values indicates a bulk write.")
    lines.append("")
    lines.append("| updated_at | records |")
    lines.append("|---|---:|")
    for day, count in sorted(updates.items(), reverse=True)[:15]:
        lines.append("| %s | %d |" % (day, count))
    lines.append("")
    lines.append("## Per-record detail")
    lines.append("")
    order = {"high": 0, "medium": 1, "review": 2}
    results.sort(key=lambda r: (min(order[f["severity"]] for f in r["findings"]), r["slug"] or ""))
    for res in results:
        lines.append("### `%s` (%s)" % (res["slug"], res["kind"]))
        lines.append("")
        lines.append("%s — published %s, updated %s" % (res["title"], res["published"], res["updated"]))
        lines.append("")
        for finding in res["findings"]:
            lines.append("- **%s** — %s: %s" % (finding["severity"], finding["check"], finding["detail"]))
        lines.append("")

    (OUT / "compromise-audit.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "compromise-audit.json").write_text(
        json.dumps({"records": results,
                    "severity_counts": dict(sev_counts),
                    "check_counts": dict(check_counts),
                    "update_dates": dict(updates)}, indent=2), encoding="utf-8")

    print("--- compromise audit ---", file=sys.stderr)
    print("  %d records, %d with findings" % (len(records), len(results)), file=sys.stderr)
    for severity in ("high", "medium", "review"):
        if sev_counts[severity]:
            print("    %-8s %d finding(s)" % (severity, sev_counts[severity]), file=sys.stderr)
    print("  by check:", file=sys.stderr)
    for check, count in check_counts.most_common():
        print("    %-42s %d" % (check, count), file=sys.stderr)
    print("  top write dates:", file=sys.stderr)
    for day, count in sorted(updates.items(), reverse=True)[:6]:
        print("    %s  %d" % (day, count), file=sys.stderr)
    print("\n  report: inventory/compromise-audit.md", file=sys.stderr)


if __name__ == "__main__":
    main()
