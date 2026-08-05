# Stage 0 findings

Inventory, DOI register and compromise audit of `www.underworldcode.org`,
5 August 2026. All evidence is reproducible from the scripts in `scripts/`.

---

## 1. The site

| | |
|---|---|
| Host | self-hosted **Ghost 5.118**, nginx/Ubuntu, DigitalOcean droplet `128.199.201.97` |
| Canonical origin | `www.underworldcode.org` |
| Apex | `underworldcode.org` → GitHub Pages A records, unclaimed by any repo, **currently 404** |
| Domain | Netregistry (AU), registered to 2035 |
| Content | **54 posts, 33 pages** (Content API); 14 of those are compromise artefacts |

The apex being already pointed at GitHub Pages and unclaimed is convenient: a
staging deploy can serve the real domain immediately without touching the live
site on `www`.

## 2. The sitemap is not a complete inventory

The published sitemap lists **51** posts. Ghost serves **54**. The three it omits
are live (HTTP 200) and each carries a registered DOI that resolves to it:

| DOI | slug |
|---|---|
| `10.59350/hsp06-ag431` | `30-years-of-citcom-ellipsis-and-underworld` |
| `10.59350/qpft6-wks47` | `australian-cities-are-quiet-during-lockdown-earthquake-scientists-are-making-the-most-of-it` |
| `10.59350/g4ysn-pv176` | `compressible-convection-in-cartesian-coordinates-in-underworld3` |

A migration driven off the sitemap — the obvious approach, and the one the brief
implies — would have dropped all three and broken three registered DOIs, silently.

**Consequence for the plan:** the inventory is built from Ghost's public Content
API, and `doi-register.csv` rather than the sitemap is what the Stage 2 link
tests are gated on. Whatever else changes, that file is the contract.

## 3. The compromise: two bulk writes

### 2026-07-07 — mass content write, 73 records

73 of 87 records carry a `codeinjection_foot` whose value is exactly:

```
'ссс'   # three x U+0441 CYRILLIC SMALL LETTER ES
```

No markup, no script, no URL. All 73 share `updated_at` of 2026-07-07.

As rendered this is inert — three stray characters at the foot of the page. Its
significance is not the payload but the access: **something wrote to 73 content
records in the Ghost database**, spanning 53 of 54 posts and 20 of 33 pages. The
capability demonstrated is arbitrary content injection sitewide; what was
actually injected on 7 July appears to be a canary or the residue of a payload
since removed.

### 2026-07-30 / 31 — 14 new records

| slug | kind | created | words |
|---|---|---|---|
| `rce-2` … `rce-11` | page | 2026-07-30 | 0 |
| `rce`, `rce-12`, `rce-13` | page | 2026-07-31 | 0 |
| `sysinfo-3c8a5c38` | post | 2026-07-31 | 0 |

All empty. Naming is consistent with remote-code-execution probing, and the
`sysinfo` post is attributed to the "Louis Moresi" author record.

> **Question for Louis:** the audit cannot distinguish attacker-created probe
> pages from pages you created yourself while investigating. If these are yours,
> say so and they are simply dropped. If they are not, 2026-07-07 is the earliest
> confirmed unauthorised write and credential rotation should be scoped from
> there, not from 30 July.

### What is *not* there

No malicious script survived in any article body. All 12 script/iframe
occurrences and both inline event handlers are legitimate:

- GitHub gist embeds (`underworld-and-singularity`, `underworld-release-2-8`)
- YouTube oembeds (`publication-news`, `underworld-release-2-8`, `craton-formation…`)
- a Google Maps embed (`congested-subduction-workshop`)
- embedly (`untitled-2`)
- jQuery + Zotero bibliography scripts (`lm-publications`, `group-publications`,
  `publications-using-uw`, `who-is-using-stripy`, `uw-mailing-lists`)
- Ghost's own `onerror="this.style.display…"` image fallback

### Standing third-party exposure, independent of the compromise

Every page loads, among others:

- `s7.addthis.com/js/300/addthis_widget.js` — **AddThis was shut down by Oracle
  in 2023.** This is executable script pulled from an abandoned service on every
  page load.
