# Underworld Technical Notes — working repository

Successor to the `underworldcode.org` Ghost blog: a MyST-based, GitHub-hosted
technical publication series with DOI-backed archival PDFs.

Design brief: `~/Downloads/underworld-technical-notes-implementation-brief.md`
Implementation plan: `~/.claude/plans/the-job-i-have-peppy-origami.md`

**Status: Stage 0 (inventory, DOI register, compromise audit) — complete.**
This is a local working repository. It has not yet been pushed to a GitHub
organisation; see *Blocked on Louis* below.

---

## What is here

```
scripts/
  inventory_site.py     read-only inventory via Ghost's public Content API
  audit_content.py      compromise audit of the exported corpus
  fetch_assets.py       verifiable mirror of every site-hosted asset
inventory/
  inventory.csv/.json   one row per public URL, classified
  doi-register.csv      the 50 registered DOIs -> the URLs that must keep resolving
  assets.txt            every site-hosted asset URL
  asset-manifest.csv    mirrored assets with SHA-256
  compromise-audit.md   generated audit report
  ghost-export/         raw Content API payloads (the content corpus)
  STAGE-0-FINDINGS.md   the analysis, and what it means for the migration
assets/                 mirrored binaries (not in git — see below)
```

Everything is read-only against the live site and stdlib-only Python 3.9+.
No admin credentials and no droplet filesystem access are used: the host is
compromised and is not trusted as a source.

```bash
python3 scripts/inventory_site.py     # --refresh to re-fetch
python3 scripts/audit_content.py
python3 scripts/fetch_assets.py
```

`assets/` (69 MB) is deliberately not committed. The checksummed manifest is in
git; the binaries are re-fetchable while the droplet is up, and will be placed
under version control properly when the site tree is laid out in Stage 2.
**Do not decommission the droplet before Stage 2 has taken them into the repo.**

---

## Headline findings

Full detail in `inventory/STAGE-0-FINDINGS.md`.

1. **The sitemap is not a complete inventory.** It lists 51 posts; Ghost serves
   **54**. The three missing posts are live and each carries a registered DOI.
   A sitemap-driven migration would have silently broken three DOIs. The
   Content API is used instead, and `doi-register.csv` — not the sitemap — is
   what the Stage 2 link tests are gated on.

2. **The compromise was two bulk writes, not a defacement.** On **2026-07-07**,
   73 of 87 content records were written with an identical
   `codeinjection_foot` of three Cyrillic `U+0441` characters. On **2026-07-30/31**,
   14 further records were created (13 `rce-*` pages and a `sysinfo-*` post,
   near-empty). Whoever did this had write access to most of the content
   database. The injected payload is inert as rendered, but the access was not
   limited to what it was used for.

3. **No malicious script survived in the article bodies.** All 12 script/iframe
   occurrences are legitimate embeds (GitHub gists, YouTube, Google Maps,
   embedly, jQuery for the Zotero bibliographies).

4. **50 registered DOIs, all resolving to live records.** Three recent posts
   (Apr–Jun 2026) carry no DOI — Rogue Scholar had not ingested them.

---

## Blocked on Louis

- **Create the GitHub organisation** and add a second owner. The local `gh`
  token holds `gist`, `read:org`, `repo` only — no `admin:org` — so this cannot
  be done from here. Suggested: org `underworld-notes`, repo `underworldcode.org`.
- **Cull the pages.** 16 Ghost pages are classified `migrate`; decide which
  survive. See the table in `STAGE-0-FINDINGS.md`.
- **Contact Front Matter** to deactivate Rogue Scholar ingestion and get written
  confirmation that the 50 registered DOIs keep resolving.
- **Ghost admin export + droplet snapshot** as the belt-and-braces incident
  record. Not blocking — the Content API already yielded the full corpus — but
  the snapshot should be taken before anything on the droplet is touched.
- **Rotate credentials** the droplet held, and treat the 2026-07-07 write as the
  earliest confirmed compromise date when scoping that.
