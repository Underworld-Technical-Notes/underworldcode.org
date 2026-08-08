# Minting a DOI

How a note gets a DOI and an archival record. Written against Figshare's actual
API — endpoints and field names below are from `docs.figshare.com/swagger.json`,
not from memory.

The reassuring part first: **everything except the last step is reversible.**

## The sequence

```
POST /account/articles                     create a DRAFT (private)
POST /account/articles/{id}/reserve_doi    → {"doi": "10.xxxx/..."}
        write that DOI into metadata.yml
        rebuild the PDF, so the DOI is on the title page
POST /account/articles/{id}/files          upload the archive package
POST /account/articles/{id}/publish        ← the only irreversible step
```

The order matters and it is the whole reason Figshare works for us: the DOI
exists *before* the PDF is built, so it can be printed on the paper. A provider
that only mints on publication cannot do this — which is why the GitHub–Zenodo
webhook was ruled out, whatever the repository layout.

## What is reversible, and what is not

| step | reversible? |
|---|---|
| create a draft | yes — `DELETE /account/articles/{id}` |
| reserve a DOI | yes while the article is unpublished |
| upload files | yes — files can be replaced or deleted |
| **publish** | **no** — the DOI resolves publicly and permanently |

So the entire workflow can be rehearsed end to end against a real draft, on the
real account, and thrown away. Only `publish` needs care, and it is one call
behind an explicit confirmation flag.

`POST /account/articles/{id}/unpublish` exists, but treat it as unavailable: a
DOI that has resolved is a citation someone may already have used.

## Verified field values

| field | value |
|---|---|
| `license` | `1` (CC BY 4.0 — matches `license: CC-BY-4.0` in our metadata) |
| `defined_type` | `12` preprint, or `11` online resource — **decision needed** |
| `title` | the only field Figshare requires at creation |
| `is_metadata_record` | must stay false; we always deposit a PDF |

`reserve_doi` returns `{"doi": "..."}`. Figshare's own example shows
`10.5072/FK2...`, which is DataCite's *test* prefix — a real account returns a
real one, and that difference is worth checking on the first run.

## Versioning

Publishing an already-published article creates a **new public version**;
updates to a published article affect only the private copy until an explicit
publish. That matches the brief: cosmetic web corrections need no deposit, and
a substantive change is a new version.

## Two eras of DOI, and why they behave differently

A legacy DOI resolves to a **web page** on this site. A Figshare DOI resolves to
a **record** whose PDF is the artefact. Readers will meet both.

That cannot be unified, and should not be:

- the fifty legacy DOIs are Crossref registrations under Front Matter's prefix.
  We do not own them and cannot re-point them;
- minting a second DOI for a note that already has one is duplicate
  publication — the thing the whole design is built to prevent;
- minting our own under our own prefix would mean becoming a DOI registration
  agency, which the brief rules out.

The right framing is that **the new behaviour is the correct one**. A Rogue
Scholar DOI points at a living page that can change under it. A Figshare DOI
points at a fixed record with checksums. The legacy behaviour is the compromise
we are leaving, not a standard the new records should meet.

What removes the difference in practice is cross-linking, which is required on
both sides:

- every Figshare record carries the live article URL in `related_materials`, so
  a reader landing on the PDF can reach the living version;
- every article page shows its DOI and links its PDF, so a reader landing on
  the page can reach the fixed one.

Either entry point reaches both artefacts. Which one comes first is all that
differs.

### The real fragility in the legacy DOIs

Those fifty resolve to `www.underworldcode.org/<slug>/`, and **we cannot change
where they point**. Today that is fine because we control the URL. It stops
being fine the moment the URL has to move.

This must be settled with Front Matter before Rogue Scholar is deactivated, and
it is a different question from the one already on the list:

1. Do the fifty registered DOIs keep resolving after deactivation? (asked)
2. **Can their target URLs still be updated afterwards, and by whom?** (not yet
   asked, and more important)

If the answer to (2) is no, then `/​<slug>/` on this domain is a permanent,
unbreakable commitment for fifty articles, and the DOI test in CI is the only
thing standing between a refactor and fifty dead citations. If the answer is
yes, the constraint is merely strict rather than absolute.

