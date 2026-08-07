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

## The failure that must never happen

Minting a *second* DOI for a note that already has one. Two guards, both in
place already:

- `metadata.yml` carries `repository_record_id`. If it is set, the publish
  command must refuse to create and offer to make a new version instead.
- `doi-register.csv` holds the fifty legacy Crossref DOIs. Any slug in it
  already has a DOI and must never be deposited as a new record. The validator
  already refuses a legacy DOI paired with a new registrant.

## Still to decide

**Which account.** A personal figshare.com account, or ANU's institutional
Figshare. This is the decision that most affects the outcome: institutional
instances can have a different DOI prefix, storage quotas, group-level review
before publication, and their own metadata requirements. Publishing under an
institution also ties the record's custodianship to it. Worth settling before
the first real deposit rather than after.

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
