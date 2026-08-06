#!/usr/bin/env python3
"""Stage 0 inventory of the live Ghost site at www.underworldcode.org.

Read-only. Uses Ghost's public **Content API** as the authoritative source --
the published sitemap is incomplete (it omits three posts that are live and
carry registered DOIs), so anything driven off the sitemap would silently drop
them. The Content API key is the public one the site's own search widget uses;
it grants read access to published content only.

Joins the Rogue Scholar DOI register and classifies every public URL.

Outputs (under ``inventory/``):
    inventory.csv / inventory.json   one row per public URL
    doi-register.csv                 DOI -> slug; the URLs that must keep resolving
    assets.txt                       every site-hosted asset URL
    ghost-export/                    raw Content API payloads (the content corpus)

Nothing here touches the admin API or the droplet filesystem; the host is
treated as untrusted.

Usage:
    python3 scripts/inventory_site.py [--refresh]
"""

import argparse
import csv
import html
import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://www.underworldcode.org"
# Public Content API key, as published in the site's own sodo-search script tag.
# Read-only, published content only.
CONTENT_KEY = "dbc8368f509b3701ec7dc8d214"
ROGUE_SCHOLAR_API = "https://api.rogue-scholar.org/posts?blog_slug=underworldcode&per_page=100"

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "inventory"
EXPORT = OUT / "ghost-export"

# Ghost pages that exist only to drive the theme's routing, indexes and archives.
# Regenerated natively by the new site rather than migrated as content.
ROUTING_SLUGS = {"", "articles", "tags", "authors", "content"}
ARCHIVE_SLUG_RE = re.compile(r"^(19|20)\d{2}$|^Early$")

# Artefacts: near-empty pages created 30-31 Jul 2026, contemporaneous with the
# site compromise. Excluded from migration; retained in the incident record.
ARTEFACT_SLUG_RE = re.compile(r"^(rce(-\d+)?|sysinfo-[0-9a-f]+)$")

# Broken, or belonging to Ghost features the new site will not have.
RETIRE_SLUGS = {"atom", "account"}


def api(endpoint, **params):
    """Call the Ghost Content API and return the decoded payload."""
    params.setdefault("key", CONTENT_KEY)
    params.setdefault("limit", "all")
    url = "%s/ghost/api/content/%s/?%s" % (SITE, endpoint, urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={"User-Agent": "uwtn-inventory/1.0 (stage-0 migration audit)"})
    with urllib.request.urlopen(req, timeout=90) as fh:
        payload = json.load(fh)
    if "errors" in payload:
        raise RuntimeError("Ghost API error: %s" % payload["errors"])
    return payload


def rogue_scholar_dois():
    """slug -> DOI for every post Rogue Scholar has registered."""
    req = urllib.request.Request(ROGUE_SCHOLAR_API, headers={"User-Agent": "uwtn-inventory/1.0"})
    with urllib.request.urlopen(req, timeout=90) as fh:
        payload = json.load(fh)
    mapping = {}
    for item in payload.get("items", []):
        url = item.get("url") or ""
        doi = (item.get("doi") or "").replace("https://doi.org/", "")
        if url and doi:
            mapping[url.replace(SITE, "").strip("/")] = doi
    return mapping


def classify(slug, kind):
    if ARTEFACT_SLUG_RE.match(slug):
        return "artefact"
    if slug in RETIRE_SLUGS:
        return "retire"
    if kind == "page" and (slug in ROUTING_SLUGS or ARCHIVE_SLUG_RE.match(slug)):
        return "routing"
    return "migrate"


def assets_and_links(body):
    """Return (site-hosted assets, external assets, outbound links)."""
    body = body or ""
    srcs = re.findall(r'<img[^>]+src="([^"]+)"', body)
    srcs += [s.split()[0] for s in re.findall(r'srcset="([^"]+)"', body) if s.strip()]
    local, external = set(), set()
    for src in srcs:
        src = html.unescape(src.strip())
        if src.startswith("/content/"):
            local.add(SITE + src)
        elif src.startswith(SITE + "/content/"):
            local.add(src)
        elif src.startswith("http"):
            external.add(src)
    outbound = {
        html.unescape(h).split("?")[0]
        for h in re.findall(r'<a[^>]+href="(https?://[^"]+)"', body)
        if SITE not in h
    }
    return sorted(local), sorted(external), sorted(outbound)


