#!/usr/bin/env python3
"""Recover images that are dead on the live site, from the Internet Archive.

Fifteen images in the corpus are still hot-linked to `underworldcode.ghost.io`,
the Ghost(Pro) hostname the site used before it was self-hosted. That host is
gone and the files were never copied to the droplet, so those figures are broken
on the live site today. One further image 404s on the current host.

The Wayback Machine has captures. This pulls them back, verifies each really is
an image, and records a SHA-256 so the recovery is auditable.

Wayback rate-limits aggressively; this runs sequentially with backoff and is
safe to re-run -- already-recovered files are skipped.

Usage:
    python3 scripts/recover_lost_assets.py [--pause 3] [--retries 4]
"""

import argparse
import csv
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
INVENTORY = ROOT / "inventory"
DEST = ROOT / "assets" / "recovered"
UA = "uwtn-recovery/1.0 (+https://www.underworldcode.org/)"

# Dead on the current host, but referenced by a published (DOI-bearing) post.
EXTRA = ["https://www.underworldcode.org/content/images/2019/09/ModelComparison.png"]


def lost_image_urls():
    """Dead outbound links that are images, from the link check."""
    path = INVENTORY / "link-check.json"
    if not path.exists():
        sys.exit("no link check -- run scripts/check_links.py first")
    data = json.loads(path.read_text(encoding="utf-8"))
    urls = {}
    for url, entry in data.items():
        status = entry["status"]
        alive = status in ("resolves", "403") or (status.isdigit() and int(status) < 400)
        if alive:
            continue
        if "/content/images/" in url or url.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
            urls[url] = entry["referenced_by"]
    for url in EXTRA:
        urls.setdefault(url, [])
    return urls


def wayback(url, pause, retries):
    """Fetch the raw archived bytes, or (None, reason)."""
    target = "https://web.archive.org/web/2020id_/" + url
    for attempt in range(retries):
        req = urllib.request.Request(target, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                if not body:
                    return None, "empty body"
                if not ctype.startswith("image/"):
                    return None, "content-type %s" % ctype
                return body, ctype
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503):
                wait = pause * (2 ** attempt)
                print("    throttled, waiting %ds" % wait, file=sys.stderr)
                time.sleep(wait)
                continue
            return None, "HTTP %s" % exc.code
        except Exception as exc:  # noqa: BLE001
            if attempt == retries - 1:
                return None, type(exc).__name__ + ": " + str(exc)[:70]
            time.sleep(pause * (2 ** attempt))
    return None, "gave up after %d attempts" % retries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pause", type=float, default=3.0, help="base delay between requests")
    parser.add_argument("--retries", type=int, default=4)
    args = parser.parse_args()

    urls = lost_image_urls()
    print("attempting recovery of %d lost image(s)\n" % len(urls), file=sys.stderr)
    DEST.mkdir(parents=True, exist_ok=True)

    rows, failed = [], []
    for i, (url, posts) in enumerate(sorted(urls.items()), 1):
        parts = urllib.parse.urlsplit(url)
        rel = parts.netloc + parts.path
        dest = DEST / rel
        print("  [%d/%d] %s" % (i, len(urls), parts.path.rsplit("/", 1)[-1]), file=sys.stderr)

        if dest.exists():
            body = dest.read_bytes()
            note = "(already recovered)"
        else:
            body, note = wayback(url, args.pause, args.retries)
            if body is None:
                failed.append((url, note, posts))
                print("        FAILED: %s" % note, file=sys.stderr)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            time.sleep(args.pause)

        rows.append({
            "url": url,
            "path": str(dest.relative_to(ROOT)),
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "referenced_by": " ".join(posts),
        })
        print("        recovered %d bytes %s" % (len(body), note), file=sys.stderr)

    with (INVENTORY / "recovered-assets.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["url", "path", "bytes", "sha256", "referenced_by"])
        writer.writeheader()
        writer.writerows(rows)

    print("\n--- recovery ---", file=sys.stderr)
    print("  %d/%d recovered, %.1f MB" % (len(rows), len(urls),
                                          sum(r["bytes"] for r in rows) / 1e6), file=sys.stderr)
    if failed:
        print("  %d unrecovered:" % len(failed), file=sys.stderr)
        for url, note, posts in failed:
            print("    %s  (%s)  in: %s" % (url, note, ", ".join(posts)), file=sys.stderr)
    print("  manifest: inventory/recovered-assets.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
