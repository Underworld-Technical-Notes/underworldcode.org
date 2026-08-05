#!/usr/bin/env python3
"""Liveness check for every outbound link in the Ghost corpus.

Twelve years of posts accumulate dead ends: services that shut down, forums
that were retired, institutional pages that moved. This finds them before the
content is migrated, so links are fixed, annotated or dropped deliberately
rather than carried across broken.

Ghost appends ``?ref=underworldcode.org`` to outbound links; that is stripped
before checking and should be stripped on migration too.

Read-only. Writes a Markdown report and a JSON companion under ``inventory/``.

Usage:
    python3 scripts/check_links.py [--workers 8] [--timeout 20]
"""

import argparse
import collections
import concurrent.futures
import html
import json
import pathlib
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPORT = ROOT / "inventory" / "ghost-export"
OUT = ROOT / "inventory"

SITE_HOSTS = {"www.underworldcode.org", "underworldcode.org"}
UA = "Mozilla/5.0 (compatible; uwtn-linkcheck/1.0; +https://www.underworldcode.org/)"


def strip_ref(url):
    """Drop Ghost's ?ref= tracking parameter, keeping any other query."""
    parts = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != "ref"]
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), "")
    )


def collect():
    """url -> set of slugs referencing it."""
    refs = collections.defaultdict(set)
    for kind in ("posts", "pages"):
        payload = json.loads((EXPORT / ("%s.json" % kind)).read_text(encoding="utf-8"))
        for rec in payload[kind]:
            blob = " ".join(str(rec.get(f) or "") for f in
                            ("html", "codeinjection_head", "codeinjection_foot"))
            found = re.findall(r'(?:href|src)="(https?://[^"]+)"', blob)
            found += re.findall(r"""\$\.ajax\(\s*['"](https?://[^'"]+)['"]""", blob)
            for url in found:
                url = strip_ref(html.unescape(url))
                if urllib.parse.urlsplit(url).netloc not in SITE_HOSTS:
                    refs[url].add(rec["slug"])
    return refs


DOI_HOSTS = {"doi.org", "dx.doi.org"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe_doi(url, timeout):
    """A DOI is alive if doi.org itself redirects it.

    The publisher it redirects *to* frequently returns 403 to anything that
    looks like a bot (Wiley, AGU, PeerJ all do). That says nothing about the
    DOI, so judging a DOI by its final status manufactures false positives.
    """
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, "unexpected 2xx from doi.org"
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            return "resolves", exc.headers.get("Location", "")[:90]
        return exc.code, "doi.org does not resolve this DOI"
    except Exception as exc:  # noqa: BLE001
        return type(exc).__name__, str(exc)[:90]


def probe(url, timeout):
    """Return (status, note). status is an int, or a short failure string."""
    if urllib.parse.urlsplit(url).netloc in DOI_HOSTS:
        return probe_doi(url, timeout)
    ctx = ssl.create_default_context()
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.status, resp.url if resp.url != url else ""
        except urllib.error.HTTPError as exc:
            # Some hosts refuse HEAD but serve GET; retry once before believing it.
            if method == "HEAD" and exc.code in (403, 405, 501):
                continue
            return exc.code, ""
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if method == "HEAD" and "timed out" not in reason.lower():
                continue
            return "URLError", reason[:90]
        except Exception as exc:  # noqa: BLE001
            return type(exc).__name__, str(exc)[:90]
    return "unknown", ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    if not (EXPORT / "posts.json").exists():
        sys.exit("no export found -- run scripts/inventory_site.py first")

    refs = collect()
    urls = sorted(refs)
    print("checking %d unique outbound links ..." % len(urls), file=sys.stderr)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(probe, u, args.timeout): u for u in urls}
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            url = futures[future]
            results[url] = future.result()
            if i % 50 == 0:
                print("  %d/%d" % (i, len(urls)), file=sys.stderr)

    def is_dead(status):
        if status == "resolves":          # DOI that doi.org redirects -- alive
            return False
        if status == 403:                 # publisher/CDN bot-blocking, not rot
            return False
        return not (isinstance(status, int) and status < 400)

    blocked = {u: r for u, r in results.items() if r[0] == 403}
    dead = {u: r for u, r in results.items() if is_dead(r[0])}
    by_host = collections.defaultdict(list)
    for url, (status, note) in dead.items():
        by_host[urllib.parse.urlsplit(url).netloc].append((url, status, note))

    lines = ["# Outbound link check", ""]
    lines.append("%d unique outbound links across the corpus; **%d dead or unreachable**."
                 % (len(urls), len(dead)))
    lines.append("")
    lines.append("Ghost appends `?ref=underworldcode.org` to outbound links. That is "
                 "stripped here and must be stripped on migration.")
    lines.append("")
    lines.append("Two categories are excluded from *dead*: DOIs that `doi.org` "
                 "resolves (the publisher behind them often returns 403 to bots, "
                 "which says nothing about the DOI), and %d link(s) returning 403 "
                 "from bot-blocking hosts. Both are listed separately below."
                 % len(blocked))
    lines.append("")
    lines.append("## Dead links by host")
    lines.append("")
    lines.append("| host | dead | referenced by |")
    lines.append("|---|---:|---|")
    for host, entries in sorted(by_host.items(), key=lambda kv: -len(kv[1])):
        slugs = sorted({s for url, _, _ in entries for s in refs[url]})
        shown = ", ".join("`%s`" % s for s in slugs[:4])
        if len(slugs) > 4:
            shown += " +%d more" % (len(slugs) - 4)
        lines.append("| `%s` | %d | %s |" % (host, len(entries), shown))
    lines.append("")
    lines.append("## Detail")
    lines.append("")
    for host, entries in sorted(by_host.items(), key=lambda kv: -len(kv[1])):
        lines.append("### `%s`" % host)
        lines.append("")
        for url, status, note in sorted(entries):
            slugs = ", ".join(sorted(refs[url]))
            lines.append("- `%s` — **%s** %s" % (url, status, note))
            lines.append("  - in: %s" % slugs)
        lines.append("")

    if blocked:
        lines.append("## Reachable but bot-blocked (403) — no action needed")
        lines.append("")
        for url in sorted(blocked):
            lines.append("- `%s` — in: %s" % (url, ", ".join(sorted(refs[url]))))
        lines.append("")

    (OUT / "link-check.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "link-check.json").write_text(json.dumps(
        {u: {"status": str(r[0]), "note": r[1], "referenced_by": sorted(refs[u])}
         for u, r in sorted(results.items())}, indent=2), encoding="utf-8")

    print("\n--- link check ---", file=sys.stderr)
    print("  %d unique links, %d dead" % (len(urls), len(dead)), file=sys.stderr)
    for host, entries in sorted(by_host.items(), key=lambda kv: -len(kv[1]))[:15]:
        print("    %-52s %d" % (host, len(entries)), file=sys.stderr)
    print("\n  report: inventory/link-check.md", file=sys.stderr)


if __name__ == "__main__":
    main()