### Which notes get a DOI

`article_type` governs it, per the brief: technical notes, worked examples and
benchmarks by default; development notes, how-tos and commentary selectively;
news never.

Note that the legacy set does not follow this — Rogue Scholar minted for
everything it ingested, so a release note in the corpus already carries a DOI.
That is not retrospectively fixable and is not worth trying to fix: the policy
governs what we mint, not what was minted.

## The failure that must never happen

Minting a *second* DOI for a note that already has one. Two guards, both in
place already:

- `metadata.yml` carries `repository_record_id`. If it is set, the publish
  command must refuse to create and offer to make a new version instead.
- `doi-register.csv` holds the fifty legacy Crossref DOIs. Any slug in it
  already has a DOI and must never be deposited as a new record. The validator
  already refuses a legacy DOI paired with a new registrant.

## Still to decide

**Which account — settled: a project account, not an institutional one and not
a personal one.**

ANU is ruled out deliberately. Leadership of Underworld will not always rest
with one person at one institution, and an institutional Figshare mints under
an institution-owned DOI prefix. Those DOIs cannot be re-minted, so they would
carry ANU's identity permanently, including after any move.

A personal figshare.com account mints under `10.6084` — Figshare's own prefix,
carrying no institutional identity at all. That is the desired property.

The account is held by the **project**, named as such (Underworld Geodynamics),
not by a person and not by an invented one. A fictitious identity is a
misrepresentation on a scholarly record, is visible as the depositor, and could
never hold an ORCID — so it could never be verified, which is the one thing an
archival record needs.

This costs nothing, because **custodianship and authorship are separate in
Figshare**: `authors` is set per record. The account owns the deposit; each
note credits its real authors with their real ORCIDs, exactly as `authors.yml`
already records them.

**Continuity comes from the email address.** Register the account to an address
on `underworldcode.org` — the project's own domain, held to 2035 — so the
account follows the domain rather than a person or an employer. The domain
currently has no MX records, so this needs mail forwarding adding at the
registrar first.

### The series as a community object

Figshare **collections** are first-class and answer this directly:
`POST /account/collections`, their own `reserve_doi`, their own author list,
categories and versions.

So the community shows up in two places, neither of which is the login:

- **each note** is an article carrying its real authors and their ORCIDs;
- **the series** is a collection with *its own DOI*, citable as a whole and
  identified independently of any person or institution.

A collection DOI is worth having on its own terms — it gives the series
something to cite, the way a journal has an ISSN — and it happens to be the
same property succession needs.

Zenodo's Communities were the reason to look again, and they turn out not to
be. Their advantage over a collection is that many people can deposit into one
community under curation. That does not apply here: the editorial model is
single-depositor by design — contributors open pull requests and CI deposits on
merge, which is what keeps the fifty registered DOIs safe from a stray
publish. Figshare being chosen for the reader's click-through therefore
stands.

**`defined_type`.** `preprint` reads as a paper awaiting formal publication;
`online resource` is vaguer but truer for a note that is not going anywhere
else. Affects how the record is described and indexed.

**Categories.** Figshare validates on publish, and in practice wants at least
one category plus keywords. Our subject/method facets are the natural source,
but Figshare's category list is its own controlled vocabulary and needs mapping
once.

## What Louis needs to provide

1. The account decision above.
2. A personal API token from that account
   (Figshare → Applications → Personal tokens).
3. The token stored as a GitHub Actions secret, `FIGSHARE_TOKEN`, so a
   publication can run from CI. Never in the repository.

## What is still to build

Nothing here is written yet — this documents the target, so the design is
settled before code exists.

- an archive-package builder: PDF, source, figures, bibliography, metadata
  JSON, `CITATION.cff`, README, SHA-256 checksums;
- a provider interface — create, reserve, upload, update, publish, new version
  — with a Figshare adapter behind it, so the Zenodo comparison stays possible;
- a publication command that is **dry-run by default**, prints exactly what it
  would deposit, and requires an explicit flag to publish;
- resumability: a run that dies after reserving a DOI must continue, not start
  again and reserve a second one.