def rows_from(records, kind, dois):
    rows = []
    for rec in records:
        slug = rec.get("slug") or ""
        body = rec.get("html") or ""
        local, external, outbound = assets_and_links(body)
        authors = rec.get("authors") or []
        rows.append({
            "kind": kind,
            "slug": slug,
            "url": rec.get("url") or "%s/%s/" % (SITE, slug),
            "title": rec.get("title") or "",
            "published": (rec.get("published_at") or "")[:10],
            "updated": (rec.get("updated_at") or "")[:10],
            "authors": "; ".join(a.get("name", "") for a in authors),
            "author_slugs": "; ".join(a.get("slug", "") for a in authors),
            "tags": "; ".join(t.get("name", "") for t in (rec.get("tags") or [])),
            "doi": dois.get(slug, ""),
            "classification": classify(slug, kind),
            "visibility": rec.get("visibility") or "",
            "html_bytes": len(body),
            "plaintext_words": len((rec.get("plaintext") or "").split()),
            "feature_image": rec.get("feature_image") or "",
            "canonical_url": rec.get("canonical_url") or "",
            "has_codeinjection": bool(rec.get("codeinjection_head") or rec.get("codeinjection_foot")),
            "n_local_assets": len(local),
            "n_external_assets": len(external),
            "n_outbound_links": len(outbound),
            "local_assets": " ".join(local),
            "external_assets": " ".join(external),
            "outbound_links": " ".join(outbound),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-fetch even if cached")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)

    print("fetching Rogue Scholar DOI register ...", file=sys.stderr)
    try:
        dois = rogue_scholar_dois()
    except Exception as exc:  # noqa: BLE001
        print("  WARNING: Rogue Scholar lookup failed (%s); DOIs will be blank" % exc, file=sys.stderr)
        dois = {}
    print("  %d registered DOIs" % len(dois), file=sys.stderr)

    fields = ("id,uuid,slug,title,html,plaintext,feature_image,feature_image_alt,"
              "published_at,updated_at,created_at,excerpt,custom_excerpt,canonical_url,"
              "codeinjection_head,codeinjection_foot,visibility,url,meta_title,meta_description,"
              "feature_image_caption")

    rows = []
    for endpoint, kind in (("posts", "post"), ("pages", "page")):
        cache = EXPORT / ("%s.json" % endpoint)
        if cache.exists() and not args.refresh:
            payload = json.loads(cache.read_text(encoding="utf-8"))
        else:
            print("fetching %s from Content API ..." % endpoint, file=sys.stderr)
            payload = api(endpoint, include="tags,authors", formats="html,plaintext", fields=fields)
            cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        records = payload[endpoint]
        print("  %d %s" % (len(records), endpoint), file=sys.stderr)
        rows.extend(rows_from(records, kind, dois))

    rows.sort(key=lambda r: (r["kind"], r["published"] or "0000", r["slug"]))

    header = [
        "kind", "slug", "url", "title", "published", "updated", "authors", "author_slugs",
        "tags", "doi", "classification", "visibility", "html_bytes", "plaintext_words",
        "has_codeinjection", "feature_image", "canonical_url", "n_local_assets",
        "n_external_assets", "n_outbound_links", "local_assets", "external_assets",
        "outbound_links",
    ]
    with (OUT / "inventory.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "inventory.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # The DOI register: the authoritative list of URLs that must keep resolving.
    by_slug = {r["slug"]: r for r in rows}
    with (OUT / "doi-register.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["doi", "slug", "url", "title", "published", "registrant", "in_ghost"])
        for slug, doi in sorted(dois.items(), key=lambda kv: kv[1]):
            row = by_slug.get(slug)
            writer.writerow([
                doi, slug, "%s/%s/" % (SITE, slug),
                row["title"] if row else "", row["published"] if row else "",
                "rogue-scholar", "yes" if row else "NO",
            ])

    assets = set()
    for row in rows:
        assets.update(row["local_assets"].split())
        if row["feature_image"].startswith(SITE) or row["feature_image"].startswith("/content/"):
            assets.add(row["feature_image"] if row["feature_image"].startswith("http")
                       else SITE + row["feature_image"])
    (OUT / "assets.txt").write_text("\n".join(sorted(assets)) + "\n", encoding="utf-8")

    counts = {}
    for row in rows:
        key = (row["kind"], row["classification"])
        counts[key] = counts.get(key, 0) + 1
    print("\n--- inventory summary ---", file=sys.stderr)
    print("  %d URLs" % len(rows), file=sys.stderr)
    for key in sorted(counts):
        print("    %-6s %-10s %d" % (key[0], key[1], counts[key]), file=sys.stderr)
    print("  %d DOIs registered" % len(dois), file=sys.stderr)
    print("  %d site-hosted assets" % len(assets), file=sys.stderr)

    orphans = sorted(set(dois) - set(by_slug))
    if orphans:
        print("\n  ERROR: %d DOI(s) reference slugs Ghost does not serve:" % len(orphans), file=sys.stderr)
        for slug in orphans:
            print("    %s -> %s" % (dois[slug], slug), file=sys.stderr)

    nodoi = [r["slug"] for r in rows
             if r["kind"] == "post" and r["classification"] == "migrate" and not r["doi"]]
    if nodoi:
        print("\n  NOTE: %d published post(s) carry no DOI:" % len(nodoi), file=sys.stderr)
        for slug in nodoi:
            print("    %s" % slug, file=sys.stderr)

    injected = [r["slug"] for r in rows if r["has_codeinjection"]]
    if injected:
        print("\n  ATTENTION: %d record(s) carry per-post code injection:" % len(injected), file=sys.stderr)
        for slug in injected:
            print("    %s" % slug, file=sys.stderr)


if __name__ == "__main__":
    main()
