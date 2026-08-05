#!/usr/bin/env python3
"""Mirror every site-hosted asset referenced by the Ghost corpus.

Assets are fetched over HTTPS from the public site rather than read off the
droplet filesystem -- the host is compromised and is not trusted as a source.
Each file is stored under ``assets/<original path>`` with its SHA-256 recorded,
so the capture is verifiable and re-runnable.

Reads ``inventory/assets.txt`` (written by inventory_site.py).

Usage:
    python3 scripts/fetch_assets.py [--retry]
"""

import argparse
import csv
import hashlib
import pathlib
import sys
import time
import urllib.error
import urllib.request

SITE = "https://www.underworldcode.org"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
INVENTORY = ROOT / "inventory"

# Content types we expect from a /content/images/ path. Anything else is
# reported rather than silently trusted.
EXPECTED_PREFIXES = ("image/", "application/pdf", "video/", "text/plain")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry", action="store_true", help="re-fetch assets already present")
    args = parser.parse_args()

    listing = INVENTORY / "assets.txt"
    if not listing.exists():
        sys.exit("no asset list -- run scripts/inventory_site.py first")

    urls = [u.strip() for u in listing.read_text(encoding="utf-8").splitlines() if u.strip()]
    ASSETS.mkdir(parents=True, exist_ok=True)

    manifest, failures, suspicious = [], [], []
    for i, url in enumerate(urls, 1):
        rel = url.replace(SITE + "/", "")
        dest = ASSETS / rel
        if dest.exists() and not args.retry:
            body = dest.read_bytes()
            ctype = "(cached)"
        else:
            req = urllib.request.Request(url, headers={"User-Agent": "uwtn-inventory/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=60) as fh:
                    body = fh.read()
                    ctype = fh.headers.get("Content-Type", "")
            except Exception as exc:  # noqa: BLE001 - a mirror must not abort mid-run
                failures.append((url, str(exc)))
                print("  FAIL %s (%s)" % (rel, exc), file=sys.stderr)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            time.sleep(0.15)
            if ctype and not any(ctype.startswith(p) for p in EXPECTED_PREFIXES):
                suspicious.append((url, ctype))

        manifest.append({
            "url": url,
            "path": str(dest.relative_to(ROOT)),
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "content_type": ctype,
        })
        if i % 25 == 0:
            print("  %d/%d" % (i, len(urls)), file=sys.stderr)

    with (INVENTORY / "asset-manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["url", "path", "bytes", "sha256", "content_type"])
        writer.writeheader()
        writer.writerows(manifest)

    total = sum(m["bytes"] for m in manifest)
    print("\n--- asset mirror ---", file=sys.stderr)
    print("  %d/%d captured, %.1f MB" % (len(manifest), len(urls), total / 1e6), file=sys.stderr)
    if suspicious:
        print("  ATTENTION: %d asset(s) with an unexpected content type:" % len(suspicious), file=sys.stderr)
        for url, ctype in suspicious:
            print("    %s  %s" % (ctype, url), file=sys.stderr)
    if failures:
        print("  %d failure(s):" % len(failures), file=sys.stderr)
        for url, err in failures:
            print("    %s  %s" % (url, err), file=sys.stderr)
    print("  manifest: inventory/asset-manifest.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
