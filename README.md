# Underworld Technical Notes — working repository

Successor to the `underworldcode.org` Ghost blog: a MyST-based, GitHub-hosted
technical publication series with DOI-backed archival PDFs.

Design brief: `~/Downloads/underworld-technical-notes-implementation-brief.md`
Implementation plan: `~/.claude/plans/the-job-i-have-peppy-origami.md`

**Status: Stage 1 complete — a working pilot of the twelve most recent months.**
Eleven articles converted from Ghost, building as a MyST site and as eleven
archival PDFs. This is a local working repository; it has not yet been pushed to
a GitHub organisation. See *Blocked on Louis* below.

```bash
pixi run convert      # Ghost export -> articles/
pixi run build        # HTML site + archival PDFs
pixi run test         # metadata validation + the DOI URL test
pixi run myst start   # preview the site locally
```

---

## What is here

```
articles/<slug>/        one directory per article
  <slug>.md             MyST source -- the FILENAME sets the URL
  metadata.yml          schema-validated article metadata
  figures/              local copies, including localised external images
templates/pdf/          archival PDF template (fork of lapreprint-typst)
schemas/                article metadata JSON Schema
authors.yml             author registry: names, ORCIDs, affiliations
corrections.yml         declared content fixes applied during conversion
scripts/
  ghost_to_myst.py      strict, sanitising Ghost -> MyST converter
  fix_slugs.py          restores full URLs after MyST's 50-char truncation
  validate_metadata.py  schema + cross-file invariants
  test_doi_urls.py      THE critical test: no registered DOI may 404
  inventory_site.py     read-only inventory via Ghost's public Content API
  audit_content.py      compromise audit of the exported corpus
  fetch_assets.py       verifiable mirror of every site-hosted asset
  check_links.py        liveness of every outbound link (DOI-aware)
  recover_lost_assets.py  Wayback recovery attempt for dead figures
inventory/
  inventory.csv/.json   one row per public URL, classified
  doi-register.csv      the 50 registered DOIs -> the URLs that must keep resolving
  assets.txt            every site-hosted asset URL
  asset-manifest.csv    mirrored assets with SHA-256
  compromise-audit.md   generated audit report
  link-check.md         dead outbound links, grouped by host
  recovered-assets.csv  what Wayback recovery actually yielded
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
python3 scripts/check_links.py
python3 scripts/recover_lost_assets.py
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

5. **Sixteen figures are permanently lost**, across eight posts, seven of which
   have DOIs. They are hot-linked to the retired `underworldcode.ghost.io` host
   and the Internet Archive never captured the image bytes — only the redirect.
   They are broken on the live site today.

6. **MyST truncates page slugs to 50 characters** — documented behaviour, and it
   silently breaks **12 of the 50 registered DOIs**. Neither a frontmatter
   `slug:` nor a toc entry overrides it, so `scripts/fix_slugs.py` restores the
   full paths after each build and rewrites internal references. It discovers
   the truncation rather than assuming the rule, and still applies under
   mystmd 1.10.1. `pixi run test-dois` is what proves a build is safe to publish.

7. **57 of 327 outbound links are dead.** The Discourse estate behind
   `uw-mailing-lists` no longer resolves in DNS, so that page is wholly dead and
   should be retired rather than migrated. Two DOI links are malformed by
   trailing punctuation — one of them Underworld3's own JOSS citation.

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