- `code.jquery.com/jquery-1.11.3.min.js` (2015)
- `t.ghostboard.io/min.js`, Google Analytics `UA-` (deprecated property)
- MathJax 2.7.3 and Prism 1.17.1 from CDNs
- Ghost `portal`, `comments-ui`, `sodo-search` from jsDelivr

The static replacement removes all of this by construction.

## 4. DOI position

- **50 registered DOIs**, Crossref prefix `10.59350`, registrant Rogue Scholar
  (Front Matter), each resolving to `https://www.underworldcode.org/<slug>/`.
- All 50 map to a live Ghost record — no orphans.
- **Three published posts carry no DOI**, being newer than the last ingestion:
  `symbolic-time-derivatives-in-underworld3` (2026-04-16),
  `particles-in-underworld3` (2026-06-03),
  `finding-particles-in-a-distributed-unstructured-mesh` (2026-06-04).
  These are the natural first candidates for the new DOI mechanism.

The 50 existing DOIs are permanent Crossref registrations under a prefix we do
not control. They are **not** to be re-minted; the obligation they create is
narrow and absolute — those 50 URLs must keep resolving.

## 5. Pages: the cull list

16 pages are real content. Louis to mark keep / retire / merge.

| slug | words | title |
|---|---:|---|
| `intro-to-underworld` | 839 | Underworld |
| `stripy` | 806 | Stripy |
| `lavavu` | 794 | Lavavu |
| `congested-subduction-workshop` | 785 | Congested Subduction Workshop |
| `how-to-cite-underworld` | 459 | How to cite underworld codes |
| `credits` | 355 | Credits |
| `underworld-steering-committee` | 210 | Underworld Steering Committee |
| `auscope-cloud` | 209 | About the AuScope Cloud |
| `underworld-model-exchange` | 206 | Underworld Model Exchange |
| `ugcomm` | 164 | About us |
| `publications-using-uw` | 128 | Who's Using Underworld |
| `who-is-using-stripy` | 92 | Who's using stripy |
| `uw-mailing-lists` | 68 | Underworld Community Mailing list |
| `group-publications` | 30 | Our Publications |
| `lm-publications` | 14 | Publications by Louis Moresi |
| `underworld-geodynamics-community` | 4 | Underworld Geodynamics Community |

Retired automatically: `account` (Ghost membership), `atom` (already returns
*400 Missing template atom.hbs*). Regenerated natively rather than migrated:
`/`, `articles`, `tags`, `authors`, `content`, and the year archives.

**Note the low word counts.** `group-publications`, `lm-publications`,
`publications-using-uw` and `who-is-using-stripy` are nearly empty as stored
because their content is fetched from Zotero by client-side JavaScript at page
load. On a static site with no third-party JS these must be **baked at build
time** — a Zotero fetch in CI writing a static bibliography. That is real work
the brief does not account for, and it should be scoped in Stage 2.

## 6. Assets

159 of 160 site-hosted assets mirrored, 69.1 MB, each with a SHA-256 in
`asset-manifest.csv`.

One failure: `content/images/2019/09/ModelComparison.png` returns 404 on the live
site. It is referenced by `shear-bands-with-dilatancy-modelled-with-underworld`,
which has a DOI (`10.59350/awc90-63186`). This is pre-existing rot — the
migration does not cause it — but the article is incomplete as published. A
Wayback recovery attempt was rate-limited; retry before Stage 2.

Feature images for recent posts are hot-linked from `images.unsplash.com` and
are not site-hosted. They are not covered by the mirror and will need either
local copies or replacement.

---

## Actions

**Louis**

1. Create the GitHub org (needs `admin:org`; the local token does not have it) and add a second owner.
2. Answer the `rce-*` / `sysinfo-*` question in §3 — yours or not?
3. Rotate droplet-held credentials; scope from 2026-07-07.
4. Mark the cull list in §5.
5. Contact Front Matter: deactivate Rogue Scholar ingestion, get written confirmation the 50 DOIs keep resolving.
6. Take the Ghost admin export and a droplet snapshot for the incident record — before anything on the droplet is touched.

**Next here (Stage 1)**

Repository skeleton, metadata schema, and one converted article
(*How Underworld3 Turns SymPy into C*) rendering as both HTML and a Typst
archival PDF.
